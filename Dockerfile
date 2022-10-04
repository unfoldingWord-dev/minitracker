FROM python:alpine

# Working from /app
WORKDIR /app

COPY main.py .

COPY requirements.txt .
COPY templates ./templates
COPY static ./static

# Install requirements
# Disable caching, to keep Docker image lean
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "main.py" ]
