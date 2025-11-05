📚 Full-Stack ML Attendance System (FastAPI + MySQL + Face Recognition)

This repository contains the blueprints for a student attendance system that uses FastAPI for the backend API, MySQL for data storage, and Python's ML libraries (like face_recognition or OpenCV/dlib) for face recognition.

1. Prerequisites

You must have the following installed:

Python 3.8+

MySQL Server (and a local database instance running)

For ML: You will likely need dlib (a dependency for face_recognition), which can be tricky to install. It often requires CMake and system build tools.

2. Backend Setup (FastAPI & Python)

a. Installation

Create a virtual environment and install the required Python packages, including python-jose for JWT handling:

pip install fastapi uvicorn pydantic python-multipart sqlalchemy mysql-connector-python face-recognition python-jose[cryptography]



b. Database Connection

Ensure your MySQL server is running.

Apply the schema from schema.sql.

In main.py, you will need to replace the placeholder strings with your actual MySQL credentials and connection logic (e.g., using SQLAlchemy's engine).

c. Running the API

Run the FastAPI server using Uvicorn:

uvicorn main:app --reload



The API documentation (Swagger UI) will be available at http://127.0.0.1:8000/docs.

3. Authentication (JWT)

The system now requires authentication to use the registration and attendance endpoints.

Login Endpoint: /token (Public)

Method: POST, requires form data (username, password).

Default Demo Credentials: username: admin, password: secret

The frontend automatically handles the JWT process: it sends the credentials to /token, stores the returned access token, and includes it in the Authorization: Bearer <token> header for all subsequent protected API calls.

4. Machine Learning Integration

The attendance system works by:

Registration (/api/register): (Requires JWT)

The user uploads a picture.

The ML model calculates a 128-dimensional numerical vector (the "encoding") of the student's face.

This numerical vector is serialized (e.g., to a JSON string) and stored in the face_encodings table, linked to the student_id.

Attendance Capture (/api/capture): (Requires JWT)

The system receives a live image (or video frame).

The ML model calculates the encoding for the new image.

It queries all stored encodings from the face_encodings table and finds the best match.

If a match is found, attendance is logged in the attendance table.

5. Frontend (UI)

The index.html file provides a great UI. You must log in using the credentials mentioned in Section 3 before attempting to register students or capture attendance.
