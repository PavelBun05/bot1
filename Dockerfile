FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем файл .env если его нет (для Railway)
RUN if [ ! -f .env ]; then echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env; fi

CMD ["python", "bot.py"]