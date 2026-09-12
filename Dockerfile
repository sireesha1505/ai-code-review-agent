FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install CPU-only PyTorch first
RUN pip install --no-cache-dir torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]