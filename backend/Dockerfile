FROM python:3.11 as build

WORKDIR /app

ENV PYTHONPATH=/app

# Install Poetry
RUN curl -k -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Install Chromium for web loader
# Can disable this if you don't use the web loader to reduce the image size
RUN apt update && apt install -y openjdk-17-jre libaio1 libaio-dev unzip libgl1-mesa-glx poppler-utils tesseract-ocr-por

# Install dependencies
COPY ./pyproject.toml ./poetry.lock* /app/
RUN poetry install --no-root --no-cache --only main

# ====================================
FROM build as release

COPY . .

CMD ["python", "main.py"]