#!/usr/bin/env bash
# Atalho para operar a aplicação NO SERVIDOR.
#
# Existe por um motivo concreto: em produção o compose precisa SEMPRE dos
# dois arquivos. Rodar `docker compose up` sozinho usa apenas o
# `docker-compose.yml`, que é o modo local — ele publica a porta 8000 em
# 0.0.0.0, o que neste servidor colide com outro projeto E deixa a aplicação
# exposta direto na internet, sem passar pelo nginx. Esquecer o
# `-f docker-compose.prod.yml` é fácil e o estrago é silencioso.
#
# Uso:
#   ./prod.sh up          — sobe/reconstrói
#   ./prod.sh logs        — acompanha os logs
#   ./prod.sh ps          — estado do container
#   ./prod.sh restart     — reinicia
#   ./prod.sh down        — derruba (PRESERVA o banco)
#   ./prod.sh usuario     — cria uma conta
#   ./prod.sh <qualquer>  — repassa para o docker compose
#
# NUNCA use `down -v` aqui: o -v apaga o volume, ou seja, o banco, as contas
# e todos os processos analisados. Para trocar de imagem, `up` já basta.
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

case "${1:-}" in
  up)
    shift
    "${COMPOSE[@]}" up -d --build "$@"
    ;;
  logs)
    shift
    "${COMPOSE[@]}" logs -f web "$@"
    ;;
  usuario)
    read -rp "E-mail: " EMAIL
    read -rsp "Senha: " SENHA; echo
    "${COMPOSE[@]}" exec -T \
      -e DJANGO_SUPERUSER_EMAIL="$EMAIL" \
      -e DJANGO_SUPERUSER_PASSWORD="$SENHA" \
      web python manage.py createsuperuser --noinput
    unset SENHA
    ;;
  down)
    # Barra o -v explicitamente: é destrutivo e irreversível.
    for arg in "$@"; do
      if [ "$arg" = "-v" ] || [ "$arg" = "--volumes" ]; then
        echo "Recusado: '$arg' apagaria o banco, as contas e os processos analisados." >&2
        echo "Se é isso mesmo que você quer, rode o docker compose direto, com os dois -f." >&2
        exit 1
      fi
    done
    shift
    "${COMPOSE[@]}" down "$@"
    ;;
  "")
    echo "Uso: ./prod.sh {up|logs|ps|restart|down|usuario}" >&2
    exit 1
    ;;
  *)
    "${COMPOSE[@]}" "$@"
    ;;
esac
