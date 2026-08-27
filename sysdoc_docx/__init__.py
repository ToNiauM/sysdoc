"""
Pacote de geração DOCX determinística do SysDoc (despacho, TR, ETP).

Módulos aqui dentro são puros e offline: recebem `dict` já carregado de
`dados_consolidados.json`, nunca leem arquivo, nunca chamam modelo e nunca
importam `sysdoc` ou `sysdoc_dvi` (para não criar import circular — quem
importa deste pacote é `sysdoc.py`).
"""

from __future__ import annotations
