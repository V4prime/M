# ==========================================
# Dockerfile for Telegram Self-Bot Manager
# ==========================================
FROM node:20-slim

WORKDIR /app

# Install dependencies needed for better-sqlite3 native build
RUN apt-get update && apt-get install -y python3 make g++ sqlite3 && rm -rf /var/lib/apt/lists/*

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install --omit=dev

# Copy source code
COPY src/ ./src/

# Create data directory for SQLite databases
RUN mkdir -p /data
ENV DATA_DIR=/data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Start the app
CMD ["node", "src/index.js"]
