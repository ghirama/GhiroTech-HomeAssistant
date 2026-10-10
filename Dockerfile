ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}
WORKDIR /app
COPY app.py index.html prezzario.sqlite ./
RUN mkdir -p /data
CMD ["python3", "-u", "app.py"]
