ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}
WORKDIR /app
COPY excel_quote.py quote_template.b64 pdf_summary.py app.py storage.py pdf_plan.py price_import.py auth.py index.html editor.html prezzario.sqlite manifest.webmanifest icon.svg logo.jpg ./
RUN pip install --no-cache-dir "reportlab>=4.2,<5"
RUN apk add --no-cache poppler-utils font-dejavu && mkdir -p /data
CMD ["python3", "-u", "app.py"]
