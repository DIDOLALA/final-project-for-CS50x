from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)
    has_submitted_info = db.Column(db.Boolean, default=False, nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    nationality = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(20), nullable=True)
    age = db.Column(db.String(20), nullable=True)
    profession = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(80), unique=True, nullable=True)   # 先允许空
    password_hash = db.Column(db.String(128), nullable=True) 

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

class Preference(db.Model):
    __tablename__ = 'preference'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    payload = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Limitation(db.Model):
    """保存用户填写的实际限制"""
    __tablename__ = 'limitation'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    duration = db.Column(db.String(20))
    pace = db.Column(db.String(20))
    budget = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Itinerary(db.Model):
    """保存最终行程，避免重复调用 LLM"""
    __tablename__ = 'itinerary'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)   # 最终渲染的 markdown
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
