FROM python:3.11-alpine

WORKDIR "/app"

COPY . .

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python","bot.py"]