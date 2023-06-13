FROM python:3.10-alpine

WORKDIR "/app"

COPY . .

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

RUN pip3 install -r requirements.txt

CMD ["python","bot.py"]