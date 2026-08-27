"""
Builder determinístico do corpo de apontamentos do Despacho de Verificação
Inicial (DVI — Despacho, não "Documento", conforme correção de
terminologia D-01/D-02 do CONTEXT.md da fase 6).

Recebe o dict já carregado de `dados_consolidados.json` e devolve XML de
parágrafos (`<w:p>`) prontos para injeção raw no placeholder
`{{corpo_apontamentos_xml}}` do template gerado no Plano 01
(`templates/dvi/despacho_*.docx`). Módulo puro e offline: não lê arquivo,
não chama modelo, não importa `sysdoc` nem `sysdoc_dvi` — quem importa
daqui é `sysdoc.py` (Plano 04), evitando import circular.

Regra que este módulo materializa (CONTEXT.md D-03 a D-08): o despacho
"deve conter tão somente o que tem de ser ajustado" — filtra por
classificação, agrupa por peça em ordem canônica (ETP → TR), numera
dinamicamente, resolve referências cruzadas entre apontamentos
equivalentes e nunca lê o campo `para` (redação sugerida da unidade
demandante) — quem aponta a necessidade de correção é o despacho, não
quem redige pela UO.

Segurança (threat model do Plano 02, T-06-02-01/02/04): `_paragrafo` é o
único ponto do módulo que emite texto dentro de `<w:t>`, e todo texto
passa por `xml.sax.saxutils.escape` antes de entrar no XML. `w:pStyle`
nunca recebe valor vindo do JSON — só as constantes `ESTILO_PECA` e
`ESTILO_ALINEA` deste módulo.
"""

from __future__ import annotations

import re
import unicodedata
from xml.sax.saxutils import escape

CLASSIFICACOES_CORPO = ("ajuste_necessário", "risco")
CLASSIFICACAO_PENDENTE = "pendente"

ORDEM_PECAS = ("ETP", "TR")

ROTULOS_PECAS = {
    "ETP": "ESTUDO TÉCNICO PRELIMINAR - ETP",
    "TR": "TERMO DE REFERÊNCIA - TR",
}

TITULO_PENDENCIAS = "PENDÊNCIAS DE DOCUMENTAÇÃO"

SEI_AUSENTE = {"", "não informado", "pendente"}

ESTILO_PECA = "DviPecaTitulo"
ESTILO_ALINEA = "DviAlinea"

TEXTO_SEM_APONTAMENTOS = (
    "Não foram identificados apontamentos que demandem ajuste pela unidade demandante."
)

_ALFABETO = "abcdefghijklmnopqrstuvwxyz"


def _texto(item: dict, *chaves: str) -> str:
    """Devolve a primeira chave presente e não vazia em `item`, já `.strip()`.

    Tolera a variante sem acento das chaves do schema (`seção`/`secao`,
    `classificação`/`classificacao`).
    """
    for chave in chaves:
        valor = item.get(chave)
        if valor is None:
            continue
        texto = str(valor).strip()
        if texto:
            return texto
    return ""


def _letra(indice: int) -> str:
    """Rótulo de alínea em base 26: 0->a, 25->z, 26->aa, 27->ab, ...

    Precisa suportar mais de 26 alíneas porque a seção de pendências pode
    ter 14 ou mais itens.
    """
    if indice < 0:
        raise ValueError("índice de alínea não pode ser negativo")
    n = indice + 1
    letras: list[str] = []
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras.append(_ALFABETO[resto])
    return "".join(reversed(letras))


def _chave_equivalencia(item: dict) -> str:
    """Chave de equivalência de D-07: `parecer` normalizado.

    Usa apenas `parecer`, não `checklist_id` nem `fundamento`. `checklist_id`
    foi descartado porque o achado do planejamento (06-02-PLAN.md) provou
    que dois pares de itens equivalentes têm `checklist_id` diferente entre
    ETP e TR. `fundamento` também foi descartado (desvio documentado em
    06-02-SUMMARY.md): medido contra `processo-teste/dados_consolidados.json`,
    o par ETP-016/TR-002 tem `parecer` idêntico mas `fundamento` que varia
    pelo nome da peça ("...seções do ETP" vs "...seções do TR") — usar
    `fundamento` na chave perderia esse par e violaria o critério de aceite
    de 2 referências cruzadas no dataset real.
    """
    parecer = _texto(item, "parecer")
    normalizado = unicodedata.normalize("NFKC", parecer)
    colapsado = re.sub(r"\s+", " ", normalizado)
    return colapsado.strip().casefold()


def _paragrafo(estilo: str, texto: str) -> str:
    """Emite um `<w:p>` completo com `w:pStyle` nomeado e texto escapado.

    Única função do módulo que emite texto dentro de `<w:t>` — nenhum
    outro ponto concatena texto de JSON dentro de XML.
    """
    return (
        f'<w:p><w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>'
    )


def _cabecalho_peca(numero: int, peca: str, sei: str) -> str:
    """`"{numero}) {rótulo}"`, com sufixo `" (SEI {sei})"` quando informado."""
    cabecalho = f"{numero}) {ROTULOS_PECAS[peca]}"
    sei_normalizado = str(sei).strip()
    if sei_normalizado not in SEI_AUSENTE:
        cabecalho = f"{cabecalho} (SEI {sei_normalizado})"
    return cabecalho


def _prefixo_secao(item: dict) -> str:
    """`"{seção}: "` quando `seção` não é vazia; string vazia caso contrário."""
    secao = _texto(item, "seção", "secao")
    return f"{secao}: " if secao else ""


def _corpo_parecer_fundamento(item: dict) -> str:
    """D-06: `parecer` seguido de `fundamento`, em prosa contínua.

    O campo `para` nunca é lido — a leitura desse campo é proibida neste
    módulo.
    """
    parecer = _texto(item, "parecer")
    fundamento = _texto(item, "fundamento")
    if not fundamento:
        return parecer
    if not parecer:
        return fundamento
    return f"{parecer} {fundamento}"


def _texto_alinea(item: dict) -> str:
    """D-06: prefixo de seção + `parecer` + `fundamento`, sem o campo `para`."""
    return f"{_prefixo_secao(item)}{_corpo_parecer_fundamento(item)}"


def _texto_referencia_cruzada(letra: str, numero_secao: int) -> str:
    """D-07: rótulo resolvido do apontamento equivalente já processado."""
    return (
        f'Vide apontamento constante na alínea "{letra}" do item {numero_secao} '
        "do presente documento."
    )


def montar_apontamentos(dados: dict) -> list[dict]:
    """Filtra, agrupa, numera e resolve o texto dos apontamentos do despacho.

    Duas passadas (D-07 exige numeração resolvida antes do texto):

    - Passada A — seleção e numeração: percorre `ORDEM_PECAS`; para cada
      peça, coleta os itens cujo `documento` é a peça e cuja
      `classificação` está em `CLASSIFICACOES_CORPO` (D-03), preservando
      a ordem de aparição no array `itens` (Claude's Discretion do
      CONTEXT: ordem do documento analisado, não por severidade). Peça
      sem item não gera seção (D-05). Numera as seções sequencialmente a
      partir de 1 e as alíneas com `_letra`.
    - Passada B — texto: se a chave de equivalência de uma alínea já
      apontou, na passada A, para uma alínea anterior, o texto vira
      `_texto_referencia_cruzada`; caso contrário, `_texto_alinea`.
    - Seção de pendências (D-04): depois de todas as seções de peça, se
      houver ao menos um item `pendente`, acrescenta uma seção com o
      próximo número e título `TITULO_PENDENCIAS`, sem referência
      cruzada (pendência de documento ausente não se cruza com
      apontamento de peça).

    Devolve `[{"numero": int, "titulo": str, "alineas": [{"letra": str, "texto": str}]}]`.
    """
    itens = dados.get("itens") or []

    itens_por_peca: dict[str, list[dict]] = {peca: [] for peca in ORDEM_PECAS}
    for item in itens:
        documento = _texto(item, "documento")
        classificacao = _texto(item, "classificação", "classificacao")
        if documento in itens_por_peca and classificacao in CLASSIFICACOES_CORPO:
            itens_por_peca[documento].append(item)

    secoes: list[dict] = []
    primeira_ocorrencia: dict[str, tuple[int, int, str]] = {}
    numero_secao = 0

    for peca in ORDEM_PECAS:
        itens_peca = itens_por_peca[peca]
        if not itens_peca:
            continue
        numero_secao += 1
        secao_dados = dados.get(f"secao_{peca.lower()}") or {}
        sei = _texto(secao_dados, "numero")
        titulo = _cabecalho_peca(numero_secao, peca, sei)
        alineas = []
        for indice, item in enumerate(itens_peca):
            letra = _letra(indice)
            chave = _chave_equivalencia(item)
            if chave not in primeira_ocorrencia:
                primeira_ocorrencia[chave] = (numero_secao, indice, letra)
            alineas.append({"letra": letra, "_indice": indice, "_item": item, "_chave": chave})
        secoes.append({"numero": numero_secao, "titulo": titulo, "alineas": alineas})

    itens_pendentes = [
        item
        for item in itens
        if _texto(item, "classificação", "classificacao") == CLASSIFICACAO_PENDENTE
    ]
    if itens_pendentes:
        numero_secao += 1
        alineas = [
            {"letra": _letra(indice), "_indice": indice, "_item": item, "_chave": None}
            for indice, item in enumerate(itens_pendentes)
        ]
        secoes.append({"numero": numero_secao, "titulo": TITULO_PENDENCIAS, "alineas": alineas})

    for secao in secoes:
        for alinea in secao["alineas"]:
            item = alinea.pop("_item")
            chave = alinea.pop("_chave")
            indice_atual = alinea.pop("_indice")
            texto = None
            if chave is not None:
                origem_secao, origem_indice, origem_letra = primeira_ocorrencia[chave]
                atual = (secao["numero"], indice_atual)
                if (origem_secao, origem_indice) < atual:
                    texto = (
                        f"{_prefixo_secao(item)}"
                        f"{_texto_referencia_cruzada(origem_letra, origem_secao)}"
                    )
            if texto is None:
                texto = _texto_alinea(item)
            alinea["texto"] = texto

    return secoes


def build_corpo_despacho_xml(dados: dict) -> str:
    """Devolve o XML dos apontamentos, pronto para injeção raw no DOCX.

    Se não houver nenhum apontamento (todos `conforme`), devolve um único
    parágrafo com `TEXTO_SEM_APONTAMENTOS` — o placeholder nunca fica
    vazio nem sobra `{{`.
    """
    secoes = montar_apontamentos(dados)
    if not secoes:
        return _paragrafo(ESTILO_ALINEA, TEXTO_SEM_APONTAMENTOS)
    partes: list[str] = []
    for secao in secoes:
        partes.append(_paragrafo(ESTILO_PECA, _titulo_numerado(secao)))
        for alinea in secao["alineas"]:
            partes.append(_paragrafo(ESTILO_ALINEA, f"{alinea['letra']}) {alinea['texto']}"))
    return "".join(partes)


def _titulo_numerado(secao: dict) -> str:
    """Garante `"{numero}) "` no título renderizado de toda seção (D-05).

    `_cabecalho_peca` já embute o número no `titulo` de seções por peça
    (usado por `montar_apontamentos`/testes unitários que comparam o campo
    literalmente). A seção de pendências guarda `TITULO_PENDENCIAS` sem
    número — de propósito, para não acoplar `montar_apontamentos` a uma
    posição de renderização — e só ganha o prefixo aqui, no momento de
    virar parágrafo, espelhando o modelo institucional real
    (`processo-teste/referencias/dvi.md`: `"3) CRONOGRAMA FÍSICO-FINANCEIRO:"`).
    """
    prefixo = f"{secao['numero']}) "
    titulo = secao["titulo"]
    return titulo if titulo.startswith(prefixo) else f"{prefixo}{titulo}"
