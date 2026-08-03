FROM python:3.12-slim

# ffmpeg/ffprobe are required by pipeline/audio_extractor.py (subprocess calls)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# --timeout is gunicorn's worker timeout, not an HTTP proxy limit -- it must
# stay comfortably above MAX_SYNC_LECTURE_DURATION_SECONDS (ingestion runs
# synchronously in-request), or gunicorn will kill the worker mid-pipeline
# on any lecture near that length.
CMD gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 1800
