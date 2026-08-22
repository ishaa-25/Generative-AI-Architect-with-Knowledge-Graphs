# 1. Base Image: Lean, official Python runtime
FROM python:3.11-slim

# 2. Working Directory inside the container
WORKDIR /app

# 3. Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application source code
COPY . .

# 5. Expose default FastAPI port
EXPOSE 8000

# 6. Start the server using Uvicorn ASGI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]