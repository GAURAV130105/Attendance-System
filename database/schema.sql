-- --------------------------------------------------------
-- Database Schema for ML-Powered Attendance System
-- Technology: MySQL
-- --------------------------------------------------------

-- Students Table: Stores static student profile information.
CREATE TABLE students (
    student_id VARCHAR(50) PRIMARY KEY, -- Unique ID, e.g., 'S12345'
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    major VARCHAR(100),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Courses/Classes Table: Defines the classes for which attendance is taken.
CREATE TABLE courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(10) UNIQUE NOT NULL, -- e.g., 'CS401'
    course_name VARCHAR(255) NOT NULL,
    teacher_name VARCHAR(100)
);

-- Face Encodings Table: Stores the ML data (128D vectors) for recognition.
CREATE TABLE face_encodings (
    encoding_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    -- Store the 128-dimensional face vector as a JSON string or BLOB/TEXT
    face_vector TEXT NOT NULL,
    image_path VARCHAR(255), -- Path to the original registration image
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Attendance Log Table: Records every successful attendance event.
CREATE TABLE attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    course_id INT,
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('PRESENT', 'LATE', 'UNKNOWN') DEFAULT 'PRESENT',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE SET NULL
);