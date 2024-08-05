from flask import Blueprint, request, jsonify, abort, Flask
from ..models import Subject
from ..schemas import subject_schema, subjects_schema
from ..utils.auth import authenticate
from ..utils.encryption import encrypt_data, decrypt_data
from .. import db
import logging


app = Flask(__name__)
logger = logging.getLogger(__name__)

subjects_bp = Blueprint('subjects', __name__)


@app.route("/add_subject", methods=["POST"])
def add_subject():
    try:
        authenticate()  # Ensure the request is authenticated
        subject_data = request.json
        if not subject_data:
            abort(400, description="Missing subject data")
        
        # Validate subject data
        validate_subject_data(subject_data)
        
        # Check if the subject already exists for the user
        existing_subject = Subject.query.filter_by(
            subject_name=subject_data["subject_name"],
            user_id=subject_data["user_id"]
        ).first()
        
        if existing_subject:
            return jsonify({
                "message": "Subject already exists for this user",
                "subject_id": existing_subject.subject_id
            })
        
        # Encrypt grade using RSA public key
        grade = subject_data["grade"]
        encrypted_grade = encrypt_data(grade, public_key)
        
        # Create new subject and add to database
        new_subject = Subject(
            subject_name=subject_data["subject_name"],
            encrypted_grade=encrypted_grade,
            user_id=subject_data["user_id"]
        )
        db.session.add(new_subject)
        db.session.commit()
        
        logger.info(f"Subject added: {new_subject}")
        
        return jsonify({"subject_id": new_subject.subject_id})
    
    except Exception as e:
        logger.error(f"Error adding subject: {str(e)}")
        return jsonify({"error": str(e)}), 500

def validate_subject_data(subject_data):
    # Validating subject name
    if not isinstance(subject_data.get("subject_name"), str) or not subject_data.get("subject_name").strip():
        abort(400, description="Invalid subject name. Subject name must be a non-empty string.")
    
    # Validating grade
    if not isinstance(subject_data.get("grade"), str) or not subject_data.get("grade").strip():
        abort(400, description="Invalid grade. Grade must be a non-empty string.")
    
    # Validating user_id
    if not isinstance(subject_data.get("user_id"), int) or subject_data.get("user_id") <= 0:
        abort(400, description="Invalid user ID. User ID must be a positive integer.")


@app.route("/get_subject_info", methods=["GET"])
def get_subject_info():
    try:
        authenticate()  # Ensure the request is authenticated
        
        # Query all subjects
        subjects = Subject.query.all()
        
        # Prepare result with decrypted grades
        result = []
        for subject in subjects:
            try:
                decrypted_grade = decrypt_data(subject.encrypted_grade, private_key)
                subject_dict = {
                    "subject_id": subject.subject_id,
                    "subject_name": subject.subject_name,
                    "grade": decrypted_grade.decode('utf-8')  # Convert bytes to UTF-8 string
                }
                result.append(subject_dict)
            except Exception as e:
                logger.error(f"Error decrypting grade for subject ID {subject.subject_id}: {str(e)}")
                continue
        
        # Log the result before returning
        logger.info(f"Retrieved {len(result)} subjects successfully")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting subject info: {str(e)}")
        return jsonify({"error": "Failed to retrieve subject information"}), 500
