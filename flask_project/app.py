from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import secrets
import logging
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/alchemy'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app)

db = SQLAlchemy(app)
ma = Marshmallow(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Random secret key for session management
app.secret_key = secrets.token_hex(16)

API_KEY = 'kabirhere'  # Replace with your actual API key

def generate_rsa_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

private_key, public_key = generate_rsa_keys()

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=False, nullable=False)
    age = db.Column(db.Integer, unique=False, nullable=False)
    gender = db.Column(db.String(10), unique=False, nullable=False)

    subjects = db.relationship('Subject', back_populates='user')

    def __init__(self, name, age, gender):
        self.name = name
        self.age = age
        self.gender = gender

class Subject(db.Model):
    __tablename__ = 'subject'
    subject_id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(50), nullable=False)
    encrypted_grade = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', back_populates='subjects')

    def __init__(self, subject_name, encrypted_grade, user_id):
        self.subject_name = subject_name
        self.encrypted_grade = encrypted_grade
        self.user_id = user_id

# Database Schema
class UserSchema(ma.SQLAlchemyAutoSchema):
    subjects = ma.Nested('SubjectSchema', many=True)  # Nested serialization for subjects

    class Meta:
        model = User
        fields = ('id', 'name', 'age', 'gender', 'subjects')

class SubjectSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Subject
        fields = ('subject_id', 'subject_name', 'encrypted_grade', 'user_id')

# Marshmallow Schemas
user_schema = UserSchema()
users_schema = UserSchema(many=True)
subject_schema = SubjectSchema()
subjects_schema = SubjectSchema(many=True)

# Authentication Middleware
def authenticate():
    api_key = request.headers.get('ApiKey')
    if api_key != API_KEY:
        abort(401, description="Unauthorized")
    return "API Key is verified"

# Function to encrypt data with RSA public key
def encrypt_data(data, public_key):
    encrypted_data = public_key.encrypt(
        data.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted_data

# Function to decrypt data with RSA private key
def decrypt_data(encrypted_data, private_key):
    try:
        decrypted_data = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_data
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        raise  # Re-raise the exception to propagate the error up



@app.route("/")
def home_route():
    return "Home Route!"

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
                subject_id = subject_data.get("id")
                if subject_id:
                    # Find the subject in the database
                    subject = Subject.query.get(subject_id)
                    if subject:
                        if "name" in subject_data:
                            subject.name = subject_data["name"]
                        if "credits" in subject_data:
                            subject.credits = subject_data["credits"]
                    else:
                        abort(404, description=f"Subject with ID {subject_id} not found.")
                else:
                    abort(400, description="Subject ID is required for updating subject info.")

        db.session.commit()

        logger.info(f"User info updated: {user}")

        return jsonify({"message": "User data updated successfully", "user_id": user.id})

    except Exception as e:
        logger.error(f"Error updating user info: {str(e)}")
        return jsonify({"error": str(e)}), 500


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



if __name__ == "__main__":
    # Create tables based on models
    with app.app_context():
        db.create_all()
    app.run(debug=True)




# #-----------------------------------------------------------------------
# # just checking code generated by chat gpt for encryption and ecryption 
# # from flask import Flask, request, jsonify
# # from cryptography.hazmat.primitives import serialization
# # from cryptography.hazmat.primitives.asymmetric import rsa, padding
# # from cryptography.hazmat.backends import default_backend
# # from cryptography.hazmat.primitives import hashes
# # import base64

# # app = Flask(__name__)

# # # Generate RSA key pair if not already present


# # # Function to encrypt a string with RSA public key
# # def encrypt_string(data, public_key):
# #     encrypted_data = public_key.encrypt(
# #         data.encode(),
# #         padding.OAEP(
# #             mgf=padding.MGF1(algorithm=hashes.SHA256()),
# #             algorithm=hashes.SHA256(),
# #             label=None
# #         )
# #     )
# #     return base64.b64encode(encrypted_data).decode('utf-8')

# # # Function to decrypt a string with RSA private key
# # def decrypt_string(encrypted_data, private_key):
# #     encrypted_data = base64.b64decode(encrypted_data)
# #     decrypted_data = private_key.decrypt(
# #         encrypted_data,
# #         padding.OAEP(
# #             mgf=padding.MGF1(algorithm=hashes.SHA256()),
# #             algorithm=hashes.SHA256(),
# #             label=None
# #         )
# #     )
# #     return decrypted_data.decode('utf-8')

# # # Route to encrypt data
# # @app.route('/encrypt', methods=['POST'])
# # def encrypt_data():
# #     data = request.json.get('data')
# #     encrypted_data = encrypt_string(data, private_key.public_key())
# #     return jsonify({'encrypted_data': encrypted_data})

# # # Route to decrypt data
# # @app.route('/decrypt', methods=['POST'])
# # def decrypt_data():
# #     encrypted_data = request.json.get('encrypted_data')
# #     decrypted_data = decrypt_string(encrypted_data, private_key)
# #     return jsonify({'decrypted_data': decrypted_data})

# # if __name__ == '__main__':
# #     app.run(debug=True)

# app.py

# app.py

# from app import create_app

# app = create_app()

# if __name__ == '__main__':
#     app.run(debug=True)
