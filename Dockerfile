FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir ".[server]"

ENV EMBEDDED_MODE=true
ENV SES_DATA_DIR=/data/ses
ENV SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "-m", "ses.server.__main__"]
