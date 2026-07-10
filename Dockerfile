# The Structural Audit — always-on container for audit.grahamkindermann.com
# Build:  docker build -t glk-audit .
# Run:    docker run -p 8080:8080 glk-audit
FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; Streamlit needs no extras for this app.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render/Fly inject $PORT. Default 8080 for local runs.
ENV PORT=8080
EXPOSE 8080

# Healthcheck endpoint provided by Streamlit itself.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",8080)}/_stcore/health')" || exit 1

CMD streamlit run app.py \
  --server.port=${PORT} \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableStaticServing=true \
  --browser.gatherUsageStats=false
