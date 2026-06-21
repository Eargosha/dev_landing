"""
Главный файл приложения.
Точка входа в Flask-приложение.

Архитектура:
  - API маршруты вынесены в app/routes/ (Flask-RESTX)
  - Сервисы в app/services/
  - Репозитории в app/repositories/
  - Модели в app/models/
"""
import os
import logging
import time
from flask import Flask, render_template, request, jsonify
from app.extensions import db, migrate, mail, cors
from config import get_config

logger = logging.getLogger(__name__)


def create_app(config_override=None):
    """Фабрика приложения."""
    app = Flask(__name__)
    
    # Загружаем конфигурацию
    config_class = get_config()
    app.config.from_object(config_class)
    
    if config_override:
        app.config.update(config_override)
    
    # ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
    import sys
    from logging.handlers import RotatingFileHandler
    
    # Создаем директорию для логов
    log_file = app.config.get("LOG_FILE", "logs/app.log")
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File Handler (ротация: 5MB, 5 файлов)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Настройка Flask логгера
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
    
    # Настройка werkzeug логгера
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.addHandler(console_handler)
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = False
    
    app.logger.info("Приложение запущено с логированием в файл: %s", log_file)
    
    # ===== ИНИЦИАЛИЗАЦИЯ РАСШИРЕНИЙ =====
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    
    # Создаём директории
    os.makedirs(app.config.get("DATA_DIR", "data"), exist_ok=True)
    os.makedirs(os.path.dirname(app.config.get("LOG_FILE", "logs/app.log")), exist_ok=True)
    
    # Инициализация rate limiter
    from app.services import init_rate_limiter
    init_rate_limiter(app)
    
    # Инициализация metrics repository
    from app.repositories import init_metrics_repository
    init_metrics_repository(app.config.get("DATA_DIR", "data"))
    
    # ===== MIDDLEWARE ДЛЯ ЛОГИРОВАНИЯ И МЕТРИК =====
    
    @app.before_request
    def before_request():
        """Записываем начало запроса."""
        request.start_time = time.time()
        app.logger.info(
            "[<==>] %s %s - %s",
            request.method,
            request.path,
            request.remote_addr
        )
    
    @app.after_request
    def after_request(response):
        """Записываем метрики после каждого запроса."""
        # Вычисляем время выполнения
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
        else:
            duration = 0
        
        # Логируем
        app.logger.info(
            "[<==>] %s %s - %s (%.3f сек)",
            request.method,
            request.path,
            response.status_code,
            duration
        )
        
        # Записываем метрики (кроме статических файлов и Swagger)
        if not request.path.startswith(('/static', '/api/docs', '/swaggerui')):
            from app.repositories.metrics_repository import metrics_repo
            if metrics_repo:
                metrics_repo.record_request(
                    endpoint=request.path,
                    status_code=response.status_code,
                    success=(200 <= response.status_code < 400)
                )
        
        return response
    
    # ===== СОЗДАНИЕ ТАБЛИЦ БД =====
    with app.app_context():
        from app.models import Contact
        db.create_all()
    
    # ===== ПРОГРЕВ AI МОДЕЛИ =====
    with app.app_context():
        from app.services.warmup import warmup_ai_model
        warmup_ai_model()
    
    # ===== РЕГИСТРАЦИЯ API МАРШРУТОВ (Flask-RESTX) =====
    from app.routes import api_bp
    app.register_blueprint(api_bp)
    
    # ===== МАРШРУТЫ ФРОНТЕНДА =====
    
    @app.route("/")
    def index():
        """Корневой маршрут — отдаём лендинг-презентацию."""
        return render_template("index.html")
    
    # ===== ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ОШИБОК =====
    
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning("400 Bad Request: %s", str(error))
        return jsonify({
            "error": "Bad Request",
            "message": "Некорректный запрос"
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning("404 Not Found: %s", request.path)
        return jsonify({
            "error": "Not Found",
            "message": "Ресурс не найден"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        app.logger.warning("405 Method Not Allowed: %s", request.method)
        return jsonify({
            "error": "Method Not Allowed",
            "message": "Метод не разрешен"
        }), 405
    
    @app.errorhandler(429)
    def too_many_requests(error):
        app.logger.warning("429 Too Many Requests")
        return jsonify({
            "error": "Too Many Requests",
            "message": "Превышен лимит запросов"
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("500 Internal Server Error: %s", str(error), exc_info=True)
        
        # Записываем метрику ошибки
        from app.repositories.metrics_repository import metrics_repo
        if metrics_repo:
            metrics_repo.record_request(
                endpoint=request.path if hasattr(request, 'path') else 'unknown',
                status_code=500,
                success=False
            )
        
        return jsonify({
            "error": "Internal Server Error",
            "message": "Внутренняя ошибка сервера"
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Обработка всех необработанных исключений."""
        app.logger.error("Unhandled Exception: %s", str(error), exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": "Произошла непредвиденная ошибка"
        }), 500
    
    return app


# Создаём экземпляр приложения
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)