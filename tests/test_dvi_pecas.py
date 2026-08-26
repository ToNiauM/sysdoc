"""
Testes do mapeamento de peças (RF3) — sysdoc.detectar_ancoras/peca_sugerida
e sysdoc_dvi.pecas.mapear_pecas.

Cobre: contagem de âncoras por peça, gravação no manifest pelo `prepare`,
detecção automática (com ambiguidade e fallback por nome), override manual
em `.sysdoc/config.yaml` e o caminho de abort explícito.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402
from sysdoc_dvi.pecas import ErroMapeamentoPeca, PecaMapeada, mapear_pecas  # noqa: E402


def _escrever_texto_cache(projeto: Path, nome: str, conteudo: str) -> Path:
    destino = projeto / ".sysdoc" / "cache" / "textos" / "documentos" / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    return destino


def _escrever_manifest(projeto: Path, files: list[dict]) -> None:
    manifest_dir = projeto / ".sysdoc" / "cache"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"project": str(projeto), "files": files}
    (manifest_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _entrada(
    label: str,
    source: str,
    cache_rel: str,
    ancoras: dict[str, int],
    peca_sugerida: str | None,
    category: str = "documentos",
) -> dict:
    return {
        "label": label,
        "category": category,
        "source": source,
        "cache": cache_rel,
        "sha256": "0" * 64,
        "chars": 100,
        "words": 20,
        "ancoras": ancoras,
        "peca_sugerida": peca_sugerida,
    }


class TestAncoras:
    def test_texto_de_etp_conta_ancoras_de_etp(self):
        texto = (
            "Este Estudo Técnico Preliminar descreve a necessidade da contratação "
            "e a estimativa das quantidades a serem adquiridas."
        )
        ancoras = sysdoc.detectar_ancoras(texto)
        assert ancoras["ETP"] > 0
        assert sysdoc.peca_sugerida(ancoras) == "ETP"

    def test_texto_de_tr_conta_ancoras_de_tr(self):
        texto = (
            "O presente Termo de Referência define os critérios de medição e "
            "pagamento e as obrigações da contratada."
        )
        ancoras = sysdoc.detectar_ancoras(texto)
        assert ancoras["TR"] > 0
        assert sysdoc.peca_sugerida(ancoras) == "TR"

    def test_texto_de_mcp_conta_ancoras_de_mcp(self):
        texto = (
            "Mapa comparativo de preços com pesquisa de preços, cotação de três "
            "fornecedores e média dos preços obtidos."
        )
        ancoras = sysdoc.detectar_ancoras(texto)
        assert ancoras["MCP"] > 0
        assert sysdoc.peca_sugerida(ancoras) == "MCP"

    def test_texto_de_mapa_de_riscos_conta_ancoras_de_riscos(self):
        texto = (
            "Matriz de riscos com probabilidade, impacto e ação preventiva para "
            "cada risco identificado."
        )
        ancoras = sysdoc.detectar_ancoras(texto)
        assert ancoras["RISCOS"] > 0
        assert sysdoc.peca_sugerida(ancoras) == "RISCOS"

    def test_empate_de_contagem_devolve_none(self):
        ancoras = {"ETP": 2, "TR": 2, "MCP": 0, "RISCOS": 0, "PROCESSO": 0}
        assert sysdoc.peca_sugerida(ancoras) is None

    def test_texto_vazio_nao_sugere_peca(self):
        ancoras = sysdoc.detectar_ancoras("")
        assert sysdoc.peca_sugerida(ancoras) is None


class TestManifest:
    def test_prepare_grava_ancoras_e_peca_sugerida(self, tmp_path, monkeypatch):
        projeto_dir = tmp_path / "ProjetoAncoras"
        docs = projeto_dir / "documentos"
        docs.mkdir(parents=True)
        (docs / "ETP.txt").write_text(
            "Estudo Técnico Preliminar. Necessidade da contratação descrita.",
            encoding="utf-8",
        )

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.prepare("ProjetoAncoras")
        assert rc == 0

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        item = manifest["files"][0]
        assert "ancoras" in item
        assert "peca_sugerida" in item
        assert item["peca_sugerida"] == "ETP"

    def test_prepare_nao_remove_chaves_existentes_do_manifest(self, tmp_path, monkeypatch):
        projeto_dir = tmp_path / "ProjetoLegado"
        docs = projeto_dir / "documentos"
        docs.mkdir(parents=True)
        (docs / "TR.txt").write_text("Termo de Referência simples.", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        sysdoc.prepare("ProjetoLegado")

        manifest = json.loads(
            (projeto_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        )
        item = manifest["files"][0]
        for chave in ("label", "category", "source", "cache", "sha256", "chars", "words"):
            assert chave in item


class TestMapeamento:
    def test_arquivo_com_peca_sugerida_mapeia_com_origem_ancora(self, tmp_path):
        projeto = tmp_path / "Projeto"
        cache_rel = ".sysdoc/cache/textos/documentos/ETP.txt"
        _escrever_texto_cache(projeto, "ETP.txt", "Estudo Técnico Preliminar")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "ETP",
                    "documentos/ETP.pdf",
                    cache_rel,
                    {"ETP": 4, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                )
            ],
        )

        resultado = mapear_pecas(projeto, exigidas={"ETP"})

        assert resultado["ETP"].peca == "ETP"
        assert resultado["ETP"].origem == "ancora"
        assert resultado["ETP"].score == 4
        assert isinstance(resultado["ETP"], PecaMapeada)

    def test_fallback_por_nome_quando_sem_ancora_vencedora(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_texto_cache(projeto, "TR.txt", "texto sem termos reconhecidos")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "TR",
                    "documentos/TR.pdf",
                    ".sysdoc/cache/textos/documentos/TR.txt",
                    {"ETP": 0, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    None,
                )
            ],
        )

        resultado = mapear_pecas(projeto, exigidas={"TR"})

        assert resultado["TR"].origem == "nome"
        assert resultado["TR"].label == "TR"

    def test_dois_arquivos_com_contagem_igual_levantam_erro(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_texto_cache(projeto, "A.txt", "Estudo Técnico Preliminar A")
        _escrever_texto_cache(projeto, "B.txt", "Estudo Técnico Preliminar B")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "DOC-01_A",
                    "documentos/A.pdf",
                    ".sysdoc/cache/textos/documentos/A.txt",
                    {"ETP": 3, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                ),
                _entrada(
                    "DOC-02_B",
                    "documentos/B.pdf",
                    ".sysdoc/cache/textos/documentos/B.txt",
                    {"ETP": 3, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                ),
            ],
        )

        with pytest.raises(ErroMapeamentoPeca) as exc_info:
            mapear_pecas(projeto, exigidas={"ETP"})

        mensagem = str(exc_info.value)
        assert "DOC-01_A" in mensagem
        assert "DOC-02_B" in mensagem

    def test_peca_nao_exigida_ausente_e_omitida_sem_erro(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_texto_cache(projeto, "ETP.txt", "Estudo Técnico Preliminar")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "ETP",
                    "documentos/ETP.pdf",
                    ".sysdoc/cache/textos/documentos/ETP.txt",
                    {"ETP": 2, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                )
            ],
        )

        resultado = mapear_pecas(projeto, exigidas={"ETP"})

        assert "RISCOS" not in resultado
        assert "ETP" in resultado

    def test_entradas_de_referencias_sao_ignoradas(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "REF-01_modelo",
                    "referencias/modelo.pdf",
                    ".sysdoc/cache/textos/referencias/REF-01_modelo.txt",
                    {"ETP": 9, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                    category="referencias",
                )
            ],
        )

        with pytest.raises(ErroMapeamentoPeca):
            mapear_pecas(projeto, exigidas={"ETP"})

    def test_caminho_de_cache_fora_da_pasta_e_recusado(self, tmp_path):
        projeto = tmp_path / "Projeto"
        (projeto / ".sysdoc" / "cache").mkdir(parents=True)
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "ETP",
                    "documentos/ETP.pdf",
                    "../../fora_do_cache.txt",
                    {"ETP": 2, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                )
            ],
        )

        with pytest.raises(ErroMapeamentoPeca):
            mapear_pecas(projeto, exigidas={"ETP"})


class TestOverride:
    def test_override_vence_deteccao_automatica(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_texto_cache(projeto, "MAPA.txt", "Mapa comparativo de preços")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "DOC-01_mapa",
                    "documentos/mapa.pdf",
                    ".sysdoc/cache/textos/documentos/MAPA.txt",
                    {"ETP": 0, "TR": 0, "MCP": 1, "RISCOS": 0, "PROCESSO": 0},
                    "MCP",
                )
            ],
        )

        resultado = mapear_pecas(projeto, exigidas={"MCP"}, overrides={"mcp": "mapa.pdf"})

        assert resultado["MCP"].origem == "override"
        assert resultado["MCP"].label == "DOC-01_mapa"

    def test_override_invalido_levanta_erro(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_manifest(projeto, [])

        with pytest.raises(ErroMapeamentoPeca) as exc_info:
            mapear_pecas(projeto, exigidas={"MCP"}, overrides={"mcp": "inexistente.pdf"})

        assert "inexistente.pdf" in str(exc_info.value)

    def test_override_via_config_yaml_do_projeto(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_texto_cache(projeto, "RISCOS.txt", "Matriz de riscos e probabilidade")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "DOC-01_riscos",
                    "documentos/riscos_v2.pdf",
                    ".sysdoc/cache/textos/documentos/RISCOS.txt",
                    {"ETP": 0, "TR": 0, "MCP": 0, "RISCOS": 2, "PROCESSO": 0},
                    "RISCOS",
                )
            ],
        )
        (projeto / ".sysdoc").mkdir(parents=True, exist_ok=True)
        (projeto / ".sysdoc" / "config.yaml").write_text(
            yaml.safe_dump({"pecas": {"riscos": "riscos_v2.pdf"}}, allow_unicode=True),
            encoding="utf-8",
        )

        resultado = mapear_pecas(projeto, exigidas={"RISCOS"})

        assert resultado["RISCOS"].origem == "override"


class TestAbort:
    def test_peca_exigida_ausente_levanta_erro_com_remedio(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_manifest(projeto, [])

        with pytest.raises(ErroMapeamentoPeca) as exc_info:
            mapear_pecas(projeto, exigidas={"RISCOS"})

        mensagem = str(exc_info.value)
        assert "pecas:" in mensagem
        assert "RISCOS" in mensagem

    def test_manifest_ausente_levanta_erro(self, tmp_path):
        projeto = tmp_path / "ProjetoSemPrepare"
        projeto.mkdir()

        with pytest.raises(ErroMapeamentoPeca):
            mapear_pecas(projeto, exigidas={"ETP"})

    def test_nunca_devolve_mapeamento_parcial_silencioso(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_texto_cache(projeto, "ETP.txt", "Estudo Técnico Preliminar")
        _escrever_manifest(
            projeto,
            [
                _entrada(
                    "ETP",
                    "documentos/ETP.pdf",
                    ".sysdoc/cache/textos/documentos/ETP.txt",
                    {"ETP": 3, "TR": 0, "MCP": 0, "RISCOS": 0, "PROCESSO": 0},
                    "ETP",
                )
            ],
        )

        with pytest.raises(ErroMapeamentoPeca):
            mapear_pecas(projeto, exigidas={"ETP", "TR", "MCP", "RISCOS"})
