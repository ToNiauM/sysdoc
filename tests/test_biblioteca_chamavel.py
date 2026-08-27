"""
Prova de que `sysdoc` e `sysdoc_dvi` são chamáveis como biblioteca pela
camada web, sem `subprocess` da CLI e sem reimplementar pipeline (D-03,
Plano 07-01).

Três frentes, adicionadas incrementalmente pelas Tasks 1-3 deste plano:

- `sysdoc.criar_documento()` devolve os caminhos gerados sem exigir leitura
  de stdout; `sysdoc.create()` continua imprimindo exatamente as mesmas
  linhas de antes (Task 1).
- `sysdoc.localizar_html_analise()` / `sysdoc.localizar_docx_despacho()`
  encontram os artefatos de download sem parsear stdout de `deploy` (Task 2).
- `sysdoc_dvi.pipeline.executar_run(..., progresso=...)` emite eventos
  estruturados a cada etapa, sem alterar a saída de terminal existente
  (Task 3).

Nenhum teste aqui chama modelo real.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers compartilhados (Task 1 / Task 2) — mesmo padrão de
# tests/test_dvi_create_variante.py, sem importar o módulo de teste alheio.
# ---------------------------------------------------------------------------

def _base_dvi_json(**overrides) -> dict:
    payload = {
        "modelo_ia": "gpt-5",
        "data_análise": "2026-08-27",
        "projeto": {
            "órgão": "Secretaria de Teste",
            "processo": "90796110000007.000039/2025-14",
            "valor_estimado": "R$ 100.000,00",
            "objeto": "Aquisição de materiais de teste",
        },
        "secao_etp": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Parecer da seção ETP consolidado.",
            "numero": "1343011",
        },
        "secao_tr": {
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer da seção TR consolidado.",
            "numero": "1343014",
        },
        "itens": [
            {
                "id": "ETP-001",
                "documento": "ETP",
                "seção": "4.20",
                "de": "texto original",
                "para": "outro texto",
                "parecer": "Parecer de ajuste necessário sobre o item analisado.",
                "fundamento": "Lei 14.133/2021 art. 18",
                "classificação": "ajuste_necessário",
                "severidade": "média",
                "risco_jurídico": "relevante",
            },
        ],
    }
    payload.update(overrides)
    return payload


def _escrever_dvi_json(project_dir: Path, **overrides) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    json_file = project_dir / "dados_consolidados.json"
    json_file.write_text(
        json.dumps(_base_dvi_json(**overrides), ensure_ascii=False),
        encoding="utf-8",
    )
    return json_file


def _projeto_dvi(tmp_path: Path, nome: str, tipo: str = "geral") -> tuple[Path, "sysdoc.ProjectPaths"]:
    """Roda `sysdoc.init_command(nome)`, marca `tipo` no `.sysdoc/config.yaml`
    e escreve um `dados_consolidados.json` válido. Precisa de `monkeypatch.
    chdir(tmp_path)` já ativo no chamador."""
    sysdoc.init_command(nome)
    project_dir = tmp_path / nome
    paths = sysdoc.project_paths(project_dir)
    config = sysdoc.load_config(paths)
    config["tipo"] = tipo
    sysdoc.write_config(paths, config)
    _escrever_dvi_json(project_dir)
    return project_dir, paths


# ---------------------------------------------------------------------------
# Task 1 — criar_documento() / create()
# ---------------------------------------------------------------------------

class TestCriarDocumento:
    def test_criar_documento_devolve_caminho_sem_ler_stdout(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _projeto_dvi(tmp_path, "ProjetoBiblioteca")

        resultado = sysdoc.criar_documento("ProjetoBiblioteca", "dvi")

        assert isinstance(resultado, sysdoc.ResultadoCreate)
        assert resultado.saida.is_file()
        assert resultado.saida.suffix == ".docx"
        assert resultado.origem_template is not None
        assert resultado.substituicoes_pendentes == 0

    def test_create_ainda_imprime_as_mesmas_linhas_e_retorna_zero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        _projeto_dvi(tmp_path, "ProjetoBibliotecaCli")

        rc = sysdoc.create("ProjetoBibliotecaCli", "dvi")

        saida = capsys.readouterr().out
        assert rc == 0
        assert "DOCX gerado: " in saida
        assert "Template DVI: " in saida
