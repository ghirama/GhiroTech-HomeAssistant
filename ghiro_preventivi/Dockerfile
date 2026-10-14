ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}
WORKDIR /app
COPY app.py pdf_plan.py price_import.py auth.py index.html editor.html prezzario.sqlite manifest.webmanifest icon.svg ./
RUN apk add --no-cache poppler-utils font-dejavu && mkdir -p /data
CMD ["python3", "-u", "app.py"]
