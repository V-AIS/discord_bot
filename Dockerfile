FROM python:3.11-alpine

WORKDIR "/app"

COPY . .

RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

RUN pip3 install --no-cache-dir -r requirements.txt

# 프로세스 생존이 아니라 각 tasks.loop 의 마지막 성공 시각을 본다.
# start-period 동안은 실패해도 unhealthy 로 세지 않는다.
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD ["python", "healthcheck.py"]

CMD ["python","bot.py"]