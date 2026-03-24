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

# Set repo identity for the launcher
ENV GITHUB_USER=AR-DYNAMICS
ENV GITHUB_REPO=ouroboros-new
ENV OUROBOROS_MAX_ROUNDS=15

# Init git repo with proper remote so launcher doesn't crash
RUN git init && \
    git remote add origin https://github.com/AR-DYNAMICS/ouroboros-new.git && \
    git add -A && \
    git commit -m "docker init" 2>/dev/null || true

# Run the colab launcher (designed for headless servers)
CMD ["python", "local_launcher.py"]
