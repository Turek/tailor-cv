FROM python:3.12-slim

# WeasyPrint runtime dependencies (Pango/Cairo/GDK-Pixbuf) + fonts.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching. constraints.txt pins exact (incl.
# transitive) versions for reproducible rebuilds across machines/time.
COPY pyproject.toml constraints.txt ./
COPY tailorcv ./tailorcv
RUN pip install --no-cache-dir .[dev] -c constraints.txt

# Assets (bind-mounted in compose for dev; copied for a standalone image).
COPY assets ./assets

ENTRYPOINT []
CMD ["python", "-m", "tailorcv", "--help"]
