# Imagem única para a aplicação web SysDoc (D-02, plano 07-04).
#
# Estágio único sobre python:3.12-slim. A imagem instala o SysDoc com o
# extra opcional "web" (Django + gunicorn) e sobe como usuário não-root.
# Nenhuma chave de API de provedor de LLM entra nesta imagem: elas chegam
# em runtime via montagem somente-leitura de ~/.sysdoc (D-05) ou via
# variável de ambiente do compose — nunca ENV/ARG neste Dockerfile.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 sysdoc \
    && useradd --uid 10001 --gid sysdoc --home-dir /home/sysdoc --create-home --shell /usr/sbin/nologin sysdoc

COPY . /app

RUN pip install --no-cache-dir -e ".[web]"

RUN mkdir -p /dados \
    && chown -R sysdoc:sysdoc /dados /app

ENV SYSDOC_WEB_DATA_DIR=/dados \
    HOME=/home/sysdoc

USER sysdoc

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
