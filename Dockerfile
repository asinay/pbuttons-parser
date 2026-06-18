FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py pbuttons_parser.py ./
COPY analyzers/ ./analyzers/
COPY static/ ./static/

# Create runtime directories
RUN mkdir -p uploads outputs

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
