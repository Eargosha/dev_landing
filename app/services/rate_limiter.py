"""
Сервис ограничения частоты запросов (Rate Limiter).
Реализация на основе файлового хранилища (JSON) со скользящим окном.

Защита от спама и DDoS-атак.
Используется файловое хранилище
Скользящее окно
"""
import json
import os
import time
import logging
from threading import Lock # Верим, что потоки в питоне есть)
from functools import wraps
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter на основе файлового хранилища.
    Хранит timestamps всех запросов для каждого IP
    """
    
    def __init__(self, data_dir="data", max_requests=5, window_minutes=60):
        """
        Конструтор RateLimiter.
        
        Args:
            data_dir: Директория для хранения данных
            max_requests: Максимальное количество запросов в окне
            window_minutes: Размер окна в минутах
        """
        self.data_dir = data_dir
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self._file_path = os.path.join(data_dir, "rate_limits.json")
        self._lock = Lock()  # Потокобезопасность
        
        # Создаём директорию если её нет
        os.makedirs(data_dir, exist_ok=True)
    
    def _load_data(self):
        """Загружаем данные из JSON файла."""
        if not os.path.exists(self._file_path):
            return {}
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Не удалось загрузить rate limit данные: %s", e)
            return {}
    
    def _save_data(self, data):
        """Сохраняем данные в JSON файл."""
        try:
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error("Не удалось сохранить rate limit данные: %s", e)
    
    def _cleanup_old_entries(self, timestamps):
        """
        Удаляем записи старше окна времени.
    
        Args: timestamps - список timestamps запросов
        
        Returns: Отфильтрованный список timestamps
        """
        current_time = time.time()
        return [ts for ts in timestamps if current_time - ts < self.window_seconds]
    
    def check_rate_limit(self, identifier):
        """
        Проверяем, превышен ли лимит запросов.
        
        Args:
            identifier: Идентификатор (IP адрес или email)
        
        Returns:
            tuple: (is_limited, remaining, reset_time)
                - is_limited: True если лимит превышен
                - remaining: Осталось запросов
                - reset_time: Время до сброса лимита (секунды)
        """
        with self._lock:  # Потокобезопасность
            data = self._load_data()
            current_time = time.time()
            
            # Получаем timestamps для этого identifier
            timestamps = data.get(identifier, [])
            
            # Удаляем старые записи
            timestamps = self._cleanup_old_entries(timestamps)
            
            # Вычисляем время до сброса
            if timestamps:
                oldest_in_window = min(timestamps)
                reset_time = int(self.window_seconds - (current_time - oldest_in_window))
            else:
                reset_time = self.window_seconds
            
            # Проверяем лимит
            if len(timestamps) >= self.max_requests:
                # Лимит превышен — сохраняем и возвращаем
                data[identifier] = timestamps
                self._save_data(data)
                
                logger.warning(
                    "Rate limit превышен для %s: %d/%d запросов",
                    identifier, len(timestamps), self.max_requests
                )
                return True, 0, max(reset_time, 1)
            
            # Лимит не превышен — добавляем текущий timestamp
            timestamps.append(current_time)
            data[identifier] = timestamps
            self._save_data(data)
            
            remaining = self.max_requests - len(timestamps)
            logger.info(
                "Rate limit для %s: %d/%d (осталось %d)",
                identifier, len(timestamps), self.max_requests, remaining
            )
            return False, remaining, reset_time
    
    def get_stats(self):
        """Получить статистику по rate limiting."""
        with self._lock:
            data = self._load_data()
            current_time = time.time()
            
            active_identifiers = 0
            total_requests = 0
            
            for identifier, timestamps in data.items():
                clean = self._cleanup_old_entries(timestamps)
                if clean:
                    active_identifiers += 1
                    total_requests += len(clean)
            
            return {
                "active_identifiers": active_identifiers,
                "total_tracked_requests": total_requests,
                "max_requests_per_window": self.max_requests,
                "window_minutes": self.window_seconds // 60,
            }


# Глобальный экземпляр (инициализируется в create_app)
rate_limiter = None


def init_rate_limiter(app):
    """
    Инициализация rate limiter с конфигурацией приложения.
    
    Args:
        app: Flask приложение
    """
    global rate_limiter
    rate_limiter = RateLimiter(
        data_dir=app.config.get("DATA_DIR", "data"),
        max_requests=app.config.get("RATE_LIMIT_MAX_REQUESTS", 5),
        window_minutes=app.config.get("RATE_LIMIT_WINDOW_MINUTES", 60)
    )
    logger.info(
        "Rate limiter инициализирован: %d запросов / %d минут",
        rate_limiter.max_requests,
        rate_limiter.window_seconds // 60
    )


def rate_limit(f):
    """
    Декоратор для применения rate limiting к маршрутам.
    
    Usage:
        @app.route("/api/contact", methods=["POST"])
        @rate_limit
        def contact():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Получаем identifier (IP адрес)
        identifier = request.remote_addr
        
        # Проверяем rate limit
        is_limited, remaining, reset_time = rate_limiter.check_rate_limit(identifier)
        
        # Добавляем заголовки в ответ
        response = f(*args, **kwargs)
        
        # Если response — это кортеж (response, status_code)
        if isinstance(response, tuple):
            response_obj, status_code = response
            if isinstance(response_obj, str):
                from flask import make_response
                response_obj = make_response(response_obj, status_code)
        else:
            response_obj = response
        
        # Добавляем заголовки rate limiting
        response_obj.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
        response_obj.headers["X-RateLimit-Remaining"] = str(remaining)
        response_obj.headers["X-RateLimit-Reset"] = str(reset_time)
        
        if is_limited:
            logger.warning("Rate limit exceeded for %s", identifier)
            return jsonify({
                "error": "Too Many Requests",
                "message": f"Превышен лимит запросов. Попробуйте через {reset_time} секунд."
            }), 429
        
        return response_obj
    
    return decorated_function