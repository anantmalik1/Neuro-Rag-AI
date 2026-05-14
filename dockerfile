# ---------------- BASE IMAGE ----------------
FROM python:3.11-slim

# ---------------- METADATA ----------------
LABEL maintainer="anantmalik125"
LABEL description="NeuroRAG - AI-Powered Document Intelligence"
LABEL version="1.0"

# ---------------- ENVIRONMENT VARIABLES ----------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

# ---------------- WORKING DIRECTORY ----------------
WORKDIR /app

# ---------------- SYSTEM DEPENDENCIES + USER + DIRECTORIES (root ke roop mein) ----------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && useradd -m -u 1000 user \
    && mkdir -p /app/uploaded_docs /app/chroma_db /app/.cache/huggingface /app/.cache/sentence-transformers \
    && chown -R user:user /app

# ---------------- NON-ROOT USER SWITCH ----------------
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# ---------------- COPY & INSTALL DEPENDENCIES ----------------
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------------- COPY APPLICATION CODE ----------------
COPY --chown=user . /app

# ---------------- EXPOSE PORT ----------------
EXPOSE 8501

# ---------------- HEALTH CHECK ----------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# ---------------- RUN APP ----------------
ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.enableCORS=false", \
            "--server.enableXsrfProtection=false"]
