FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Never run as root; never mount the Docker socket (see deploy role).
RUN useradd --uid 10001 --shell /usr/sbin/nologin --no-create-home bridge
USER bridge

EXPOSE 8642
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8642"]
