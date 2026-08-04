FROM python:3.12-slim

# ffmpeg/ffprobe are required by pipeline/audio_extractor.py (subprocess calls)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

# collectstatic doesn't need real DB/Supabase creds, so it's safe at build
# time; DJANGO_SECRET_KEY just needs to be *some* string for settings.py to
# import cleanly during the build.
RUN DJANGO_SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

EXPOSE 8000

# GUNICORN_TIMEOUT (in entrypoint.sh) is gunicorn's worker timeout, not an
# HTTP proxy limit -- it must stay comfortably above
# MAX_SYNC_LECTURE_DURATION_SECONDS (ingestion runs synchronously
# in-request), or gunicorn will kill the worker mid-pipeline on any lecture
# near that length. If you put Nginx/Caddy in front on the Oracle instance,
# its proxy_read_timeout needs the same headroom.
CMD ["./entrypoint.sh"]
