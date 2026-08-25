FROM python:3.14.3-slim

LABEL maintainer="Package Maximizer Team <team@package-maximizer.dev>"
LABEL description="Контейнер для Package Maximizer"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения
RUN useradd -m -u 1000 pmuser && \
    mkdir -p /app /data /cache && \
    chown -R pmuser:pmuser /app /data /cache

WORKDIR /app

# Копирование файлов требований
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY --chown=pmuser:pmuser . .

# Установка пакета
RUN pip install -e .

# Переключение на пользователя приложения
USER pmuser

EXPOSE 5000

# Переменные окружения
ENV FLASK_APP=package_maximizer.web.app
ENV FLASK_ENV=production
ENV PACKAGE_MAXIMIZER_CACHE_DIR=/cache
ENV PACKAGE_MAXIMIZER_DATA_DIR=/data

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Команда по умолчанию
CMD ["python", "-m", "package_maximizer.web.app"]
