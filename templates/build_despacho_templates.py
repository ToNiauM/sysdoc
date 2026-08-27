"""
Gerador determinístico das duas variantes do Despacho de Verificação Inicial
(DVI) em `templates/dvi/` (P6 - 260827-p66, rodada 1).

Roda sob demanda (`python3 templates/build_despacho_templates.py`) e escreve
`templates/dvi/despacho_geral.docx` e `templates/dvi/despacho_tic.docx`,
fiéis à moldura do modelo institucional real
(`processo-teste/referencias/dvi.md`): título, processo SEI, vocativo,
contextualização, corpo dos apontamentos, "Observações:", assinatura e o
"De acordo" da autoridade.

Cada parágrafo de campo fixo é um único `<w:r><w:t xml:space="preserve">`,
de modo que nenhum placeholder `{{...}}` fique partido entre runs XML. As
entradas do ZIP usam data fixa (`ZipInfo.date_time`) para que a regeração
seja byte-estável (D-10 de 06-CONTEXT.md).

Regra do placeholder raw (D-08): um placeholder terminado em `_xml` — aqui,
`{{corpo_apontamentos_xml}}` — deve ser o único conteúdo textual do seu
`<w:p>`, porque o parágrafo hospedeiro inteiro é trocado na renderização
pelo builder do Plano 04. Nenhum outro texto pode compartilhar esse
parágrafo.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DESTINO_DIR = ROOT / "templates" / "dvi"

_DATA_FIXA = (2026, 1, 1, 0, 0, 0)

VARIANTES = ("geral", "tic")

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
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
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" "
    'Target="styles.xml"/>'
    "</Relationships>"
)

_ESTILOS = ("DviTitulo", "DviSubtitulo", "DviVocativo", "DviCorpo", "DviPecaTitulo", "DviAlinea")

_ESTILOS_NEGRITO = {"DviTitulo", "DviPecaTitulo"}


def _estilo_xml(style_id: str) -> str:
    propriedades = ""
    if style_id in _ESTILOS_NEGRITO:
        propriedades += "<w:rPr><w:b/></w:rPr>"
    if style_id == "DviAlinea":
        propriedades = '<w:pPr><w:ind w:left="567"/></w:pPr>' + propriedades
    return (
        f'<w:style w:type="paragraph" w:styleId="{style_id}">'
        f'<w:name w:val="{style_id}"/>'
        f"{propriedades}"
        "</w:style>"
    )


def _styles_xml() -> str:
    corpo = "".join(_estilo_xml(style_id) for style_id in _ESTILOS)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"{corpo}"
        "</w:styles>"
    )


_OBSERVACAO_1 = (
    "A presente verificação não abordou as particularidades da execução do serviço, "
    "as quais são de responsabilidade da equipe de planejamento."
)

_OBSERVACAO_3 = (
    "Visando preservar o histórico do processo, nenhum documento que foi submetido a "
    "análise deverá ser cancelado pela unidade demandante, no caso de eventual reedição "
    "de novo documento que venha a substituí-lo."
)

_OBSERVACAO_2_GERAL = (
    "No que tange ao ETP, a análise realizada limitou-se à verificação da presença dos "
    "elementos e requisitos exigidos pela Instrução Normativa aplicável, não abrangendo "
    "o exame do mérito técnico, do conteúdo ou das soluções adotadas."
)

_OBSERVACAO_2_TIC = (
    "No que tange ao ETP, a análise realizada limitou-se à verificação da presença dos "
    "elementos e requisitos exigidos pela Instrução Normativa SGD/ME nº 94, de 23 de "
    "dezembro de 2022, não abrangendo o exame do mérito técnico, do conteúdo ou das "
    "soluções adotadas."
)

_OBSERVACOES = {
    "geral": (_OBSERVACAO_1, _OBSERVACAO_2_GERAL, _OBSERVACAO_3),
    "tic": (_OBSERVACAO_1, _OBSERVACAO_2_TIC, _OBSERVACAO_3),
}


def _moldura(variante: str) -> list[tuple[str, str]]:
    observacao_1, observacao_2, observacao_3 = _OBSERVACOES[variante]
    return [
        ("DviTitulo", "DESPACHO DE VERIFICAÇÃO INICIAL - dvi"),
        ("DviSubtitulo", "Processo SEI n.º {{projeto.processo}}"),
        ("DviVocativo", "{{despacho.vocativo}}"),
        ("DviCorpo", "Trata o presente processo de {{projeto.objeto}}"),
        (
            "DviCorpo",
            "O processo foi protocolado no {{despacho.unidade}} e após triagem inicial de "
            "sua composição, faço as seguintes considerações:",
        ),
        ("DviCorpo", "{{corpo_apontamentos_xml}}"),
        ("DviCorpo", "Observações:"),
        ("DviCorpo", observacao_1),
        ("DviCorpo", observacao_2),
        ("DviCorpo", observacao_3),
        ("DviCorpo", "{{despacho.signatario}}"),
        ("DviCorpo", "{{despacho.cargo_signatario}}"),
        ("DviCorpo", "De acordo,"),
        ("DviCorpo", "{{despacho.destinatario}}"),
        ("DviCorpo", "{{despacho.autoridade}}"),
        ("DviCorpo", "{{despacho.cargo_autoridade}}"),
    ]


def _paragrafo_xml(estilo: str, texto: str) -> str:
    return (
        "<w:p>"
        f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{escape(texto)}</w:t></w:r>'
        "</w:p>"
    )


def _documento_xml(variante: str) -> str:
    corpo = "".join(_paragrafo_xml(estilo, texto) for estilo, texto in _moldura(variante))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{corpo}</w:body>"
        "</w:document>"
    )


def construir(variante: str, destino: Path | None = None) -> Path:
    if variante not in VARIANTES:
        raise ValueError(f"variante desconhecida: {variante!r} (esperado {VARIANTES})")

    if destino is None:
        destino = DESTINO_DIR / f"despacho_{variante}.docx"

    destino.parent.mkdir(parents=True, exist_ok=True)
    entradas = {
        "[Content_Types].xml": _CONTENT_TYPES,
        "_rels/.rels": _RELS_RAIZ,
        "word/document.xml": _documento_xml(variante),
        "word/_rels/document.xml.rels": _RELS_DOCUMENTO,
        "word/styles.xml": _styles_xml(),
    }
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome in sorted(entradas):
            info = zipfile.ZipInfo(nome, date_time=_DATA_FIXA)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, entradas[nome])
    return destino


def construir_todas(destino_dir: Path | None = None) -> list[Path]:
    base = destino_dir if destino_dir is not None else DESTINO_DIR
    return [construir(variante, base / f"despacho_{variante}.docx") for variante in VARIANTES]


if __name__ == "__main__":
    for caminho in construir_todas():
        print(f"Template de despacho gerado: {caminho}")
