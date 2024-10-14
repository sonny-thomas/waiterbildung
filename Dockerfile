FROM python:3.12.5

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./queue_scraper.py"]
