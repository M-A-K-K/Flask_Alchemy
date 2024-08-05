# app/schemas.py

from app import ma
from app.models import User, Subject

class UserSchema(ma.SQLAlchemyAutoSchema):
    subjects = ma.Nested('SubjectSchema', many=True)

    class Meta:
        model = User
        fields = ('id', 'name', 'age', 'gender', 'subjects')

class SubjectSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Subject
        fields = ('id', 'subject_name', 'encrypted_grade', 'user_id')

user_schema = UserSchema()
users_schema = UserSchema(many=True)
subject_schema = SubjectSchema()
subjects_schema = SubjectSchema(many=True)
