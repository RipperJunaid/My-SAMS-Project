"""
Database Handler for SmartFace Attendance System v2.0
SQLite database for storing users, students and attendance records
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional
import json
import hashlib


class AttendanceDB:
    """SQLite database handler for attendance system"""

    def __init__(self, db_path: str = "attendance.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Create tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Students table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Attendance table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
        """)

        # Users table for authentication
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """)

        conn.commit()
        
        # Create default admin user
        cursor.execute("SELECT username FROM users WHERE username = ?", ("Basim",))
        if not cursor.fetchone():
            password_hash = hashlib.sha256("cr@7".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("Basim", password_hash, "admin")
            )
            conn.commit()
            print("✅ Admin user 'Basim' created")
        
        conn.close()
        print("✅ Database initialized successfully")

    def add_user(self, username: str, password: str, role: str):
        """Add a new user to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            conn.commit()
            print(f"✅ User added: {username} ({role})")
        except sqlite3.IntegrityError:
            raise ValueError(f"Username {username} already exists")
        finally:
            conn.close()

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """Verify user credentials and return user info"""
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "SELECT username, role FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def add_student(self, student_id: str, name: str, image_path: str):
        """Add a new student to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO students (student_id, name, image_path)
            VALUES (?, ?, ?)
            """, (student_id, name, image_path))
            conn.commit()
            print(f"Student added: {name} ({student_id})")
        except sqlite3.IntegrityError:
            raise ValueError(f"Student ID {student_id} already exists")
        finally:
            conn.close()

    def get_student(self, student_id: str) -> Optional[Dict]:
        """Get student by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def get_all_students(self) -> List[Dict]:
        """Get all registered students"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_attendance(self, student_id: str, name: str) -> int:
        """Mark attendance for a student"""
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()

        # Check if already marked today
        cursor.execute("""
        SELECT id FROM attendance
        WHERE student_id = ? AND date = ?
        """, (student_id, today))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return existing[0]

        # Mark new attendance
        cursor.execute("""
        INSERT INTO attendance (student_id, name, date)
        VALUES (?, ?, ?)
        """, (student_id, name, today))
        attendance_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"Attendance marked: {name} ({student_id})")
        return attendance_id

    def get_attendance_records(self, date_filter: str = None, student_id: str = None) -> List[Dict]:
        """Get attendance records with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM attendance WHERE 1=1"
        params = []

        if date_filter:
            query += " AND date = ?"
            params.append(date_filter)
        if student_id:
            query += " AND student_id = ?"
            params.append(student_id)

        query += " ORDER BY marked_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_today_attendance_count(self) -> int:
        """Get count of attendance marked today"""
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]

        # Total attendance records
        cursor.execute("SELECT COUNT(*) FROM attendance")
        total_attendance = cursor.fetchone()[0]

        # Today's attendance
        today = date.today().isoformat()
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
        today_attendance = cursor.fetchone()[0]

        # This week's attendance
        cursor.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE date >= date('now', '-7 days')
        """)
        week_attendance = cursor.fetchone()[0]

        # Attendance rate today
        attendance_rate = 0
        if total_students > 0:
            attendance_rate = round((today_attendance / total_students) * 100, 2)

        # Recent attendance
        cursor.execute("""
        SELECT student_id, name, marked_at
        FROM attendance
        ORDER BY marked_at DESC
        LIMIT 10
        """)
        recent_records = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "total_students": total_students,
            "total_attendance_records": total_attendance,
            "today_attendance": today_attendance,
            "week_attendance": week_attendance,
            "attendance_rate": attendance_rate,
            "recent_attendance": recent_records
        }

    def delete_student(self, student_id: str):
        """Delete a student and their attendance records"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
        conn.close()
        print(f"Student deleted: {student_id}")

    def get_attendance_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get attendance records within date range"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM attendance
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, marked_at DESC
        """, (start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
