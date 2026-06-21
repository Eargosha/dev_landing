"""
Repository для работы с моделью Contact.

Отделяем работу с БД от бизнес-логики.
"""
import logging
from datetime import datetime
from app.extensions import db
from app.models.contact import Contact

logger = logging.getLogger(__name__)


class ContactRepository:
    """Repository для работы с обращениями."""
    
    @staticmethod
    def create(contact_data, ai_analysis=None, ip_address=None, user_agent=None):
        """
        Создаём новое обращение в БД.
        
        Args:
            contact_data: dict с данными пользователя (name, email, phone, message)
            ai_analysis: dict с результатами AI-анализа (опционально)
            ip_address: IP адрес пользователя
            user_agent: User-Agent браузера
        
        Returns: Contact: Созданный объект контакта
        
        Raises: Exception: Если не удалось сохранить в БД
        """
        try:
            contact = Contact(
                name=contact_data["name"],
                email=contact_data["email"],
                phone=contact_data.get("phone"),
                message=contact_data["message"],
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
                created_at=datetime.utcnow()
            )
            
            # Добавляем AI-анализ если есть
            if ai_analysis:
                contact.sentiment = ai_analysis.get("sentiment")
                contact.category = ai_analysis.get("category")
                contact.priority = ai_analysis.get("priority")
                contact.auto_response = ai_analysis.get("auto_response")
                contact.ai_used = ai_analysis.get("ai_used", False)
                contact.ai_fallback = ai_analysis.get("ai_fallback", False)
            
            db.session.add(contact)
            db.session.commit()
            
            logger.info(
                "Обращение #%d сохранено в БД: %s (%s)",
                contact.id, contact.name, contact.email
            )
            
            return contact
            
        except Exception as e:
            db.session.rollback()
            logger.error(" Ошибка сохранения обращения в БД: %s", str(e), exc_info=True)
            raise
    
    @staticmethod
    def update_email_status(contact_id, email_sent_to_owner=False, email_sent_to_user=False):
        """
        Обновляем статус отправки email.
        
        Args:
            contact_id: ID контакта
            email_sent_to_owner: Отправлено ли письмо владельцу
            email_sent_to_user: Отправлено ли письмо пользователю
        """
        try:
            contact = Contact.query.get(contact_id)
            if contact:
                contact.email_sent_to_owner = email_sent_to_owner
                contact.email_sent_to_user = email_sent_to_user
                db.session.commit()
                logger.info("Статус email обновлён для контакта #%d", contact_id)
        except Exception as e:
            db.session.rollback()
            logger.error("  Ошибка обновления статуса email: %s", str(e))
    
    @staticmethod
    def get_all(limit=100, offset=0):
        """Получить список обращений."""
        return Contact.query.order_by(Contact.created_at.desc()).limit(limit).offset(offset).all()
    
    @staticmethod
    def get_by_id(contact_id):
        """Получить обращение по ID."""
        return Contact.query.get(contact_id)
    
    @staticmethod
    def get_stats():
        """
        Получить статистику по обращениям.
        
        Returns:
            dict: Статистика (всего обращений, по категориям, по приоритетам)
        """
        total = Contact.query.count()
        
        # По категориям
        categories = {}
        for category in ["job_offer", "collaboration", "question", "feedback", "other"]:
            count = Contact.query.filter_by(category=category).count()
            categories[category] = count
        
        # По приоритетам
        priorities = {}
        for priority in ["high", "medium", "low"]:
            count = Contact.query.filter_by(priority=priority).count()
            priorities[priority] = count
        
        # По тональности
        sentiments = {}
        for sentiment in ["positive", "neutral", "negative"]:
            count = Contact.query.filter_by(sentiment=sentiment).count()
            sentiments[sentiment] = count
        
        # AI статистика
        ai_used_count = Contact.query.filter_by(ai_used=True).count()
        ai_fallback_count = Contact.query.filter_by(ai_fallback=True).count()
        
        return {
            "total": total,
            "by_category": categories,
            "by_priority": priorities,
            "by_sentiment": sentiments,
            "ai_used": ai_used_count,
            "ai_fallback": ai_fallback_count,
        }