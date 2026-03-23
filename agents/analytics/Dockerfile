FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including fonts for Japanese chart rendering)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .

# Expose the default AgentCore Runtime port
EXPOSE 8080

# Run the agent
CMD ["python", "agent.py"]
