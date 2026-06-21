"""
Схемы валидации для контактной формы.
Используем marshmallow для валидации и сериализации данных.
"""
from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE


class ContactSchema(Schema):
    """
    Схема валидации данных контактной формы.
    
    Поля:
    - name: обязательное, 2-100 символов
    - email: обязательное, валидный email
    - phone: опциональное, формат телефона
    - message: обязательное, 10-2000 символов
    """
    
    # Имя
    name = fields.String(
        required=True,
        validate = [
            validate.Length(min=2, max=100, error="Имя должно быть от 2 до 100 символов")
        ]
    )
    
    # Адрес почты
    email = fields.Email(
        required=True,
        error_messages={"invalid": "Некорректный формат email"}
    )
    
    # Номер мобилки
    phone = fields.String(
        required=False,
        allow_none=True,
        load_default=None,
        validate=[
            validate.Regexp(
                regex=r"^$|^[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]*$",
                error="Некорректный формат телефона"
            )
        ],
    error_messages={
        "invalid": "Некорректный телефон"
    }
    )
    
    # Коммент пользователя
    message = fields.String(
        required=True,
        validate=[
            validate.Length(min=10, max=2000, error="Сообщение должно быть от 10 до 2000 символов")
        ]
    )
    
    class Meta:
        """Метаданные схемы."""
        # Убираем неизвестные поля (защита от лишних данных)
        unknown = "EXCLUDE"


# Создаём экземпляр схемы для использования
contact_schema = ContactSchema()