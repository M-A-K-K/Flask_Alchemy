from flask import  Blueprint, request, jsonify, abort, Flask
from app.models import User
from app.schemas import user_schema, users_schema
from app.utils.auth import authenticate
from app import db
from app.models import Subject
from flask import request, jsonify, abort
from app import db, logger  # Assuming authenticate function is defined somewhere
from ..utils.auth import authenticate
from ..utils.encryption import encrypt_data, decrypt_data
from app.models import Subject, User  # Adjust based on your models import


app = Flask(__name__)
users_bp = Blueprint('users', __name__)

@app.route("/add_user_info", methods=["POST"])
def add_user_info():
    try:
        authenticate()  # Ensure the request is authenticated 
        user_data = request.json
        if not user_data:
            abort(400, description="Missing user data") 
        
        # Validate user data
        validate_user_data(user_data)
        
        # Check if the user already exists based on name, age, and gender
        existing_user = find_existing_user(user_data)
        if existing_user:
            return jsonify({"message": "User data already exists",
                            "user_id": existing_user.id})
        
        # Create new user and add to database
        new_user = User(name=user_data["name"], age=user_data["age"], gender=user_data["gender"])
        db.session.add(new_user)
        db.session.commit()

        logger.info(f"User added: {new_user}")
        
        return jsonify({"user_id": new_user.id})
    
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        return jsonify({"error": str(e)}), 500

def validate_user_data(user_data):
    # Validating age
    if not isinstance(user_data.get("age"), int) or user_data.get("age") < 0:
        abort(400, description="Invalid age. Age must be a non-negative integer.")
    
    # Validating name
    if not isinstance(user_data.get("name"), str) or not user_data.get("name").strip():
        abort(400, description="Invalid name. Name must be a non-empty string.")
    
    # Validating gender (assuming gender can only be "male" or "female")
    if (not isinstance(user_data.get("gender"), str) or
        not user_data.get("gender").strip() or
            user_data.get("gender") not in ["male", "female"]):
        abort(400, description="Invalid gender. Gender must be 'male' or 'female'.")

def find_existing_user(new_user_data):

    existing_user = User.query.filter_by(
        name=new_user_data["name"], 
        age=new_user_data["age"], 
        gender=new_user_data["gender"]
    ).first()
    return existing_user


@app.route("/get_user_info", methods=["GET"])
def get_user_info():
    try:
        authenticate()  # Ensure the request is authenticated
        
        # Query specific fields from User table
        users = User.query.with_entities(User.id, User.name, User.age, User.gender).all()
        
        # Prepare result as list of dictionaries
        result = []
        for user in users:
            user_dict = {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "gender": user.gender
            }
            result.append(user_dict)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return jsonify({"error": str(e)}), 500



    try:
        authenticate()  # Ensure the request is authenticated
        
        # Get user ID from the request JSON body
        user_id = request.json.get("user_id")
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400
        
        # Query specific user by ID from User table
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({"error": "User not found."}), 404
        
        # Prepare result as dictionary
        user_dict = {
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "gender": user.gender
        }
        
        return jsonify(user_dict)
    
    except Exception as e:
        logger.error(f"Error getting user by ID: {str(e)}")
        return jsonify({"error": "Failed to retrieve user information"}), 500

@app.route("/get_user_by_id", methods=["POST"])
def get_user_and_subjects_by_id():
    try:
        authenticate()  # Ensure the request is authenticated
        
        # Get user ID from the request JSON body
        user_id = request.json.get("user_id")
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400
        
        # Query specific user by ID from User table
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({"error": "User not found."}), 404
        
        # Prepare user data as dictionary
        user_dict = {
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "gender": user.gender
        }
        
        # Query subjects for the specific user by user_id
        subjects = Subject.query.filter_by(user_id=user_id).all()
        
        # Prepare subjects data as a list of dictionaries
        subjects_list = []
        for subject in subjects:
            try:
                decrypted_grade = decrypt_data(subject.encrypted_grade, private_key)
                subject_dict = {
                    "subject_id": subject.subject_id,
                    "subject_name": subject.subject_name,
                    "grade": decrypted_grade.decode('utf-8')  # Convert bytes to UTF-8 string
                }
                subjects_list.append(subject_dict)
            except Exception as e:
                logger.error(f"Error decrypting grade for subject ID {subject.subject_id}: {str(e)}")
                continue
        
        # Add subjects data to user data
        user_dict["subjects"] = subjects_list
        
        return jsonify(user_dict)
    
    except Exception as e:
        logger.error(f"Error getting user and subjects by ID: {str(e)}")
        return jsonify({"error": "Failed to retrieve user and subject information"}), 500

@app.route("/update_user_info", methods=["PUT"])
def update_user_info():
    try:
        authenticate()  # Ensure the request is authenticated

        # Get user data from the request JSON body
        user_data = request.json
        if not user_data or not user_data.get("id"):
            abort(400, description="User ID is required for updating user info.")

        # Find the user in the database
        user = User.query.get(user_data["id"])
        if not user:
            abort(404, description="User not found.")

        # Update user fields
        if "name" in user_data:
            user.name = user_data["name"]
        if "age" in user_data:
            user.age = user_data["age"]
        if "gender" in user_data:
            user.gender = user_data["gender"]

        # Update user's subjects if provided
        if "subjects" in user_data:
            for subject_data in user_data["subjects"]:
                subject_id = subject_data.get("subject_id")
                if subject_id:
                    # Find the subject in the database
                    subject = Subject.query.get(subject_id)
                    if subject:
                        if "subject_name" in subject_data:
                            subject.subject_name = subject_data["subject_name"]
                        if "grade" in subject_data:
                            # Example: Decrypt grade if needed
                            decrypted_grade = decrypt_data(subject.encrypted_grade, private_key)
                            # Assuming you update encrypted_grade
                            subject.encrypted_grade = encrypt_data(subject_data["grade"], public_key)
                    else:
                        abort(404, description=f"Subject with ID {subject_id} not found.")
                else:
                    abort(400, description="Subject ID is required for updating subject info.")

        db.session.commit()  # Commit changes to the database

        logger.info(f"User info updated: {user}")

        return jsonify({"message": "User data updated successfully", "user_id": user.id})

    except Exception as e:
        logger.error(f"Error updating user info: {str(e)}")
        return jsonify({"error": str(e)}), 500
