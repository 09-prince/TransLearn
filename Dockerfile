# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y gcc libglib2.0-0 libsm6 libxext6 libxrender-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port for documentation (not functional on Railway)
EXPOSE 8000

# Start FastAPI using Uvicorn and respect Railway's dynamic PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
