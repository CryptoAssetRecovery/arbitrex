# Dockerfile

# Use the official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=arbitrex.settings

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create staticfiles directory with correct permissions
RUN mkdir -p /app/staticfiles && chmod 755 /app/staticfiles

# Create and switch to non-root user
RUN adduser --disabled-password --no-create-home myuser
RUN chown -R myuser:myuser /app
USER myuser

# Copy project
COPY --chown=myuser:myuser . /app/

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose the port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "arbitrex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]