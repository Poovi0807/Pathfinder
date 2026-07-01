# ── Pathfinder Dockerfile ─────────────────────────────────────────────────────
# Runs the CLI tool in an isolated container.
# Data, logs, and backups are persisted via mounted volumes.

FROM python:3.12-slim

# Metadata
LABEL maintainer="Pathfinder"
LABEL description="Customer Onboarding Tracker CLI"

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash pathfinder

# Set working directory
WORKDIR /app

# Copy source
COPY tracker.py .

# Create directories that will hold persistent data
RUN mkdir -p logs backups \
    && chown -R pathfinder:pathfinder /app

# Switch to non-root user
USER pathfinder

# Default command — interactive menu
# Override with: docker run ... python tracker.py --check
CMD ["python", "tracker.py"]
