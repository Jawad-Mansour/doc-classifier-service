FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["rq", "worker", "default", "--url", "redis://redis:6379/0"]
