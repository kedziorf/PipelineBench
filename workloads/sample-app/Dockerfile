FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY benchmark/ benchmark/
COPY tests/ tests/

CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
