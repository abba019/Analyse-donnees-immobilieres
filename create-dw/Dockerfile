FROM python:3.12-slim

WORKDIR /create-dw

RUN pip install datetime psycopg2-binary

COPY ./create_and_load_dw.py /create-dw/

CMD ["python", "create_and_load_dw.py"]
