# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем зависимости системы (если нужны для .docx/.rtf)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Порт, на котором будет работать приложение
EXPOSE 8005

# Запуск приложения через uvicorn
CMD ["uvicorn", "api_parsing:app", "--host", "0.0.0.0", "--port", "8005"]