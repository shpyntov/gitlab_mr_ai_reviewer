# GitLab MR AI Reviewer - Dockerfile
# Builds a containerized AI code review bot for GitLab CI

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY reviewbot/ ./reviewbot/
COPY prompts/ ./prompts/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command - runs the review bot
ENTRYPOINT ["python", "-m", "reviewbot.main"]
