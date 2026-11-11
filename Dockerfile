# One image for both Python services; docker-compose picks the command per service.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mathpath_common mathpath_common
COPY content_service content_service
COPY practice_service practice_service
COPY scripts scripts
COPY seed seed
RUN useradd --system app && chown -R app /app
USER app
