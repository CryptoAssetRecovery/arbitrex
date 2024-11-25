# Dockerfile

# Use the official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 8000

# Use a non-root user for security
RUN adduser --disabled-password myuser
USER myuser

# Run the application with Gunicorn
CMD ["gunicorn", "arbitrex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]