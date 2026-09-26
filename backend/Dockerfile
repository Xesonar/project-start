FROM python:3.12-slim

WORKDIR /app

# MAX's API domains (platform-api2.max.ru) are signed by the Russian
# government's "Mintsifry" root/intermediate CAs, which aren't in any
# standard trust store outside Russia. Without this, every outbound call in
# max_bot_client.py fails with CERTIFICATE_VERIFY_FAILED — verified this by
# hitting the real API from this exact base image before adding the fix.
COPY certs/*.crt /usr/local/share/ca-certificates/
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# httpx/requests trust certifi's own bundled CA file by default, not the OS
# trust store update-ca-certificates just updated — so the Mintsifry CAs
# need to land there too, or this fix only helps tools that don't use certifi.
RUN cat /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
        /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt \
        >> "$(python -c 'import certifi; print(certifi.where())')"

COPY . .
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
