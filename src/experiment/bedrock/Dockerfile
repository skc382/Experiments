# Use a lightweight Python base image
FROM python:3.9

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies and verify gunicorn
RUN pip install --no-cache-dir -r requirements.txt \
    && gunicorn --version

# Copy application code
COPY . .

# Expose the application port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV APP_HOST=0.0.0.0
ENV APP_PORT=5000

# Run the application with Gunicorn
CMD ["gunicorn", "--worker-class=eventlet", "-w", "1", "--bind=0.0.0.0:5000", "app:app"]