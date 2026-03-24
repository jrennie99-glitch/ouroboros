FROM python:3.12-slim

WORKDIR /app

# Install git (needed for ouroboros git operations)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

# Create local_state directory
RUN mkdir -p local_state/logs local_state/state local_state/memory

# Run the local launcher
CMD ["python", "local_launcher.py"]
