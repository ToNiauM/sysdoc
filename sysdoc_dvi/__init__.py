"""
sysdoc_dvi — motor de análise por checklist (DVI) do SysDoc.

Pacote separado da CLI determinística `sysdoc`. Nenhum comando de `sysdoc`
importa este pacote; a relação é unidirecional: `sysdoc_dvi` pode reusar
`sysdoc.py` como biblioteca, nunca o contrário.
"""

from __future__ import annotations

from sysdoc_dvi.tipos import (
    Aplicabilidade,
    AnalysisAgent,
    ItemChecklist,
    ModeloAlvo,
    OrigemVerificacao,
    Peca,
    ResultadoItem,
    TipoVerificacao,
    UsoModelo,
)

__version__ = "1.5.0"

__all__ = [
    "__version__",
    "Aplicabilidade",
    "AnalysisAgent",
    "ItemChecklist",
    "ModeloAlvo",
    "OrigemVerificacao",
    "Peca",
    "ResultadoItem",
    "TipoVerificacao",
    "UsoModelo",
]
