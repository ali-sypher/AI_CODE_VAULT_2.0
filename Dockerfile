# Dockerfile for AI Code Vault 2.0
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for compiling some python packages like bcrypt if wheels aren't available)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose both the Static Frontend and the Streamlit Backend ports
EXPOSE 8000 8501

# Run the dual-server autonomous launcher
CMD ["python", "launcher.py"]
