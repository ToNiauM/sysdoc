"""
Trava de regressão para a expansão da sigla DVI (Plano 06-03).

DVI significa **Despacho de Verificação Inicial** (D-01 de 06-CONTEXT.md),
confirmado pelo modelo institucional real em `processo-teste/referencias/dvi.md`.
Duas expansões erradas já circularam pelo repositório: "Diligência de
Verificação de Instrução" (corrigida na release 1.5.x) e "Documento de
Verificação Inicial" (corrigida no Plano 06-03). Este módulo varre todo
arquivo versionado e falha, nomeando arquivo e linha, se qualquer uma delas
reaparecer.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_SUFIXOS_VARRIDOS = {".md", ".py", ".yaml", ".yml", ".txt"}
_PREFIXOS_EXCLUIDOS = (".planning/",)
_ARQUIVOS_EXCLUIDOS = {"CHANGELOG.md", "tests/test_sigla_dvi.py"}

_EXPANSOES_ERRADAS = (
    "Documento de Verificação Inicial",
    "DOCUMENTO DE VERIFICAÇÃO INICIAL",
    "Diligência de Verificação de Instrução",
)

_EXPANSAO_CORRETA = "Despacho de Verificação Inicial"


def _arquivos_versionados() -> list[Path]:
    try:
        resultado = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pytest.skip("git ls-files indisponível — repositório não inicializado.", allow_module_level=True)
        return []

    arquivos = []
    for linha in resultado.stdout.splitlines():
        rel = linha.strip()
        if not rel:
            continue
        if any(rel.startswith(prefixo) for prefixo in _PREFIXOS_EXCLUIDOS):
            continue
        if rel in _ARQUIVOS_EXCLUIDOS:
            continue
        caminho = Path(rel)
        if caminho.suffix not in _SUFIXOS_VARRIDOS:
            continue
        caminho_absoluto = ROOT / rel
        if caminho_absoluto.is_file():
            arquivos.append(caminho_absoluto)
    return arquivos


_ARQUIVOS_VERSIONADOS = _arquivos_versionados()


class TestExpansaoDaSigla:
    def test_nenhuma_ocorrencia_da_expansao_errada(self):
        ocorrencias = []
        for arquivo in _ARQUIVOS_VERSIONADOS:
            try:
                texto = arquivo.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for numero, linha in enumerate(texto.splitlines(), start=1):
                for expansao_errada in _EXPANSOES_ERRADAS:
                    if expansao_errada in linha:
                        rel = arquivo.relative_to(ROOT)
                        ocorrencias.append(f"{rel}:{numero}: '{expansao_errada}' -> {linha.strip()!r}")

        assert not ocorrencias, "Expansão errada de DVI encontrada:\n" + "\n".join(ocorrencias)

    def test_expansao_correta_presente_nos_documentos_canonicos(self):
        documentos_canonicos = (
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / "checklists" / "dvi.yaml",
            ROOT / "skills" / "sysdoc" / "SKILL.md",
        )
        for documento in documentos_canonicos:
            texto = documento.read_text(encoding="utf-8")
            assert _EXPANSAO_CORRETA in texto, (
                f"{documento.relative_to(ROOT)} deveria conter '{_EXPANSAO_CORRETA}'"
            )

    def test_docx_base_usa_a_expansao_correta(self):
        docx_base = ROOT / "templates" / "dvi_base.docx"
        if not docx_base.exists():
            pytest.skip("templates/dvi_base.docx aposentado.")
        with zipfile.ZipFile(docx_base) as pacote:
            xml = pacote.read("word/document.xml").decode("utf-8")
        assert "DESPACHO DE VERIFICAÇÃO INICIAL" in xml
        assert "DOCUMENTO DE VERIFICAÇÃO" not in xml

    def test_modelo_institucional_confirma_a_grafia(self):
        modelo = ROOT / "processo-teste" / "referencias" / "dvi.md"
        if not modelo.exists():
            pytest.skip("processo-teste/ não presente neste ambiente.")
        primeira_linha = modelo.read_text(encoding="utf-8").splitlines()[0]
        assert "DESPACHO DE VERIFICAÇÃO INICIAL" in primeira_linha
