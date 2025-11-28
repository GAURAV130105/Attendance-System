import os
import shutil
import json
import numpy as np
from typing import List, Union, Annotated
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette import status

# --- LIBRARIES FOR REAL IMPLEMENTATION ---
import face_recognition
import mysql.connector
from mysql.connector import Error

# --- SECURITY CONFIGURATION ---
SECRET_KEY = "your-very-secret-key-that-should-be-in-env-vars"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- APP CONFIGURATION ---
UPLOAD_DIR = "student_images"
app = FastAPI(
    title="ML Attendance API with JWT",
    description="Backend for student attendance using FastAPI, MySQL, and Face Recognition."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB CONFIGURATION ---
# UPDATE THESE CREDENTIALS AS NEEDED
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',      # Default XAMPP/MySQL user
    'password': '',      # Default XAMPP password (empty)
    'database': 'attendance_system' # Ensure this matches your schema
}

# --- Pydantic Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

class AttendanceResponse(BaseModel):
    success: bool
    message: str
    student_id: Union[str, None] = None
    name: Union[str, None] = None
    timestamp: str

# --- JWT Utility Functions ---
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return TokenData(username=user_id)
    except JWTError:
        raise credentials_exception

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_token(token, credentials_exception)

# --- Database & ML Utilities ---

def get_db_connection():
    """Creates and returns a MySQL database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def load_known_faces():
    """Loads all face encodings from the database into memory."""
    known_encodings = []
    known_student_ids = []
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT student_id, face_vector FROM face_encodings")
        rows = cursor.fetchall()
        for row in rows:
            # Parse JSON string back to list/numpy array
            encoding = json.loads(row['face_vector'])
            known_encodings.append(np.array(encoding))
            known_student_ids.append(row['student_id'])
    except Error as e:
        print(f"Error loading faces: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            
    return known_encodings, known_student_ids

# Initialize cache
print("Loading known faces...")
# In a production app, you might want to refresh this periodically or on new registration
# For simplicity, we load it once at startup, but we'll also append to it dynamically on register.
global_known_encodings, global_known_student_ids = [], []

try:
    global_known_encodings, global_known_student_ids = load_known_faces()
    print(f"Loaded {len(global_known_student_ids)} faces from DB.")
except Exception as e:
    print(f"Startup Warning: Could not load faces. DB might be empty or unreachable. {e}")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- API ENDPOINTS ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if form_data.username == "admin" and form_data.password == "secret":
        access_token = create_access_token(data={"sub": form_data.username})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

@app.post("/api/register", response_model=dict)
async def register_student(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    student_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    course_id: int = Form(...),
    image: UploadFile = File(...)
):
    # 1. Check if student_id already exists in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail=f"Student ID {student_id} is already registered.")
    finally:
        cursor.close()
        conn.close()

    # 2. Process Image & Generate Encoding
    file_path = os.path.join(UPLOAD_DIR, f"{student_id}_{image.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Load image with face_recognition
    image_data = face_recognition.load_image_file(file_path)
    encodings = face_recognition.face_encodings(image_data)

    if len(encodings) == 0:
        os.remove(file_path) # Cleanup
        raise HTTPException(status_code=400, detail="No face detected in the image. Please try again.")
    
    if len(encodings) > 1:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Multiple faces detected. Please ensure only one person is in the frame.")

    new_encoding = encodings[0]

    # 3. Check for Duplicate Face (Prevent re-registration of same person)
    # Compare against all known faces
    if len(global_known_encodings) > 0:
        matches = face_recognition.compare_faces(global_known_encodings, new_encoding, tolerance=0.5)
        if True in matches:
            # Find who it matches
            match_index = matches.index(True)
            existing_id = global_known_student_ids[match_index]
            os.remove(file_path)
            raise HTTPException(status_code=409, detail=f"This person is already registered as {existing_id}.")

    # 4. Save to Database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Insert into students
        cursor.execute(
            "INSERT INTO students (student_id, first_name, last_name) VALUES (%s, %s, %s)",
            (student_id, first_name, last_name)
        )
        
        # Insert into face_encodings
        # Serialize numpy array to list then to JSON string
        encoding_json = json.dumps(new_encoding.tolist())
        cursor.execute(
            "INSERT INTO face_encodings (student_id, face_vector, image_path) VALUES (%s, %s, %s)",
            (student_id, encoding_json, file_path)
        )
        
        conn.commit()
        
        # Update memory cache
        global_known_encodings.append(new_encoding)
        global_known_student_ids.append(student_id)
        
        return {"message": f"Student {first_name} {last_name} ({student_id}) registered successfully."}

    except Error as e:
        conn.rollback()
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error during registration.")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/capture", response_model=AttendanceResponse)
async def capture_attendance(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    image: UploadFile = File(...)
):
    # 1. Load Image
    # We can load directly from the spooled file without saving to disk first for speed,
    # but face_recognition needs a file-like object or numpy array.
    # Saving temp file is safer for now.
    temp_filename = f"temp_{datetime.utcnow().timestamp()}.jpg"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    timestamp = datetime.utcnow().isoformat() + "Z"

    try:
        image_data = face_recognition.load_image_file(temp_filename)
        encodings = face_recognition.face_encodings(image_data)

        if len(encodings) == 0:
            return AttendanceResponse(success=False, message="No face detected.", timestamp=timestamp)

        # Use the first face found
        unknown_encoding = encodings[0]

        # 2. Compare with Known Faces
        if not global_known_encodings:
             return AttendanceResponse(success=False, message="No registered students in database.", timestamp=timestamp)

        # Calculate distances to find the best match
        face_distances = face_recognition.face_distance(global_known_encodings, unknown_encoding)
        best_match_index = np.argmin(face_distances)
        
        # Tolerance: Lower is stricter. 0.6 is default, 0.5 is better for security.
        if face_distances[best_match_index] < 0.5:
            student_id = global_known_student_ids[best_match_index]
            
            # 3. Fetch Student Details & Log Attendance
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                # Get Name
                cursor.execute("SELECT first_name, last_name FROM students WHERE student_id = %s", (student_id,))
                student = cursor.fetchone()
                student_name = f"{student['first_name']} {student['last_name']}" if student else "Unknown"

                # Log to DB
                cursor.execute(
                    "INSERT INTO attendance (student_id, status) VALUES (%s, 'PRESENT')",
                    (student_id,)
                )
                conn.commit()
                
                return AttendanceResponse(
                    success=True,
                    message="Attendance recorded.",
                    student_id=student_id,
                    name=student_name,
                    timestamp=timestamp
                )
            except Error as e:
                print(f"DB Error: {e}")
                return AttendanceResponse(success=False, message="Database error logging attendance.", timestamp=timestamp)
            finally:
                cursor.close()
                conn.close()
        else:
            return AttendanceResponse(success=False, message="Face not recognized.", timestamp=timestamp)

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)