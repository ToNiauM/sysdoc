"""
Testes estáticos de configuração de container (plano 07-04).

Nenhum destes testes precisa de Docker instalado nem de Django: são
asserções de leitura de arquivo sobre `docker-compose.yml` e
`docker/entrypoint.sh`, travando as invariantes de D-02 (um único
comando de subida), D-05 (nenhum segredo embutido) e D-14 (uma análise
por vez, sem broker externo).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPOSE_PATH = ROOT / "docker-compose.yml"
ENTRYPOINT_PATH = ROOT / "docker" / "entrypoint.sh"
DOCKERIGNORE_PATH = ROOT / ".dockerignore"


def _carregar_compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def _linhas_entrypoint() -> list[str]:
    return [
        linha
        for linha in ENTRYPOINT_PATH.read_text(encoding="utf-8").splitlines()
        if not linha.strip().startswith("#")
    ]


def test_compose_tem_um_unico_servico():
    dados = _carregar_compose()
    assert list(dados["services"]) == ["web"]


def test_compose_nao_usa_broker():
    texto = COMPOSE_PATH.read_text(encoding="utf-8")
    assert not re.search(r"redis|celery|rabbit|broker", texto, re.IGNORECASE)


def test_compose_nao_contem_segredo_literal():
    dados = _carregar_compose()
    ambiente = dados["services"]["web"].get("environment", {})
    chaves_provedor = (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
    )
    for chave, valor in ambiente.items():
        valor_str = str(valor)
        assert "sk-" not in valor_str
        if chave in chaves_provedor:
            assert valor_str.startswith("${") and valor_str.endswith("}")


def test_compose_declara_volume_de_dados():
    dados = _carregar_compose()
    assert "sysdoc-dados" in dados["volumes"]
    volumes_web = dados["services"]["web"]["volumes"]
    assert any(
        (isinstance(v, str) and v.startswith("sysdoc-dados:/dados"))
        for v in volumes_web
    )


def test_compose_monta_config_do_servidor_somente_leitura():
    dados = _carregar_compose()
    volumes_web = dados["services"]["web"]["volumes"]
    montagens_ro = [
        v for v in volumes_web if isinstance(v, str) and v.rstrip().endswith(":ro")
    ]
    assert any(".sysdoc" in v for v in montagens_ro)


def test_entrypoint_roda_migrate_e_saneamento_antes_do_servidor():
    linhas = _linhas_entrypoint()
    indice_migrate = next(i for i, l in enumerate(linhas) if "manage.py migrate" in l)
    indice_saneamento = next(
        i for i, l in enumerate(linhas) if "manage.py sanear_jobs" in l
    )
    indice_runworker = next(i for i, l in enumerate(linhas) if "runworker" in l)
    indice_gunicorn = next(i for i, l in enumerate(linhas) if "exec gunicorn" in l)
    assert indice_migrate < indice_gunicorn
    assert indice_saneamento < indice_gunicorn
    assert indice_runworker < indice_gunicorn


def test_gunicorn_com_um_worker():
    linhas = _linhas_entrypoint()
    linha_gunicorn = next(l for l in linhas if "exec gunicorn" in l)
    assert "--workers 1" in linha_gunicorn
    assert "--threads 4" in linha_gunicorn
    assert "--workers 2" not in linha_gunicorn
    assert "-w " not in linha_gunicorn


def test_dockerignore_exclui_material_do_usuario():
    texto = DOCKERIGNORE_PATH.read_text(encoding="utf-8")
    for entrada in ("processo-teste", "Referencias", ".git"):
        assert entrada in texto
