FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y build-essential libpq-dev

# Копируем зависимости
COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем проект
COPY . .

# Переменная окружения для alembic
ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]