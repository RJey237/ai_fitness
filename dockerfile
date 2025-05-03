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

# Copy the Django project into the image
COPY . .

# Expose port 8000
# EXPOSE 8000

# Run development server
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]