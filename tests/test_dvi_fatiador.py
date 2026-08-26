"""
Testes do fatiador determinístico de peças (P1) — sysdoc.detectar_fronteiras_pecas,
sysdoc.fatiar_texto_por_pecas, sysdoc.escrever_fatias_virtuais, `sysdoc.prepare` num
projeto de documento único e `sysdoc_dvi.pecas.mapear_pecas` consumindo as fatias.

Cobre: detecção de fronteira em linha própria, menção no meio de frase ignorada,
fatia curta descartada, ambiguidade sem fatiamento, offsets consistentes com o
texto original gravados pelo `prepare`, resolução `fatiamento`/`arquivo-inteiro`
sem `config.yaml`, override ainda apontando para o arquivo inteiro, regressão
multi-arquivo (sem entradas virtuais) e rastreabilidade do `de` retirado de uma
fatia contra `templates/validate_sysdoc.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "templates"))

import sysdoc  # noqa: E402
from sysdoc_dvi.pecas import mapear_pecas  # noqa: E402

import validate_sysdoc  # noqa: E402


CORPO_ETP = (
    "1. Necessidade da contratação\n"
    "A necessidade da contratação decorre da substituição de equipamentos obsoletos.\n"
    + ("Texto de preenchimento adicional sobre o objeto do estudo técnico preliminar. " * 40)
    + "A estimativa das quantidades considera o consumo médio dos últimos doze meses.\n"
)

CORPO_TR = (
    "1. Critérios de medição e pagamento\n"
    "Os critérios de medição e pagamento seguem a tabela anexa a este termo.\n"
    + ("Texto de preenchimento adicional sobre a execução contratual do termo de referência. " * 40)
    + "As obrigações da contratada incluem relatórios mensais de desempenho.\n"
)

CORPO_RISCOS = (
    "1. Probabilidade e impacto\n"
    "A probabilidade de atraso é média e o impacto financeiro é considerado relevante.\n"
    + ("Texto de preenchimento adicional sobre riscos identificados na contratação. " * 40)
    + "A ação preventiva recomendada é o monitoramento mensal do cronograma físico.\n"
)


def _texto_processo_unico() -> str:
    return (
        "PROCESSO ADMINISTRATIVO Nº 12345.678900/2026-00\n"
        + ("Filler antes de qualquer peça, sem cabeçalho reconhecível.\n" * 5)
        + "\nESTUDO TÉCNICO PRELIMINAR\n\n"
        + CORPO_ETP
        + "\nTERMO DE REFERÊNCIA\n\n"
        + CORPO_TR
        + "\nMAPA DE RISCOS\n\n"
        + CORPO_RISCOS
    )


class TestDeteccaoDeFronteira:
    def test_cabecalho_em_linha_propria_e_detectado_com_offset(self):
        texto = _texto_processo_unico()
        fronteiras = sysdoc.detectar_fronteiras_pecas(texto)
        pecas_detectadas = [peca for _, peca in fronteiras]
        assert pecas_detectadas == ["ETP", "TR", "RISCOS"]

        offset_etp = texto.index("ESTUDO TÉCNICO PRELIMINAR")
        offset_tr = texto.index("TERMO DE REFERÊNCIA")
        offset_riscos = texto.index("MAPA DE RISCOS")
        assert fronteiras[0] == (offset_etp, "ETP")
        assert fronteiras[1] == (offset_tr, "TR")
        assert fronteiras[2] == (offset_riscos, "RISCOS")

    def test_mencao_no_meio_de_frase_nao_e_fronteira(self):
        texto = "Texto qualquer conforme o Termo de Referência anexo a este processo administrativo."
        fronteiras = sysdoc.detectar_fronteiras_pecas(texto)
        assert fronteiras == []


class TestFatiamento:
    def test_fatia_menor_que_o_minimo_e_descartada(self):
        texto = (
            "ESTUDO TÉCNICO PRELIMINAR\n"
            "Texto curto que não atinge o mínimo de caracteres exigido para a fatia.\n"
            "TERMO DE REFERÊNCIA\n" + CORPO_TR
        )
        fatias = sysdoc.fatiar_texto_por_pecas(texto)
        assert "ETP" not in fatias
        assert "TR" in fatias

    def test_ambiguidade_entre_duas_fatias_grandes_da_mesma_peca_nao_fatiam(self):
        texto = (
            "ESTUDO TÉCNICO PRELIMINAR\n" + CORPO_ETP
            + "ESTUDO TÉCNICO PRELIMINAR\n" + CORPO_ETP
        )
        fatias = sysdoc.fatiar_texto_por_pecas(texto)
        assert "ETP" not in fatias

    def test_texto_sem_fronteiras_nao_fatia_nada(self):
        assert sysdoc.fatiar_texto_por_pecas("texto qualquer sem nenhum cabeçalho reconhecível") == {}


def _preparar_projeto_documento_unico(tmp_path, monkeypatch, nome_pasta="ProjetoUnico"):
    projeto_dir = tmp_path / nome_pasta
    docs = projeto_dir / "documentos"
    docs.mkdir(parents=True)
    (docs / "Processo_042.txt").write_text(_texto_processo_unico(), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    rc = sysdoc.prepare(nome_pasta)
    assert rc == 0
    return projeto_dir


class TestPrepareDocumentoUnico:
    def test_prepare_grava_fatias_com_offsets_consistentes(self, tmp_path, monkeypatch):
        projeto_dir = _preparar_projeto_documento_unico(tmp_path, monkeypatch)

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        virtuais = [item for item in manifest["files"] if item.get("virtual")]
        pecas_virtuais = {item["peca"] for item in virtuais}
        assert pecas_virtuais == {"ETP", "TR", "RISCOS"}

        base_entry = next(item for item in manifest["files"] if not item.get("virtual"))
        texto_original = (projeto_dir / base_entry["cache"]).read_text(encoding="utf-8")

        for item in virtuais:
            fatia_path = projeto_dir / item["cache"]
            conteudo_fatia = fatia_path.read_text(encoding="utf-8")
            assert texto_original[item["offset_inicio"]:item["offset_fim"]] == conteudo_fatia

    def test_prepare_imprime_pecas_fatiadas(self, tmp_path, monkeypatch, capsys):
        _preparar_projeto_documento_unico(tmp_path, monkeypatch)
        saida = capsys.readouterr().out
        assert "Peças fatiadas do documento único" in saida

    def test_prepare_sem_fronteira_imprime_mensagem_de_fallback(self, tmp_path, monkeypatch, capsys):
        projeto_dir = tmp_path / "ProjetoSemCabecalho"
        docs = projeto_dir / "documentos"
        docs.mkdir(parents=True)
        (docs / "PROCESSO.txt").write_text(
            "Texto de processo sem nenhum cabeçalho de peça reconhecível.", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        sysdoc.prepare("ProjetoSemCabecalho")
        saida = capsys.readouterr().out
        assert "nenhuma fronteira inequívoca" in saida

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        assert not any(item.get("virtual") for item in manifest["files"])


class TestMapeamentoSemConfig:
    def test_pecas_fatiadas_resolvem_com_origem_fatiamento_e_demais_com_arquivo_inteiro(
        self, tmp_path, monkeypatch
    ):
        projeto_dir = _preparar_projeto_documento_unico(tmp_path, monkeypatch)

        resultado = mapear_pecas(
            projeto_dir, exigidas={"ETP", "TR", "MCP", "RISCOS", "PROCESSO"}
        )

        assert resultado["ETP"].origem == "fatiamento"
        assert resultado["TR"].origem == "fatiamento"
        assert resultado["RISCOS"].origem == "fatiamento"
        assert resultado["MCP"].origem == "arquivo-inteiro"
        assert resultado["PROCESSO"].origem == "arquivo-inteiro"
        assert not (projeto_dir / ".sysdoc" / "config.yaml").is_file()

    def test_arquivo_inteiro_aponta_para_o_cache_do_documento_base(self, tmp_path, monkeypatch):
        projeto_dir = _preparar_projeto_documento_unico(tmp_path, monkeypatch)
        resultado = mapear_pecas(projeto_dir, exigidas={"PROCESSO"})

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        base_entry = next(item for item in manifest["files"] if not item.get("virtual"))
        caminho_base_esperado = (projeto_dir / base_entry["cache"]).resolve()

        assert resultado["PROCESSO"].caminho == caminho_base_esperado


class TestOverrideContinuaVencendo:
    def test_override_via_config_yaml_ainda_aponta_para_arquivo_inteiro(self, tmp_path, monkeypatch):
        projeto_dir = _preparar_projeto_documento_unico(tmp_path, monkeypatch)
        (projeto_dir / ".sysdoc").mkdir(parents=True, exist_ok=True)
        (projeto_dir / ".sysdoc" / "config.yaml").write_text(
            yaml.safe_dump({"pecas": {"tr": "processo_042.txt"}}, allow_unicode=True),
            encoding="utf-8",
        )

        resultado = mapear_pecas(projeto_dir, exigidas={"TR"})

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        base_entry = next(item for item in manifest["files"] if not item.get("virtual"))
        caminho_base_esperado = (projeto_dir / base_entry["cache"]).resolve()

        assert resultado["TR"].origem == "override"
        assert resultado["TR"].caminho == caminho_base_esperado


class TestRegressaoMultiArquivo:
    def test_projeto_multi_arquivo_nao_gera_entradas_virtuais(self, tmp_path, monkeypatch):
        projeto_dir = tmp_path / "ProjetoMultiArquivo"
        docs = projeto_dir / "documentos"
        docs.mkdir(parents=True)
        (docs / "ETP.txt").write_text(CORPO_ETP, encoding="utf-8")
        (docs / "TR.txt").write_text(CORPO_TR, encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.prepare("ProjetoMultiArquivo")
        assert rc == 0

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        assert not any(item.get("virtual") for item in manifest["files"])

        resultado = mapear_pecas(projeto_dir, exigidas={"ETP", "TR"})
        assert resultado["ETP"].origem in {"ancora", "nome"}
        assert resultado["TR"].origem in {"ancora", "nome"}


class TestRastreabilidade:
    def test_de_literal_de_fatia_de_etp_e_rastreavel_no_documento_especifico(
        self, tmp_path, monkeypatch
    ):
        projeto_dir = _preparar_projeto_documento_unico(tmp_path, monkeypatch)
        etp_texto = (
            projeto_dir / ".sysdoc" / "cache" / "textos" / "documentos" / "ETP.txt"
        ).read_text(encoding="utf-8")

        trecho = "A necessidade da contratação decorre da substituição de equipamentos obsoletos."
        assert trecho in etp_texto
        assert validate_sysdoc.is_traceable(trecho, etp_texto)

    def test_de_de_outra_parte_do_processo_e_rastreavel_pela_uniao(self, tmp_path, monkeypatch):
        projeto_dir = _preparar_projeto_documento_unico(tmp_path, monkeypatch)

        riscos_texto = (
            projeto_dir / ".sysdoc" / "cache" / "textos" / "documentos" / "RISCOS.txt"
        ).read_text(encoding="utf-8")
        trecho = "A ação preventiva recomendada é o monitoramento mensal do cronograma físico."
        assert trecho in riscos_texto

        sources = validate_sysdoc.load_source_texts(projeto_dir)
        assert "ETP" in sources and "TR" in sources
        assert not validate_sysdoc.is_traceable(trecho, sources.get("ETP", ""))

        uniao = validate_sysdoc.load_union_source_text(projeto_dir, sources)
        assert uniao is not None
        assert validate_sysdoc.is_traceable(trecho, uniao)
