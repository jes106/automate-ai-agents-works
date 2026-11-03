FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DEMO_TODAY=2026-11-03 TZ=Europe/Madrid PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "server.py"]
