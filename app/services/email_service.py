"""
Сервис отправки email-уведомлений с асинхронной отправкой и отслеживанием статусов.
"""
import logging
from flask import current_app, render_template_string
from flask_mail import Message
from app.extensions import mail

logger = logging.getLogger(__name__)


# ===== HTML ШАБЛОНЫ =====

# HTML шаблон письма владельцу
OWNER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .message-box { background: #f1f3f5; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0; }
        .ai-analysis { background: #e8f5e9; padding: 15px; border-radius: 5px; margin-top: 20px; }
        .label { font-weight: bold; color: #495057; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 3px; font-size: 12px; }
        .badge-high { background: #dc3545; color: white; }
        .badge-medium { background: #ffc107; color: black; }
        .badge-low { background: #28a745; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Новое обращение с сайта</h2>
        <p><span class="label">От:</span> {{ name }} ({{ email }})</p>
        <p><span class="label">Телефон:</span> {{ phone or 'не указан' }}</p>
        <p><span class="label">Время:</span> {{ created_at }}</p>
    </div>
    
    <h3>Сообщение:</h3>
    <div class="message-box">
        {{ message|replace('\n', '<br>')|safe }}
    </div>
    
    {% if ai_analysis %}
    <div class="ai-analysis">
        <h3>AI-анализ</h3>
        <p><span class="label">Тональность:</span> {{ ai_analysis.sentiment }}</p>
        <p><span class="label">Категория:</span> {{ ai_analysis.category }}</p>
        <p>
            <span class="label">Приоритет:</span>
            <span class="badge badge-{{ ai_analysis.priority }}">
                {{ ai_analysis.priority|upper }}
            </span>
        </p>
        <p><span class="label">AI использован:</span> {{ 'Да' if ai_analysis.ai_used else 'Нет (fallback)' }}</p>
        {% if ai_analysis.ai_model %}
        <p><span class="label">Модель:</span> {{ ai_analysis.ai_model }}</p>
        {% endif %}
        <hr>
        <p><strong>Автоответ от AI:</strong></p>
        <div style="background: white; padding: 10px; border-radius: 3px;">
            {{ ai_analysis.auto_response|replace('\n', '<br>')|safe }}
        </div>
    </div>
    {% endif %}
    
    <div class="footer">
        <p>IP: {{ ip_address or 'неизвестен' }}</p>
        <p>Это письмо сгенерировано автоматически. Пожалуйста, не отвечайте на него.</p>
    </div>
</body>
</html>
"""

# Plain-text шаблон письма владельцу (обязателен)
OWNER_TEXT_TEMPLATE = """
Новое обращение с сайта-портфолио

Имя: {{ name }}
Email: {{ email }}
Телефон: {{ phone or 'не указан' }}

Сообщение:
{{ message }}

---
Время: {{ created_at }}
IP: {{ ip_address or 'неизвестен' }}

{% if ai_analysis %}
AI-анализ:
  Тональность: {{ ai_analysis.sentiment }}
  Категория: {{ ai_analysis.category }}
  Приоритет: {{ ai_analysis.priority }}
  AI использован: {{ 'Да' if ai_analysis.ai_used else 'Нет (fallback)' }}
  {% if ai_analysis.ai_model %}Модель: {{ ai_analysis.ai_model }}{% endif %}
  
Автоответ от AI:
{{ ai_analysis.auto_response }}
{% endif %}
"""

# HTML шаблон для пользователя
USER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #e3f2fd; padding: 20px; border-radius: 5px; margin-bottom: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; border-radius: 5px; }
        .response-box { background: white; padding: 15px; border-left: 4px solid #28a745; margin: 15px 0; }
        .signature { margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Ваше обращение получено!</h2>
        <p>Здравствуйте, {{ name }}!</p>
    </div>
    
    <div class="content">
        <p>Спасибо за ваше обращение. Я получил ваше сообщение.</p>
        
        {% if auto_response %}
        <div class="response-box">
            <h3>Мой глупенький искусствнный ассистент Антошка хочет вам что-то сказать:</h3>
            {{ auto_response|replace('\n', '<br>')|safe }}
        </div>
        {% else %}
        <p>Обычно я отвечаю в течение 24 часов.</p>
        {% endif %}
    </div>
    
    <div class="signature">
        <p>С уважением,<br>
        <strong>Егор Николаевич</strong></p>
        <p style="font-size: 12px; color: #6c757d;">
            Это автоматическое сообщение, пожалуйста, не отвечайте на него.
        </p>
    </div>
</body>
</html>
"""

USER_TEXT_TEMPLATE = """
Здравствуйте, {{ name }}!

Спасибо за ваше обращение. Я получил ваше сообщение.

{% if auto_response %}
{{ auto_response }}
{% else %}
Обычно я отвечаю в течение 24 часов.
{% endif %}

---
С уважением,
Егор Николаевич
"""


class EmailService:
    """Сервис для отправки email-уведомлений."""
    
    @staticmethod
    def _is_configured():
        username = current_app.config.get("MAIL_USERNAME")
        password = current_app.config.get("MAIL_PASSWORD")
        return bool(username and password and username != "your-email@mail.ru")
    
    @classmethod
    def send_owner_notification(cls, contact_data, ai_analysis=None, ip_address=None):
        if not cls._is_configured():
            logger.warning("SMTP не настроен. Письмо владельцу не отправлено.")
            return False
        
        try:
            owner_email = current_app.config.get("MAIL_OWNER_EMAIL")
            if not owner_email:
                logger.error("MAIL_OWNER_EMAIL не указан")
                return False
            
            subject = "Новое обращение от с сайта лендинга"
            
            # Подготовка данных для шаблонов
            context = {
                "name": contact_data.get("name"),
                "email": contact_data.get("email"),
                "phone": contact_data.get("phone"),
                "message": contact_data.get("message"),
                "created_at": contact_data.get("created_at", "неизвестно"),
                "ip_address": ip_address,
                "ai_analysis": ai_analysis,
            }
            
            # Генерируем обе версии письма
            html_body = render_template_string(OWNER_HTML_TEMPLATE, **context)
            text_body = render_template_string(OWNER_TEXT_TEMPLATE, **context)
            
            msg = Message(
                subject=subject,
                recipients=[owner_email],
                body=text_body,  # Plain-text версия (обязательна)
                html=html_body,   # HTML версия (опционально, но желательно)
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                # reply_to=contact_data.get("email"),
                # extra_headers={
                #     'X-Mailer': 'Web Application Mailer',
                #     'X-Priority': '3',  # Нормальный приоритет (не высокий)
                #     'X-MSMail-Priority': 'Normal',
                #     # 'Importance': 'Normal',
                # }
            )
            
            mail.send(msg)
            logger.info("  Письмо владельцу отправлено на %s", owner_email)
            return True
            
        except Exception as e:
            logger.error("  Ошибка отправки письма владельцу: %s", str(e), exc_info=True)
            return False
    
    @classmethod
    def send_user_confirmation(cls, contact_data, auto_response=None):
        if not cls._is_configured():
            logger.warning("SMTP не настроен. Письмо пользователю не отправлено.")
            return False
        
        try:
            user_email = contact_data.get("email")
            if not user_email:
                logger.warning("Email пользователя не указан")
                return False
            
            context = {
                "name": contact_data.get("name", "уважаемый пользователь"),
                "auto_response": auto_response,
            }
            
            html_body = render_template_string(USER_HTML_TEMPLATE, **context)
            text_body = render_template_string(USER_TEXT_TEMPLATE, **context)
            
            msg = Message(
                subject="  Ваше обращение получено!",
                recipients=[user_email],
                body=text_body,
                html=html_body,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                # extra_headers={
                #     'X-Mailer': 'Web Application Mailer',
                #     'X-Priority': '3',
                #     'X-MSMail-Priority': 'Normal',
                # } re_UjYsREQo_Q1n2UxNV48u6o6Rdr6NkyAvy
            )
            
            mail.send(msg)
            logger.info("  Письмо-подтверждение отправлено на %s", user_email)
            return True
            
        except Exception as e:
            logger.error("  Ошибка отправки письма пользователю: %s", str(e), exc_info=True)
            return False
    
    @classmethod
    def send_all(cls, contact_data, ai_analysis=None, ip_address=None):
        logger.info("  Начинаем отправку email-уведомлений...")
        
        owner_sent = cls.send_owner_notification(contact_data, ai_analysis, ip_address)
        
        auto_response = ai_analysis.get("auto_response") if ai_analysis else None
        user_sent = cls.send_user_confirmation(contact_data, auto_response)
        
        logger.info(
            "Отправка завершена: владелец=%s, пользователь=%s",
            "Доставлено" if owner_sent else "Нет",
            "Доставлено" if user_sent else "Нет"
        )
        
        return {"owner_sent": owner_sent, "user_sent": user_sent}