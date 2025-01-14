FROM python:3.12-slim

WORKDIR /update-db-dw

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./webscraping.py /update-db-dw/

CMD ["python", "webscraping.py"]
