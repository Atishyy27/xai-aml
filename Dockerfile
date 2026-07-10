# SENTINEL API -- Hugging Face Spaces (Docker SDK).
# The UI is not in this image; it deploys to Vercel and calls this over CORS.
#
# Two things this file must get right, both of which the previous version got
# wrong and neither of which shows up until you build from a clean clone:
#
#   1. artifacts/ is gitignored, so it does not exist in a fresh checkout. The
#      old `COPY . /code/` produced a container with no models, and the app died
#      on boot with FileNotFoundError: artifacts/scaler.pkl. Training happens
#      here, at build time, so the image is self-contained.
#   2. `COPY . /code/` also copied .env -- Neo4j Aura credentials -- into a
#      public image layer. See .dockerignore.

FROM python:3.10-slim

# Torch ships a ~2.5GB CUDA wheel by default on Linux. The autoencoder is a
# 9-6-3-6-9 MLP scored once at startup; it will never see a GPU. The CPU index
# cuts the image by roughly an order of magnitude.
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu

WORKDIR /code

COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./models /code/models
COPY ./backend /code/backend
COPY ./SynthDataGen /code/SynthDataGen

# Bake the models in. Both trainers are seeded (random_state=42), so this is
# reproducible: the image's metrics are the metrics in the readme.
RUN python -m models.anomaly && python -m models.classifier

# HF Spaces runs containers as UID 1000. Do this after the training step so it
# can still write /code/artifacts.
RUN useradd -m -u 1000 app && chown -R app:app /code
USER app

ENV PYTHONUNBUFFERED=1 \
    PORT=7860

EXPOSE 7860

# Warmup is ~25s (graph build + SHAP explainer), so give the healthcheck room to
# clear the lifespan handler before it starts failing.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health').read()"

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
