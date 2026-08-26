"""
Testes de preços de modelos configuráveis por alvo (P5) —
sysdoc_dvi.config.carregar_precos_dvi, sysdoc_dvi.cli.config (--preco/--listar)
e a precedência sobre a tabela embutida em sysdoc_dvi.provedores.

Nenhum teste toca `~/.sysdoc/config.json` real: `HOME` é sempre monkeypatchado
para `tmp_path`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi import cli  # noqa: E402
from sysdoc_dvi.config import carregar_precos_dvi  # noqa: E402
from sysdoc_dvi.provedores import _preco_estimado  # noqa: E402


def _config_path(tmp_path: Path) -> Path:
    return tmp_path / ".sysdoc" / "config.json"


def _escrever_config(tmp_path: Path, dados: dict) -> Path:
    caminho = _config_path(tmp_path)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


class TestGravarPreco:
    def test_preco_gravado_preserva_demais_chaves(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        _escrever_config(
            tmp_path,
            {
                "dvi": {"economico": "openrouter/deepseek-chat", "forte": "anthropic/claude-opus-5"},
                "api_keys": {"anthropic": "sk-ant-teste"},
            },
        )

        rc = cli.config(precos=[["openrouter/openai/gpt-5.6-luna", "1.25", "10.0"]])
        assert rc == 0

        dados = json.loads(_config_path(tmp_path).read_text(encoding="utf-8"))
        assert dados["dvi"]["economico"] == "openrouter/deepseek-chat"
        assert dados["dvi"]["forte"] == "anthropic/claude-opus-5"
        assert dados["dvi"]["precos"]["openrouter/openai/gpt-5.6-luna"] == {
            "entrada": 1.25,
            "saida": 10.0,
        }
        assert dados["api_keys"] == {"anthropic": "sk-ant-teste"}

    def test_precos_multiplos_se_acumulam_sem_apagar_anteriores(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        cli.config(precos=[["openrouter/deepseek-chat", "0.28", "0.42"]])
        cli.config(precos=[["anthropic/claude-opus-5", "15", "75"]])

        dados = json.loads(_config_path(tmp_path).read_text(encoding="utf-8"))
        precos = dados["dvi"]["precos"]
        assert precos["openrouter/deepseek-chat"] == {"entrada": 0.28, "saida": 0.42}
        assert precos["anthropic/claude-opus-5"] == {"entrada": 15.0, "saida": 75.0}

    def test_arquivo_gravado_com_permissao_0600(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        cli.config(precos=[["openrouter/deepseek-chat", "0.28", "0.42"]])
        modo = _config_path(tmp_path).stat().st_mode & 0o777
        assert modo == 0o600


class TestListarPreco:
    def test_listar_mostra_precos_registrados_sem_ecoar_chave(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("HOME", str(tmp_path))
        _escrever_config(
            tmp_path,
            {
                "dvi": {
                    "economico": "openrouter/deepseek-chat",
                    "forte": "anthropic/claude-opus-5",
                    "precos": {"openrouter/deepseek-chat": {"entrada": 0.28, "saida": 0.42}},
                },
                "api_keys": {"openrouter": "sk-or-secreta"},
            },
        )

        rc = cli.config(listar=True)
        assert rc == 0
        saida = capsys.readouterr().out
        assert "openrouter/deepseek-chat: entrada 0.28, saída 0.42" in saida
        assert "sk-or-secreta" not in saida

    def test_listar_sem_preco_mostra_mensagem_padrao(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("HOME", str(tmp_path))
        _escrever_config(tmp_path, {"dvi": {"economico": "a/b", "forte": "c/d"}})

        cli.config(listar=True)
        saida = capsys.readouterr().out
        assert "<nenhum preço registrado>" in saida


class TestValidacaoNaEscrita:
    def test_alvo_malformado_devolve_1_e_nao_grava(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        rc = cli.config(precos=[["modelo-sem-barra", "1.0", "2.0"]])
        assert rc == 1
        assert not _config_path(tmp_path).is_file()

    def test_provedor_nao_suportado_devolve_1_e_nao_grava(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        rc = cli.config(precos=[["provedor-invalido/modelo-x", "1.0", "2.0"]])
        assert rc == 1
        assert not _config_path(tmp_path).is_file()

    def test_valor_nao_numerico_devolve_1_e_nao_grava(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        rc = cli.config(precos=[["openrouter/deepseek-chat", "gratis", "2.0"]])
        assert rc == 1
        assert not _config_path(tmp_path).is_file()

    def test_valor_negativo_devolve_1_e_nao_grava(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        rc = cli.config(precos=[["openrouter/deepseek-chat", "-1.0", "2.0"]])
        assert rc == 1
        assert not _config_path(tmp_path).is_file()

    def test_nada_para_atualizar_cita_preco(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        rc = cli.config()
        assert rc == 1
        saida = capsys.readouterr().out
        assert "--preco" in saida


class TestCarregarPrecosDvi:
    def test_ignora_entradas_malformadas_e_coage_para_float(self, tmp_path):
        config_path = _escrever_config(
            tmp_path,
            {
                "dvi": {
                    "precos": {
                        "openrouter/deepseek-chat": {"entrada": "0.28", "saida": "0.42"},
                        "openrouter/sem-saida": {"entrada": 1.0},
                        "openrouter/negativo": {"entrada": -1.0, "saida": 2.0},
                        "openrouter/nao-e-objeto": "gratis",
                    }
                }
            },
        )

        precos = carregar_precos_dvi(config_path)
        assert precos == {"openrouter/deepseek-chat": {"entrada": 0.28, "saida": 0.42}}

    def test_sem_arquivo_devolve_dicionario_vazio(self, tmp_path):
        assert carregar_precos_dvi(tmp_path / "inexistente.json") == {}


class TestPrecedenciaSobreTabelaEmbutida:
    def test_preco_configurado_produz_custo_diferente_de_zero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        _escrever_config(
            tmp_path,
            {"dvi": {"precos": {"openrouter/deepseek-chat": {"entrada": 1.0, "saida": 2.0}}}},
        )

        custo = _preco_estimado("openrouter/deepseek-chat", 1_000_000, 500_000)
        assert custo == pytest.approx(1.0 * 1 + 2.0 * 0.5)

    def test_alvo_sem_preco_configurado_gera_custo_zero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        custo = _preco_estimado("openrouter/modelo-sem-preco", 1000, 1000)
        assert custo == 0.0


class TestAvisoComRemedio:
    def test_alvo_sem_preco_gera_aviso_com_comando_pronto(self):
        from sysdoc_dvi.relatorio import montar_relatorio

        registro = [
            {
                "provedor": "openrouter",
                "modelo": "modelo-sem-preco",
                "tokens_entrada": 100,
                "tokens_saida": 50,
                "custo_estimado": 0.0,
                "duracao_s": 1.0,
            }
        ]
        from sysdoc_dvi.tipos import ResultadoItem

        item = ResultadoItem(
            checklist_id="DVI-X",
            origem_verificacao="llm",
            documento="ETP",
            seção="1",
            de="trecho",
            para="trecho revisado",
            parecer="parecer",
            fundamento="fundamento",
            classificação="conforme",
            severidade="baixa",
            risco_jurídico="informativo",
        )
        relatorio = montar_relatorio([item], "hash", "1.1", 1.0, registro_chamadas=registro)
        aviso = next(a for a in relatorio["avisos"] if "openrouter/modelo-sem-preco" in a)
        assert "sysdoc-dvi config --preco openrouter/modelo-sem-preco" in aviso
