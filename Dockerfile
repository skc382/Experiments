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
RUN pip install --no-cache-dir -r requirements.txt

RUN uvicorn --version

# Copy application code
COPY src/main .

# Expose port for FastAPI
EXPOSE 8000

# Run the application with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]