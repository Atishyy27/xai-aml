# SENTINEL API. Works on any Docker host (Hugging Face Spaces, Render-as-Docker).
# Render's default runtime for this repo is native Python via render.yaml; this
# file is the container path.
#
# The models are committed under artifacts/, so this image neither installs
# torch nor trains anything -- it installs the torch-free runtime requirements
# and serves. That keeps the image small and the running process well under a
# 512MB instance (~265MB resident; the serving code never imports torch).

FROM python:3.10-slim

WORKDIR /code

COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./models /code/models
COPY ./backend /code/backend
COPY ./SynthDataGen /code/SynthDataGen
COPY ./artifacts /code/artifacts

# HF Spaces runs containers as UID 1000; harmless elsewhere.
RUN useradd -m -u 1000 app && chown -R app:app /code
USER app

ENV PYTHONUNBUFFERED=1 \
    PORT=7860

EXPOSE 7860

# ~25s first-request warmup (graph build + SHAP explainer), so give the probe
# room before it starts failing.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health').read()"

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
