import os
import shutil
import json # Added for face_vector serialization
from typing import List, Union, Annotated
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette import status

# --- SECURITY CONFIGURATION ---
# IMPORTANT: Change this key and keep it secret in a real application!
SECRET_KEY = "your-very-secret-key-that-should-be-in-env-vars"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- APP CONFIGURATION ---
UPLOAD_DIR = "student_images" # Directory where registration images will be stored
app = FastAPI(
    title="ML Attendance API with JWT",
    description="Backend for student attendance using FastAPI, Pydantic, MySQL, and JWT Auth."
)

# Configure CORS to allow the frontend (index.html) to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---

class StudentRegistration(BaseModel):
    """Schema for a new student registration (used for internal data handling)."""
    student_id: str = Field(..., example="S2025001")
    first_name: str = Field(..., example="Alex")
    last_name: str = Field(..., example="Johnson")
    course_id: int = Field(..., example=101)

class AttendanceResponse(BaseModel):
    """Schema for the attendance capture result."""
    success: bool
    message: str
    student_id: Union[str, None] = None
    name: Union[str, None] = None
    timestamp: str

class Token(BaseModel):
    """Schema for the JWT response."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for data stored within the JWT payload."""
    username: Union[str, None] = None

# --- JWT Utility Functions ---

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    """Verifies and decodes the JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(username=user_id)
    except JWTError:
        raise credentials_exception
    return token_data

# Mock User Database/Getter (for Auth and Dependency)
def get_user_from_db(user_id: str):
    """Mocks fetching user data based on ID (for authentication context)."""
    # In a real app, query a 'users' table
    if user_id == "admin":
        return {"user_id": "admin", "full_name": "System Administrator"}
    return None

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """FastAPI dependency to validate JWT and return the user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token, credentials_exception)
    user = get_user_from_db(token_data.username)
    if user is None:
        raise credentials_exception
    return user

# --- ML & DB Utility (Mocked) ---

def initialize_ml_and_db():
    """Initializes ML model cache and DB connection."""
    print("--- 1. Initialize MySQL Connection (SQLAlchemy) ---")
    # TODO: Initialize SQLAlchemy engine and session here.
    # e.g., engine = create_engine("mysql+mysqlconnector://user:pass@host/db")
    
    print("--- 2. Load Face Encodings into Memory Cache ---")
    # TODO: Load all existing face vectors from the 'face_encodings' MySQL table
    # into a structure suitable for real-time comparison.
    
    # Ensure the upload directory exists
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

# Call initialization on startup
initialize_ml_and_db()


def save_image_and_get_encoding(student_id: str, image_file: UploadFile):
    """Saves the image and performs ML processing (mocked)."""
    # 1. Save the file to disk
    file_path = os.path.join(UPLOAD_DIR, f"{student_id}_{image_file.filename}")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # 2. ML Logic Placeholder
    print(f"--- ML TASK: Processing {file_path} ---")
    # TODO: Load the image, detect the face, and calculate the 128D encoding vector.
    
    # Mock Encoding (In a real app, this would be the actual 128D vector)
    mock_encoding_vector = [0.12, 0.55, 0.01, 0.88] # 4 floats for simplicity here
    
    # 3. DB Logic Placeholder
    print(f"--- DB TASK: Saving encoding for {student_id} to MySQL ---")
    # TODO: Insert the student info into the 'students' table.
    # The encoding must be serialized (e.g., json.dumps(mock_encoding_vector))
    # before storing in the TEXT field of 'face_encodings'.

    return {
        "encoding_vector_length": len(mock_encoding_vector),
        "storage_path": file_path
    }


def perform_face_recognition(image_file: UploadFile):
    """Performs recognition against stored encodings (mocked)."""
    # 1. ML Logic Placeholder
    # TODO: Load image_file, detect face, calculate new encoding.
    
    # 2. Matching Logic Placeholder
    # TODO: Compare the new encoding against the cached encodings (from MySQL).
    
    # Mock Match Result
    # Simulate a successful match
    mock_match_id = "S2025001"
    mock_student_name = "Alex Johnson"
    is_recognized = True
    
    # For demonstration: If the filename contains 'unknown', simulate failure
    if 'unknown' in image_file.filename.lower():
         is_recognized = False

    # 3. DB Logic Placeholder
    if is_recognized:
        print(f"--- DB TASK: Logging attendance for {mock_match_id} ---")
        # TODO: Insert a new record into the 'attendance' table.
        
    return is_recognized, mock_match_id, mock_student_name

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "Attendance API is running. See /docs for endpoints. Use /token to authenticate."}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Authenticates user and returns a JWT access token."""
    
    # --- MOCK CREDENTIAL CHECK ---
    # In a real app, hash the password (e.g., using passlib) and check against the DB.
    if form_data.username == "admin" and form_data.password == "secret":
        access_token = create_access_token(
            data={"sub": form_data.username}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.post("/api/register", response_model=dict)
async def register_student(
    current_user: Annotated[dict, Depends(get_current_user)], # PROTECTED ROUTE
    student_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    course_id: int = Form(...),
    image: UploadFile = File(...)
):
    """Registers a new student's face encoding in the database."""
    print(f"User authenticated: {current_user['user_id']}")
    
    # Input Validation (e.g., check if student_id already exists)
    if student_id == "S2025002":
        raise HTTPException(status_code=409, detail="Student ID already registered.")
        
    try:
        result = save_image_and_get_encoding(student_id, image)
        
        return {
            "message": f"Student {first_name} {lastName} registered successfully. Encoding calculated.",
            "student_id": student_id,
            "encoding_vector_length": result['encoding_vector_length'],
            "storage_path": result['storage_path']
        }
    except Exception as e:
        print(f"Registration Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during registration.")


@app.post("/api/capture", response_model=AttendanceResponse)
async def capture_attendance(
    current_user: Annotated[dict, Depends(get_current_user)], # PROTECTED ROUTE
    image: UploadFile = File(...)
):
    """Captures an image, runs face recognition, and logs attendance."""
    print(f"User authenticated: {current_user['user_id']}")

    recognized, student_id, student_name = perform_face_recognition(image)
    
    timestamp = str(datetime.utcnow().isoformat() + "Z") # Use current time

    if recognized:
        # Mock student ID and name if recognized successfully (since the ML part is mocked)
        if not student_id:
             student_id = "S2025001"
             student_name = "Alex Johnson"

        return AttendanceResponse(
            success=True,
            message=f"Attendance recorded for {student_name} ({student_id}).",
            student_id=student_id,
            name=student_name,
            timestamp=timestamp
        )
    else:
        return AttendanceResponse(
            success=False,
            message="Face not recognized. Please register or try again.",
            student_id=None,
            name=None,
            timestamp=timestamp
        )