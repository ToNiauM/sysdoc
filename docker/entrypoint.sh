#!/bin/sh
# Entrypoint do container web do SysDoc (D-02, D-14, D-15, plano 07-04).
#
# `docker compose up` é o único comando do administrador: este script faz
# tudo o que precisa acontecer antes de servir — segredo, migração,
# estáticos, saneamento de jobs órfãos e o worker single-slot — para que
# nenhum passo manual de migração ou seed sobre no administrador.
set -eu

DADOS_DIR="${SYSDOC_WEB_DATA_DIR:-/dados}"
SECRET_FILE="${DADOS_DIR}/secret_key"

# 1. Segredo persistido no volume: gerado uma única vez, reaproveitado nas
# subidas seguintes, para que sessões e tokens CSRF não sejam invalidados
# a cada reinício do container (T-07-04-05).
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    if [ ! -f "${SECRET_FILE}" ]; then
        python -c "import secrets; print(secrets.token_urlsafe(50))" > "${SECRET_FILE}"
        chmod 600 "${SECRET_FILE}"
    fi
    DJANGO_SECRET_KEY="$(cat "${SECRET_FILE}")"
    export DJANGO_SECRET_KEY
fi

# 2. Falha cedo e com mensagem clara se o extra "web" não estiver instalado.
python -m django --version

# 3. Migração do banco — nenhum passo manual do administrador.
python manage.py migrate --noinput

# 4. Estáticos coletados para STATIC_ROOT (dentro do volume de dados).
python manage.py collectstatic --noinput

# 5. Saneamento de jobs órfãos de uma subida anterior (D-15): qualquer job
# que ficou "em_execucao" quando o container caiu vira "interrompida",
# nunca uma mentira eterna de "em andamento" na tela do pregoeiro.
python manage.py sanear_jobs

# 6. Worker single-slot em segundo plano, num laço de reinício. Exatamente
# um processo `runworker` — nunca dois — é a segunda metade da trava de
# "uma análise por vez" (D-14); a primeira metade é a UniqueConstraint do
# banco (plano 07-03), que nenhum worker adicional conseguiria driblar de
# qualquer forma, mas o compose não sobe um segundo por disciplina mesmo
# assim.
while true; do
    python manage.py runworker --intervalo "${SYSDOC_WEB_INTERVALO_WORKER:-2}"
    sleep 5
done &

echo "Para criar o primeiro usuário: docker compose exec web python manage.py createsuperuser"

# 7. Servidor de aplicação. `--workers 1` é obrigatório: é a garantia de
# que o processo do servidor em si nunca tem duas réplicas concorrentes
# (T-07-04-04, D-14). `--threads 4` é intencional, não um default
# acidental: o paralelismo de thread serve só ao polling de progresso e ao
# upload (plano 07-06), nunca à execução da análise (que continua isolada
# no laço do worker acima). É seguro porque a corrida de lock entre
# threads no SQLite já está coberta em duas pontas: o `timeout` das
# settings (07-02) faz o driver esperar em vez de falhar na hora, e
# `fila.enfileirar` converte tanto `IntegrityError` quanto
# `OperationalError` em `FilaOcupada` (07-03) — sem essas duas defesas,
# `--threads 4` transformaria a recusa "análise em andamento" num 500
# genérico.
exec gunicorn sysdoc_web.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile -
