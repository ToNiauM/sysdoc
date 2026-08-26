"""
Testes do mapeamento de peças (sysdoc_dvi.pecas) — RF3.

TDD RED (Task 2): cobre o comportamento descrito no plano 05-07 antes da
implementação de `mapear_pecas`. Task 3 expande esta suíte.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


class TestMapeamentoPorAncora:
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


class TestAmbiguidade:
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

        resultado = mapear_pecas(
            projeto, exigidas={"MCP"}, overrides={"mcp": "mapa.pdf"}
        )

        assert resultado["MCP"].origem == "override"
        assert resultado["MCP"].label == "DOC-01_mapa"

    def test_override_invalido_levanta_erro(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_manifest(projeto, [])

        with pytest.raises(ErroMapeamentoPeca) as exc_info:
            mapear_pecas(projeto, exigidas={"MCP"}, overrides={"mcp": "inexistente.pdf"})

        assert "inexistente.pdf" in str(exc_info.value)


class TestAbort:
    def test_peca_exigida_ausente_levanta_erro_com_remedio(self, tmp_path):
        projeto = tmp_path / "Projeto"
        _escrever_manifest(projeto, [])

        with pytest.raises(ErroMapeamentoPeca) as exc_info:
            mapear_pecas(projeto, exigidas={"RISCOS"})

        mensagem = str(exc_info.value)
        assert "pecas:" in mensagem
        assert "RISCOS" in mensagem

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


class TestFallbackPorNome:
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
