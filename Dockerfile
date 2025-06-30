FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY unified_api.py .

# Expose port
EXPOSE 3000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "unified_api:app"] 