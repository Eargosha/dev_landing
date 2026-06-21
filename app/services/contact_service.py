"""
Сервис для обработки контактных обращений.

Собирает все компоненты:
  - Валидация данных
  - Rate limiting
  - AI анализ
  - Сохранение в БД
  - Отправка email
  - Запись метрик

Это центральный сервис, который связывает все части вместе.
"""
import logging
from datetime import datetime
from flask import request
from app.extensions import db
from app.schemas.contact_schema import contact_schema
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.repositories.contact_repository import ContactRepository

logger = logging.getLogger(__name__)


class ContactService:
    """
    Сервис для обработки контактных обращений.
    
    Все методы статические — не нужно создавать экземпляр.
    """
    
    @classmethod
    def process_contact(cls, request_data, ip_address, user_agent):
        """
        Обрабатываем контактное обращение.
        
        Этапы:
        1. Валидация данных
        2. Rate limiting
        3. AI анализ
        4. Сохранение в БД
        5. Отправка email
        6. Обновление статуса email
        7. Запись метрик
        
        Args:
            request_data: dict с данными из запроса
            ip_address: IP адрес пользователя
            user_agent: User-Agent браузера
        
        Returns:
            dict: {
                "success": bool,
                "contact_id": int,
                "ai_analysis": dict,
                "email_status": dict,
                "message": str
            }
        
        Raises:
            ValueError: Если валидация не прошла
            RuntimeError: Если rate limit превышен
        """
        logger.info("  Начало обработки обращения от %s (%s)", 
                   request_data.get("name"), ip_address)
        
        # ===== 1. ВАЛИДАЦИЯ =====
        try:
            validated_data = contact_schema.load(request_data)
            logger.info(" Валидация пройдена")
        except Exception as e:
            logger.error(" Ошибка валидации: %s", str(e))
            raise ValueError(f"Ошибка валидации: {str(e)}")
        
        # ===== 2. RATE LIMITING =====
        # Импортируем динамически (получаем актуальное значение)
        from app.services.rate_limiter import rate_limiter
        
        if rate_limiter is None:
            logger.warning(" ️ Rate limiter не инициализирован, пропускаем проверку")
            is_limited = False
            remaining = 0
            reset_time = 0
        else:
            is_limited, remaining, reset_time = rate_limiter.check_rate_limit(ip_address)
            
            if is_limited:
                logger.warning(" Rate limit превышен для %s", ip_address)
                raise RuntimeError(
                    f"Превышен лимит запросов. Попробуйте через {reset_time} секунд."
                )
            
            logger.info(" Rate limit пройден (осталось: %d)", remaining)
        
        # ===== 3. AI АНАЛИЗ =====
        ai_analysis = AIService.analyze(
            validated_data["name"],
            validated_data["message"]
        )
        
        logger.info(
            " AI анализ завершён: sentiment=%s, category=%s, priority=%s",
            ai_analysis.get("sentiment"),
            ai_analysis.get("category"),
            ai_analysis.get("priority")
        )
        
        # ===== 4. СОХРАНЕНИЕ В БД =====
        contact = ContactRepository.create(
            contact_data=validated_data,
            ai_analysis=ai_analysis,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(" Обращение #%d сохранено в БД", contact.id)
        
        # ===== 5. ОТПРАВКА EMAIL =====
        contact_data_with_time = {
            **validated_data,
            "created_at": contact.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        email_status = EmailService.send_all(
            contact_data=contact_data_with_time,
            ai_analysis=ai_analysis,
            ip_address=ip_address
        )
        
        # ===== 6. ОБНОВЛЕНИЕ СТАТУСА EMAIL В БД =====
        ContactRepository.update_email_status(
            contact_id=contact.id,
            email_sent_to_owner=email_status["owner_sent"],
            email_sent_to_user=email_status["user_sent"]
        )
        
        logger.info(
            " Статус email обновлён: владелец=%s, пользователь=%s",
            "" if email_status["owner_sent"] else " ",
            "" if email_status["user_sent"] else " "
        )
        
        # ===== 7. ЗАПИСЬ МЕТРИК =====
        from app.repositories.metrics_repository import metrics_repo
        if metrics_repo:
            metrics_repo.record_request(
                endpoint="/api/contact",
                status_code=201,
                success=True
            )
        
        # ===== ВОЗВРАЩАЕМ РЕЗУЛЬТАТ =====
        result = {
            "success": True,
            "contact_id": contact.id,
            "ai_analysis": {
                "sentiment": ai_analysis.get("sentiment"),
                "category": ai_analysis.get("category"),
                "priority": ai_analysis.get("priority"),
                "ai_used": ai_analysis.get("ai_used"),
                "ai_fallback": ai_analysis.get("ai_fallback"),
            },
            "email_status": email_status,
            "message": "Обращение успешно отправлено! Мы свяжемся с вами в ближайшее время."
        }
        
        logger.info("  Обращение #%d полностью обработано", contact.id)
        
        return result