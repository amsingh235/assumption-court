# Hugging Face Spaces (Docker SDK). Spaces run containers as uid 1000 and route traffic to port 7860.
# Secrets (GEMINI_API_KEY, GEMINI_MODEL, FRONTEND_ORIGIN, ...) are injected as env vars from the Space settings.
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user app ./app
COPY --chown=user prompts ./prompts
COPY --chown=user cached_cases ./cached_cases
RUN mkdir -p logs

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
