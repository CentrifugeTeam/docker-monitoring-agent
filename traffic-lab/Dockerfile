FROM alpine

RUN apk add --no-cache bash curl netcat-openbsd python3 && \
    rm -rf /var/cache/apk/*

RUN apk add --no-cache bash curl netcat-openbsd python3

WORKDIR /app
COPY testfile.txt .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
