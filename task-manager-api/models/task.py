from database import db
from utils.helpers import utc_now


class Task(db.Model):
    __tablename__ = 'tasks'

    VALID_STATUSES = ['pending', 'in_progress', 'done', 'cancelled']
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 200
    MIN_PRIORITY = 1
    MAX_PRIORITY = 5
    DEFAULT_PRIORITY = 3

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self, include_relations=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
            'overdue': self.is_overdue(),
        }
        if include_relations:
            data['user_name'] = self.user.name if self.user else None
            data['category_name'] = self.category.name if self.category else None
        return data

    @classmethod
    def validate_status(cls, new_status):
        return new_status in cls.VALID_STATUSES

    @classmethod
    def validate_priority(cls, p):
        return isinstance(p, int) and cls.MIN_PRIORITY <= p <= cls.MAX_PRIORITY

    @classmethod
    def validate_title(cls, title):
        return bool(title) and cls.MIN_TITLE_LENGTH <= len(title) <= cls.MAX_TITLE_LENGTH

    def is_overdue(self):
        if not self.due_date:
            return False
        return self.due_date < utc_now() and self.status not in ('done', 'cancelled')
