# ==========================================
# Stage 1: Build & Dependency Isolation
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create an isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Install dependencies into virtual environment without caching wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Final Production Runtime
# ==========================================
FROM python:3.10-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Copy the pre-built virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY . .

# Create non-root system user and ensure write permissions for SQLite database
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    mkdir -p instance && \
    chown -R appuser:appgroup /app

# Switch to non-root user for security hardening (least privilege)
USER appuser

# Expose port 5000 for Flask/Gunicorn
EXPOSE 5000

# Start production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
