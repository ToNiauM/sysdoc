"""
Validação de upload (D-08, T-07-05-* — 07-CONTEXT.md / 07-05-PLAN.md).

Isolado de Django forms para poder ser testado em unidade. Toda recusa usa
`ArquivoRecusado`, com mensagem em português voltada ao pregoeiro, sem termo
técnico. Nenhuma escrita em disco acontece antes de `validar_arquivo`
aprovar o conteúdo.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

import sysdoc

# Allowlist única — o mesmo conjunto que `sysdoc.prepare` sabe extrair.
# Nunca redigitar aqui: um formato que a web aceitasse e o `prepare` não
# soubesse ler ficaria preso no processo sem nunca virar texto analisável.
EXTENSOES_PERMITIDAS = frozenset(sysdoc.SUPPORTED_REFERENCE_SUFFIXES)

# Assinatura binária dos dois formatos que não são texto puro.
ASSINATURAS = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
}

_NOME_MAX = 80
_RAZAO_MAX_EXPANSAO_ZIP = 200


class ArquivoRecusado(ValidationError):
    """Recusa de upload, sempre com mensagem em português para o pregoeiro."""


def nome_seguro(nome_original: str) -> str:
    """Deriva um nome de arquivo seguro para gravar em disco.

    Recusa extensão fora da allowlist antes de qualquer outra coisa. O
    resultado nunca contém `/`, `\\` ou `..`, nem começa por ponto — porque
    é montado só a partir do `stem` sanitizado mais a extensão validada,
    nunca a partir do caminho original.
    """
    sufixo = Path(nome_original or "").suffix.lower()
    if sufixo not in EXTENSOES_PERMITIDAS:
        raise ArquivoRecusado(
            f"Tipo de arquivo não aceito ({sufixo or 'sem extensão'}). "
            "Envie PDF, Word (.docx), texto (.txt) ou Markdown (.md)."
        )
    stem = Path(nome_original or "").stem
    base = sysdoc.sanitize_filename(stem)[:_NOME_MAX].strip("._")
    if not base:
        raise ArquivoRecusado("Não foi possível reconhecer o nome do arquivo enviado.")
    return f"{base}{sufixo}"


def _validar_entradas_zip(pacote: zipfile.ZipFile) -> None:
    for item in pacote.infolist():
        nome = item.filename
        if nome.startswith("/") or nome.startswith("\\") or Path(nome).is_absolute():
            raise ArquivoRecusado(
                "O arquivo Word enviado é inválido (entrada de caminho absoluto)."
            )
        if ".." in Path(nome).parts:
            raise ArquivoRecusado(
                "O arquivo Word enviado é inválido (entrada com deslocamento de caminho)."
            )
    if "word/document.xml" not in pacote.namelist():
        raise ArquivoRecusado(
            "O arquivo Word enviado é inválido (documento principal não encontrado)."
        )
    total_comprimido = sum(item.compress_size for item in pacote.infolist()) or 1
    total_descomprimido = sum(item.file_size for item in pacote.infolist())
    if total_descomprimido > total_comprimido * _RAZAO_MAX_EXPANSAO_ZIP:
        raise ArquivoRecusado("O arquivo Word enviado é inválido (conteúdo comprometido).")


def validar_arquivo(arquivo) -> None:
    """Recusa `arquivo` antes que ele toque o disco.

    Ordem: (1) extensão/nome via `nome_seguro`; (2) tamanho contra
    `SYSDOC_WEB_MAX_UPLOAD_MB`; (3) assinatura de conteúdo; (4) para `.docx`,
    integridade do ZIP interno.
    """
    nome_seguro(arquivo.name)

    limite_mb = settings.SYSDOC_WEB_MAX_UPLOAD_MB
    if arquivo.size > limite_mb * 1024 * 1024:
        raise ArquivoRecusado(f"Arquivo maior que o limite permitido ({limite_mb} MB).")

    sufixo = Path(arquivo.name).suffix.lower()
    inicio = arquivo.read(8)
    arquivo.seek(0)

    if sufixo in ASSINATURAS:
        assinatura = ASSINATURAS[sufixo]
        if not inicio.startswith(assinatura):
            raise ArquivoRecusado(
                "O conteúdo do arquivo não corresponde ao tipo esperado para essa extensão."
            )
    else:
        conteudo = arquivo.read(4096)
        arquivo.seek(0)
        try:
            conteudo.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            try:
                conteudo.decode("latin-1", errors="strict")
            except UnicodeDecodeError as exc:
                raise ArquivoRecusado(
                    "O conteúdo do arquivo não parece ser texto legível."
                ) from exc

    if sufixo == ".docx":
        try:
            with zipfile.ZipFile(arquivo) as pacote:
                _validar_entradas_zip(pacote)
        except zipfile.BadZipFile as exc:
            raise ArquivoRecusado(
                "O arquivo Word enviado é inválido (pacote não reconhecível)."
            ) from exc
        finally:
            arquivo.seek(0)


def validar_conjunto(arquivos, maximo: int) -> None:
    """Recusa listas vazias, acima do teto de quantidade, ou com nomes duplicados."""
    if not arquivos:
        raise ArquivoRecusado("Envie ao menos um documento do processo.")
    if len(arquivos) > maximo:
        raise ArquivoRecusado(f"Envie no máximo {maximo} arquivos.")
    nomes_vistos: set[str] = set()
    for arquivo in arquivos:
        nome = nome_seguro(arquivo.name)
        if nome in nomes_vistos:
            raise ArquivoRecusado(
                f"Dois arquivos resultam no mesmo nome depois da padronização: {nome}."
            )
        nomes_vistos.add(nome)


def gravar_em(diretorio: Path, arquivo) -> Path:
    """Grava `arquivo` dentro de `diretorio`, confirmando a contenção do destino."""
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / nome_seguro(arquivo.name)
    if destino.resolve().parent != diretorio.resolve():
        raise ArquivoRecusado("Caminho de gravação do arquivo é inválido.")
    with destino.open("wb") as saida:
        for pedaco in arquivo.chunks():
            saida.write(pedaco)
    return destino
