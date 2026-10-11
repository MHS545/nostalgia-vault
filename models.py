from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy ORM instance
db = SQLAlchemy()

class Memory(db.Model):
    """
    Memory Database Model.
    Represents the 'memories' table in MySQL.
    Stores memorable user titles, descriptions, image paths/URLs, and timestamps.
    """
    __tablename__ = 'memories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Memory id={self.id} title='{self.title}'>"
