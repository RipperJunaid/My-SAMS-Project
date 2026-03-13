"""
SmartFace Attendance System v2.0 - Main Application
Modern face recognition attendance system with authentication
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
import os
from pathlib import Path
import json

# Import our modules
from face_engine import FaceRecognitionEngine
from database import AttendanceDB

# Initialize FastAPI
app = FastAPI(title="SmartFace Attendance System", version="2.0.0")

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
face_engine = FaceRecognitionEngine()
db = AttendanceDB()

# Create necessary directories
Path("faces/registered").mkdir(parents=True, exist_ok=True)
Path("faces/temp").mkdir(parents=True, exist_ok=True)
Path("static").mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/faces", StaticFiles(directory="faces"), name="faces")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML page"""
    try:
        with open("frontend.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>frontend.html not found</h1>", status_code=404)


@app.get("/api", tags=["Health"])
async def api_health_check():
    """API Health Check"""
    return {
        "status": "online",
        "message": "SmartFace Attendance System API",
        "version": "2.0.0",
        "endpoints": {
            "login": "/api/login",
            "create_user": "/api/users/create",
            "register": "/api/register",
            "recognize": "/api/recognize",
            "attendance": "/api/attendance",
            "stats": "/api/stats"
        }
    }


@app.post("/api/login", tags=["Authentication"])
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Login endpoint - Authenticates user credentials
    
    Args:
        username: User's username
        password: User's password
        
    Returns:
        access_token, token_type, role, username
    """
    try:
        # Verify user credentials using database
        user = db.verify_user(username, password)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )
        
        # Return authentication token and user info
        return {
            "access_token": f"token_{username}_{datetime.now().timestamp()}",
            "token_type": "bearer",
            "role": user["role"],
            "username": user["username"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/api/users/create", tags=["User Management"])
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    """
    Create a new user account
    
    Args:
        username: User's username
        email: User's email (for frontend validation)
        password: User's password
        role: User's role (student, teacher, admin)
    
    Returns:
        Success message with user details
    """
    try:
        # Check if username already exists
        existing_user = db.get_user(username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail=f"Username '{username}' already exists"
            )
        
        # Create new user
        db.add_user(username, password, role)
        
        return {
            "success": True,
            "message": f"User '{username}' created successfully",
            "username": username,
            "role": role
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")


@app.post("/api/register", tags=["Student Management"])
async def register_student(
    name: str = Form(...),
    student_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Register a new student with their face image
    """
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "File must be an image")
        contents = await file.read()
        image_path = face_engine.save_face_image(student_id, name, contents)
        db.add_student(student_id, name, image_path)
        return {
            "success": True, 
            "message": f"Student {name} registered successfully", 
            "student_id": student_id, 
            "image_path": image_path
        }
    except Exception as e:
        raise HTTPException(500, f"Registration failed: {str(e)}")


@app.post("/api/recognize", tags=["Attendance"])
async def recognize_face(file: UploadFile = File(...)):
    """Recognize a face and mark attendance"""
    temp_path = "faces/temp/capture.jpg"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
        result = face_engine.recognize_face(temp_path)
        if result["recognized"]:
            student_id = result["student_id"]
            name = result["name"]
            confidence = result["confidence"]
            attendance_id = db.mark_attendance(student_id, name)
            today_count = db.get_today_attendance_count()
            return {
                "success": True,
                "recognized": True,
                "student_id": student_id,
                "name": name,
                "confidence": confidence,
                "attendance_id": attendance_id,
                "timestamp": datetime.now().isoformat(),
                "today_total": today_count,
                "message": f"Welcome {name}! Attendance marked successfully."
            }
        else:
            return {
                "success": True, 
                "recognized": False, 
                "message": "Face not recognized. Please register first."
            }
    except Exception as e:
        raise HTTPException(500, f"Recognition failed: {str(e)}")
    finally:
        if os.path.exists(temp_path): 
            os.remove(temp_path)


@app.get("/api/attendance", tags=["Attendance"])
async def get_attendance(date: str = None, student_id: str = None):
    """Get attendance records"""
    try:
        records = db.get_attendance_records(date, student_id)
        return {"success": True, "count": len(records), "records": records}
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch attendance: {str(e)}")


@app.get("/api/students", tags=["Student Management"])
async def get_students():
    """Get all registered students"""
    try:
        students = db.get_all_students()
        return {"success": True, "count": len(students), "students": students}
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch students: {str(e)}")


@app.get("/api/stats", tags=["Statistics"])
async def get_statistics():
    """Get attendance statistics"""
    try:
        stats = db.get_statistics()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch statistics: {str(e)}")


@app.delete("/api/student/{student_id}", tags=["Student Management"])
async def delete_student(student_id: str):
    """Delete a student record"""
    try:
        db.delete_student(student_id)
        return {"success": True, "message": f"Student {student_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(500, f"Failed to delete student: {str(e)}")


if __name__ == "__main__":
    print("="*60)
    print("SmartFace Attendance System v2.0 - Starting Server")
    print("="*60)
    print("🌐 UI: http://localhost:8000/")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔑 API Base: http://localhost:8000/api")
    print("="*60)
    print("\n🔐 Default Admin Login:")
    print("   Username: Basim")
    print("   Password: cr@7")
    print("="*60)
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
