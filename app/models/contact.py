"""
Модель контактного обращения.
Хранит данные из формы обратной связи + результаты AI-анализа.
"""
from datetime import datetime
from app.extensions import db


class Contact(db.Model):
    """Модель контактного обращения."""
    
    __tablename__ = "contacts"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Данные пользователя
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # AI-анализ
    sentiment = db.Column(db.String(20), nullable=True)  # positive/neutral/negative
    category = db.Column(db.String(50), nullable=True)  # job_offer/collaboration/question/feedback/other
    priority = db.Column(db.String(20), nullable=True)  # high/medium/low
    auto_response = db.Column(db.Text, nullable=True)
    ai_used = db.Column(db.Boolean, default=False)
    ai_fallback = db.Column(db.Boolean, default=False)
    
    # Метаданные
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Статус обработки
    email_sent_to_owner = db.Column(db.Boolean, default=False)
    email_sent_to_user = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """Сериализация модели в словарь для JSON-ответа."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "message": self.message,
            "sentiment": self.sentiment,
            "category": self.category,
            "priority": self.priority,
            "ai_used": self.ai_used,
            "ai_fallback": self.ai_fallback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<Contact {self.id}: {self.name} ({self.email})>"