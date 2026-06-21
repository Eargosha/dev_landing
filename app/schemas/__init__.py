"""
Пакет схем валидации.
Импортируем все схемы валидацити на уровне пакета для удобства.
"""
from app.schemas.contact_schema import ContactSchema, contact_schema 

__all__ = ["ContactSchema", "contact_schema"]