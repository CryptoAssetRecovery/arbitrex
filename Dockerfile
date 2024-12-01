# Dockerfile

# Use the official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=arbitrex.settings

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Create and switch to non-root user
RUN adduser --disabled-password --no-create-home myuser
RUN chown -R myuser:myuser /app
USER myuser

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose the port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "arbitrex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]