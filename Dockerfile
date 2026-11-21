FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

RUN groupadd --system insureai && useradd --system --gid insureai --create-home insureai
COPY --chown=insureai:insureai . .
USER insureai

CMD ["sh", "-c", "exec gunicorn backend.app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 2 --timeout 600"]
