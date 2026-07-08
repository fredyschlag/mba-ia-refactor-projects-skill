import re
from database import db
from utils.helpers import utc_now
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'

    VALID_ROLES = ['user', 'admin', 'manager']
    MIN_PASSWORD_LENGTH = 4
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password, pwd)

    def is_admin(self):
        return self.role == 'admin'

    @classmethod
    def validate_email(cls, email):
        return bool(email) and bool(cls.EMAIL_REGEX.match(email))

    @classmethod
    def validate_password(cls, pwd):
        return bool(pwd) and len(pwd) >= cls.MIN_PASSWORD_LENGTH

    @classmethod
    def validate_role(cls, role):
        return role in cls.VALID_ROLES
