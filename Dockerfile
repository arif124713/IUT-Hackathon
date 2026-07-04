# ── OfficePulse — Hugging Face Spaces Docker deployment ──────────────────────
# Serves: React frontend (nginx :7860) + FastAPI backend (:8000) + MCP (:8001)
# Database: SQLite (ephemeral) by default; override DATABASE_URL for MySQL
FROM python:3.11-slim

# ── System packages ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx curl && rm -rf /var/lib/apt/lists/*

# Node.js 20 for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.hf.txt .
RUN pip install --no-cache-dir -r requirements.hf.txt

# ── Frontend build ────────────────────────────────────────────────────────────
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci --silent
COPY frontend/ frontend/
RUN cd frontend && npm run build

# ── Application code ──────────────────────────────────────────────────────────
COPY backend/  backend/
COPY mcp_server/ mcp_server/
COPY agent/    agent/

# ── Nginx configuration ───────────────────────────────────────────────────────
RUN rm -f /etc/nginx/sites-enabled/default
COPY nginx.hf.conf /etc/nginx/sites-enabled/officepulse

# ── Startup script ────────────────────────────────────────────────────────────
COPY start.sh .
RUN chmod +x start.sh

# HF Spaces requires port 7860
EXPOSE 7860

CMD ["./start.sh"]
