FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install curl -y

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "main.py"]