# Dockerfile

# Use the official Python base image
FROM python:3.11-slim

# Install build dependencies and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    libtool \
    autoconf \
    automake \
    make \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Download and install the latest config.guess and config.sub
RUN wget -O /usr/share/misc/config.guess \
    https://git.savannah.gnu.org/cgit/config.git/plain/config.guess \
    && wget -O /usr/share/misc/config.sub \
    https://git.savannah.gnu.org/cgit/config.git/plain/config.sub

# Install ta-lib C library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr --build=aarch64-unknown-linux-gnu \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=arbitrex.settings

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Create staticfiles directory with correct permissions
RUN mkdir -p /app/staticfiles && chmod 755 /app/staticfiles

# Create and switch to non-root user
RUN adduser --disabled-password --no-create-home myuser \
    && chown -R myuser:myuser /app
USER myuser

# Copy project
COPY --chown=myuser:myuser . /app/

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose the port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "arbitrex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]