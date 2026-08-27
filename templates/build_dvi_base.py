"""
Gerador determinístico de `templates/dvi_base.docx` (P6 - 260826-o2d).

Roda sob demanda (`python3 templates/build_dvi_base.py`) e escreve o DOCX
mínimo semeado por `sysdoc init` em `referencias/dvi.docx`, para que
`sysdoc create <pasta> dvi` funcione sem template institucional manual.

Cada parágrafo é um único `<w:r><w:t xml:space="preserve">...</w:t></w:r>`,
de modo que nenhum placeholder `{{...}}` fique partido entre runs XML. As
entradas do ZIP usam data fixa (`ZipInfo.date_time`) para que a regeração
seja byte-estável.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "templates" / "dvi_base.docx"

_DATA_FIXA = (2026, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_RELS_RAIZ = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
    'Target="word/document.xml"/>'
    "</Relationships>"
)

_RELS_DOCUMENTO = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
)

_PARAGRAFOS = [
    "DESPACHO DE VERIFICAÇÃO INICIAL — DVI",
    "{{titulo}}",
    "{{subtitulo}}",
    "Data da análise: {{data_análise}} — Modelo de IA: {{modelo_ia}}",
    "1. PARECER EXECUTIVO",
    "{{parecer_executivo}}",
    "2. ANÁLISE DO ESTUDO TÉCNICO PRELIMINAR (ETP)",
    "{{secao_etp.parecer_documento}}",
    "3. ANÁLISE DO TERMO DE REFERÊNCIA (TR)",
    "{{secao_tr.parecer_documento}}",
    "4. ITENS VERIFICADOS",
    "Total de itens: {{total_itens}} — Bloqueantes: {{total_bloqueantes}} — Pendentes: {{total_pendentes}}",
    "{{tabela_itens}}",
    "5. NOTA DE INTEGRIDADE",
    "{{nota_integridade}}",
]


def _paragrafo_xml(texto: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>'


def _documento_xml() -> str:
    corpo = "".join(_paragrafo_xml(paragrafo) for paragrafo in _PARAGRAFOS)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{corpo}</w:body>"
        "</w:document>"
    )


def construir(destino: Path = DESTINO) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    entradas = {
        "[Content_Types].xml": _CONTENT_TYPES,
        "_rels/.rels": _RELS_RAIZ,
        "word/document.xml": _documento_xml(),
        "word/_rels/document.xml.rels": _RELS_DOCUMENTO,
    }
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome in sorted(entradas):
            info = zipfile.ZipInfo(nome, date_time=_DATA_FIXA)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, entradas[nome])
    return destino


if __name__ == "__main__":
    caminho = construir()
    print(f"Template DVI base gerado: {caminho}")
