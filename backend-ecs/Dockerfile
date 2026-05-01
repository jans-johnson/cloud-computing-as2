# Single-stage image: small attack surface, fast cold-start on Fargate.
FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    AWS_REGION=us-east-1

WORKDIR /app

# Dependencies first to maximise layer caching
COPY backend-ec2/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Repo layout: app.py imports config/ and core/ from the parent
COPY config /app/config
COPY core /app/core
COPY backend-ec2/app.py /app/backend-ec2/app.py
COPY backend-ec2/__init__.py /app/backend-ec2/__init__.py

EXPOSE 8080

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "backend-ec2.app:app"]
