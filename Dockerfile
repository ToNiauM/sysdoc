# Imagem da aplicação web SysDoc (D-02, plano 07-04).
#
# Dois estágios: o primeiro compila o CSS do Tailwind, o segundo é o runtime
# Python. A imagem instala o SysDoc com o extra opcional "web" e sobe como
# usuário não-root. Nenhuma chave de API de provedor de LLM entra nesta
# imagem: elas chegam em runtime via montagem somente-leitura de ~/.sysdoc
# (D-05) ou via variável de ambiente do compose — nunca ENV/ARG aqui.

# ---------------------------------------------------------------------------
# Estágio 1 — CSS
# ---------------------------------------------------------------------------
# O Tailwind é COMPILADO, nunca servido por CDN: a política do projeto é não
# depender de rede externa em runtime. O binário do node existe só aqui e não
# entra na imagem final.
FROM node:20-alpine AS assets

WORKDIR /build

COPY tailwind.config.js ./
COPY core/static/src ./core/static/src
# Os `content` globs do tailwind.config.js apontam para os templates. Sem
# copiá-los, o Tailwind não encontra classe nenhuma e gera um CSS vazio —
# a página sobe sem estilo e sem erro. A verificação de tamanho abaixo é
# justamente para isso falhar no build, não em produção.
COPY core/templates ./core/templates
COPY sysdoc_web/templates ./sysdoc_web/templates

RUN npx --yes tailwindcss@3.4.17 \
        -c ./tailwind.config.js \
        -i ./core/static/src/input.css \
        -o ./core/static/dist/tailwind.css \
        --minify \
    && CSS_BYTES=$(wc -c < ./core/static/dist/tailwind.css) \
    && echo "tailwind.css gerado: ${CSS_BYTES} bytes" \
    && if [ "${CSS_BYTES}" -lt 10000 ]; then \
         echo "ERRO: CSS suspeito de vazio (${CSS_BYTES} bytes)." >&2; \
         echo "Os content globs do tailwind.config.js não casaram com nenhum template." >&2; \
         exit 1; \
       fi

# ---------------------------------------------------------------------------
# Estágio 2 — runtime
# ---------------------------------------------------------------------------
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
COPY --from=assets /build/core/static/dist/tailwind.css /app/core/static/dist/tailwind.css

RUN pip install --no-cache-dir -e ".[web]"

RUN mkdir -p /dados \
    && chown -R sysdoc:sysdoc /dados /app

ENV SYSDOC_WEB_DATA_DIR=/dados \
    HOME=/home/sysdoc

USER sysdoc

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
