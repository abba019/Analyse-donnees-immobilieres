FROM python:3.12-slim

WORKDIR /create-db

RUN pip install pandas psycopg2-binary sqlalchemy openpyxl

COPY ./create_and_load_db.py /create-db/
COPY ./dbfiles /create-db/dbfiles

CMD ["python", "create_and_load_db.py"]
