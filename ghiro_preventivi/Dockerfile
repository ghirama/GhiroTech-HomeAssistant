ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}
WORKDIR /app
COPY app.py auth.py index.html editor.html prezzario.sqlite manifest.webmanifest icon.svg ./
RUN mkdir -p /data
CMD ["python3", "-u", "app.py"]
