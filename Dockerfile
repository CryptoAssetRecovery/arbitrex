# Build stage
FROM python:3.11-slim AS builder
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
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr --build=aarch64-unknown-linux-gnu \
    && make && make install

# Final runtime stage
FROM python:3.11-slim
COPY --from=builder /usr /usr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY . /app/

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "arbitrex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]