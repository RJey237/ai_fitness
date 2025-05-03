# Use official Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install aiogram==3.20.0

# Copy the bot and application code into the image
COPY . .

# Expose port (adjust based on your app, if necessary)
# EXPOSE 8000

# Run bot
CMD ["python", "bot.py"]
