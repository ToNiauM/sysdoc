"""
Entrega endurecida dos dois downloads da tela de resultado (D-13 —
07-CONTEXT.md; T-07-07-02/05 do threat model do `07-07-PLAN.md`).

O HTML da análise nunca é servido para renderização dentro da origem
autenticada da aplicação: mesmo sendo produzido pelo renderizador
determinístico e imutável (`templates/render_analise.py`), seu texto deriva
de um modelo de linguagem — conteúdo não confiável não pode ficar embutido
na própria origem. Por isso todo download aqui é sempre `attachment`, com
cabeçalhos que impedem o navegador de tentar executar o conteúdo como parte
do site.
"""

from __future__ import annotations

from pathlib import Path

from django.core.exceptions import SuspiciousOperation
from django.http import FileResponse, Http404
from django.utils.http import content_disposition_header

import sysdoc


def entregar(
    caminho: Path, raiz_permitida: Path, nome_para_usuario: str, tipo_conteudo: str
) -> FileResponse:
    """Serve `caminho` como anexo, contido em `raiz_permitida`.

    Recusa com `SuspiciousOperation` caminho fora da pasta do processo
    (path traversal — o nome do arquivo servido vem de dados) e com
    `Http404` arquivo inexistente. `nome_para_usuario` passa pelo mesmo
    saneamento de nome de arquivo usado no upload, preservando a extensão.
    """
    caminho_resolvido = Path(caminho).resolve()
    raiz_resolvida = Path(raiz_permitida).resolve()
    if not caminho_resolvido.is_relative_to(raiz_resolvida):
        raise SuspiciousOperation(
            f"Caminho de download fora da pasta do processo: {caminho_resolvido}"
        )
    if not caminho_resolvido.is_file():
        raise Http404("Arquivo não encontrado.")

    sufixo = Path(nome_para_usuario).suffix
    stem = Path(nome_para_usuario).stem
    nome_seguro = f"{sysdoc.sanitize_filename(stem)}{sufixo}"

    resposta = FileResponse(caminho_resolvido.open("rb"), content_type=tipo_conteudo)
    resposta["Content-Disposition"] = content_disposition_header(True, nome_seguro)
    resposta["X-Content-Type-Options"] = "nosniff"
    resposta["Content-Security-Policy"] = "sandbox"
    resposta["Referrer-Policy"] = "no-referrer"
    resposta["Cache-Control"] = "private, no-store"
    return resposta
