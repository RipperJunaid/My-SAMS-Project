"""
Face Recognition Engine using DeepFace
Handles all face recognition operations
"""

from deepface import DeepFace
import cv2
import os
from pathlib import Path
import numpy as np
from typing import Dict, Optional


class FaceRecognitionEngine:
    """Face recognition engine powered by DeepFace"""
    
    def __init__(self, model_name="Facenet512", detector_backend="opencv"):
        """
        Initialize face recognition engine
        
        Args:
            model_name: DeepFace model (VGG-Face, Facenet, Facenet512, OpenFace, DeepFace, DeepID, ArcFace, Dlib, SFace)
            detector_backend: Face detector (opencv, ssd, dlib, mtcnn, retinaface, mediapipe)
        """
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.faces_db_path = "faces/registered"
        
        print(f"Initializing Face Engine with model: {model_name}")
        
        # Ensure directory exists
        Path(self.faces_db_path).mkdir(parents=True, exist_ok=True)
    
    def save_face_image(self, student_id: str, name: str, image_data: bytes) -> str:
        """
        Save face image for a student
        
        Args:
            student_id: Unique student ID
            name: Student name
            image_data: Image bytes
            
        Returns:
            Path to saved image
        """
        # Create filename
        filename = f"{student_id}_{name.replace(' ', '_')}.jpg"
        filepath = os.path.join(self.faces_db_path, filename)
        
        # Save image
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        # Verify face is detected
        try:
            face = DeepFace.extract_faces(
                img_path=filepath,
                detector_backend=self.detector_backend,
                enforce_detection=True
            )
            
            if not face:
                os.remove(filepath)
                raise ValueError("No face detected in image")
                
            print(f"Face registered: {name} ({student_id})")
            return filepath
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise ValueError(f"Face detection failed: {str(e)}")
    
    def recognize_face(self, image_path: str, distance_threshold: float = 0.6) -> Dict:
        """
        Recognize a face from image
        
        Args:
            image_path: Path to image file
            distance_threshold: Maximum distance for match (lower = stricter)
            
        Returns:
            Dictionary with recognition results
        """
        try:
            # Check if database has any faces
            registered_faces = [f for f in os.listdir(self.faces_db_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
            
            if not registered_faces:
                return {
                    "recognized": False,
                    "message": "No registered faces in database"
                }
            
            # Perform face recognition
            results = DeepFace.find(
                img_path=image_path,
                db_path=self.faces_db_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                silent=True
            )
            
            # Check if any face found
            if len(results) == 0 or len(results[0]) == 0:
                return {
                    "recognized": False,
                    "message": "No matching face found"
                }
            
            # Get best match
            best_match = results[0].iloc[0]
            distance = best_match['distance']
            matched_image = best_match['identity']
            
            # Check if within threshold
            if distance > distance_threshold:
                return {
                    "recognized": False,
                    "message": f"Face similarity too low (distance: {distance:.3f})"
                }
            
            # Extract student info from filename
            filename = os.path.basename(matched_image)
            parts = filename.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
            
            if '_' in parts:
                student_id = parts.split('_')[0]
                name = ' '.join(parts.split('_')[1:])
            else:
                student_id = parts
                name = "Unknown"
            
            confidence = round((1 - distance) * 100, 2)
            
            return {
                "recognized": True,
                "student_id": student_id,
                "name": name,
                "confidence": confidence,
                "distance": round(distance, 4),
                "model": self.model_name
            }
            
        except Exception as e:
            print(f"Recognition error: {str(e)}")
            return {
                "recognized": False,
                "message": f"Recognition failed: {str(e)}"
            }
    
    def verify_face(self, image1_path: str, image2_path: str) -> Dict:
        """
        Verify if two images contain the same person
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            
        Returns:
            Verification result
        """
        try:
            result = DeepFace.verify(
                img1_path=image1_path,
                img2_path=image2_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            
            return {
                "verified": result['verified'],
                "distance": result['distance'],
                "threshold": result['threshold'],
                "model": result['model']
            }
            
        except Exception as e:
            return {
                "verified": False,
                "message": f"Verification failed: {str(e)}"
            }
    
    def analyze_face(self, image_path: str) -> Dict:
        """
        Analyze face attributes (age, gender, emotion, race)
        
        Args:
            image_path: Path to image
            
        Returns:
            Analysis results
        """
        try:
            analysis = DeepFace.analyze(
                img_path=image_path,
                actions=['age', 'gender', 'emotion'],
                detector_backend=self.detector_backend,
                enforce_detection=False,
                silent=True
            )
            
            if isinstance(analysis, list):
                analysis = analysis[0]
            
            return {
                "success": True,
                "age": analysis.get('age'),
                "gender": analysis.get('dominant_gender'),
                "emotion": analysis.get('dominant_emotion'),
                "emotions": analysis.get('emotion')
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Analysis failed: {str(e)}"
            }
    
    def get_registered_count(self) -> int:
        """Get count of registered faces"""
        faces = [f for f in os.listdir(self.faces_db_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
        return len(faces)
