"""
Tabela curada de vigência de normativos e verificação determinística do
tipo `vigencia` (RF4, RF7; D-10..D-13 de 05-CONTEXT.md).

Vigência de normativo é respondida exclusivamente pela tabela curada em
`normas/vigencia.yaml` (com override opcional por projeto), nunca por
consulta a modelo de linguagem. Norma citada e ausente da tabela vira item
`pendente` com a mensagem "norma não catalogada". Apenas `status: vigente`
produz `conforme`; entradas com status `suspensa` ou
`pendente_de_conferencia` degradam para `pendente` com mensagem honesta
pedindo conferência manual — a verificação nunca certifica o que a tabela
não afirma.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from sysdoc_dvi.tipos import ItemChecklist, ResultadoItem

STATUS_VALIDOS = {
    "vigente",
    "revogada",
    "substituida",
    "suspensa",
    "pendente_de_conferencia",
}

_CAMPOS_OBRIGATORIOS = ("norma", "status", "conferida_em")

_MESES = (
    "janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro"
    "|outubro|novembro|dezembro"
)

_DATA_EXTENSA_PATTERN = re.compile(
    rf"\bde\s+\d{{1,2}}[ºo°]?\s+de\s+(?:{_MESES})\s+de\s+(\d{{4}})\b"
)
_N_PREFIXO_PATTERN = re.compile(r"\bn(?:[º°o]\.?|\.)")
_MILHAR_PATTERN = re.compile(r"(?<=\d)\.(?=\d{3}\b)")
_DE_ISOLADO_PATTERN = re.compile(r"\bde\b")
_NAO_PALAVRA_PATTERN = re.compile(r"[^\w\s]", flags=re.UNICODE)
_ESPACOS_PATTERN = re.compile(r"\s+")

_PALAVRAS_CITACAO = (
    r"Lei|Decreto|Instru[cç][aã]o Normativa|IN|Portaria|Resolu[cç][aã]o|Ac[oó]rd[aã]o"
)
_CITACAO_PATTERN = re.compile(
    rf"\b(?:{_PALAVRAS_CITACAO})\b[^\n]{{0,120}}?\d{{4}}\b(?:[-–][^\s,.;]{{1,30}})?",
    flags=re.IGNORECASE,
)


class ErroVigencia(Exception):
    """Erro estrutural na tabela de vigência de normativos."""


def _ler_entradas(path: str | Path) -> list[dict]:
    resolved = Path(path)
    if not resolved.is_file():
        return []
    with resolved.open("r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh)
    if not dados:
        return []
    if not isinstance(dados, dict) or not isinstance(dados.get("normas"), list):
        raise ErroVigencia(
            f"{resolved}: tabela de vigência inválida, esperado mapeamento com chave 'normas'"
        )
    return dados["normas"]


def _validar_entrada(entrada: dict, indice: int, origem_path: str) -> None:
    if not isinstance(entrada, dict):
        raise ErroVigencia(f"{origem_path} entrada[{indice}]: deve ser um mapeamento")
    for campo in _CAMPOS_OBRIGATORIOS:
        if not entrada.get(campo):
            raise ErroVigencia(
                f"{origem_path} entrada[{indice}]: campo obrigatório ausente: '{campo}'"
            )
    status = entrada["status"]
    if status not in STATUS_VALIDOS:
        raise ErroVigencia(f"{origem_path} entrada[{indice}]: status inválido: '{status}'")
    if status == "substituida" and not entrada.get("substituida_por"):
        raise ErroVigencia(
            f"{origem_path} entrada[{indice}]: status 'substituida' exige 'substituida_por'"
        )


def carregar_vigencia(
    global_path: str | Path, projeto_path: str | Path | None = None
) -> dict[str, dict]:
    tabela: dict[str, dict] = {}

    def _indexar(entradas: list[dict], origem: str, origem_path: str) -> None:
        for indice, entrada in enumerate(entradas):
            _validar_entrada(entrada, indice, origem_path)
            registro = dict(entrada)
            registro["origem"] = origem
            chaves = [registro["norma"], *(registro.get("aliases") or [])]
            for chave in chaves:
                tabela[normalizar_citacao(chave)] = registro

    globais = _ler_entradas(global_path)
    _indexar(globais, "global", str(global_path))

    if projeto_path is not None:
        entradas_projeto = _ler_entradas(projeto_path)
        _indexar(entradas_projeto, "projeto", str(projeto_path))

    return tabela


def normalizar_citacao(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto or ""))
    normalizado = "".join(char for char in normalizado if not unicodedata.combining(char))
    normalizado = normalizado.lower()
    normalizado = _DATA_EXTENSA_PATTERN.sub(r" \1", normalizado)
    normalizado = _N_PREFIXO_PATTERN.sub(" ", normalizado)
    normalizado = normalizado.replace("º", "").replace("°", "")
    normalizado = _MILHAR_PATTERN.sub("", normalizado)
    normalizado = normalizado.replace("/", " ")
    normalizado = _DE_ISOLADO_PATTERN.sub(" ", normalizado)
    normalizado = _NAO_PALAVRA_PATTERN.sub(" ", normalizado)
    normalizado = _ESPACOS_PATTERN.sub(" ", normalizado).strip()
    return normalizado


def consultar_norma(tabela: dict[str, dict], citacao: str) -> dict | None:
    return tabela.get(normalizar_citacao(citacao))


def _parse_conferida_em(valor) -> date:
    if isinstance(valor, date):
        return valor
    return datetime.strptime(str(valor), "%Y-%m-%d").date()


def normas_desatualizadas(
    tabela: dict[str, dict], limiar_dias: int = 180, hoje: date | None = None
) -> list[str]:
    referencia = hoje or date.today()
    limite = referencia - timedelta(days=limiar_dias)
    vistas: set[str] = set()
    resultado: list[str] = []
    for entrada in tabela.values():
        nome = entrada["norma"]
        if nome in vistas:
            continue
        vistas.add(nome)
        if _parse_conferida_em(entrada["conferida_em"]) < limite:
            resultado.append(nome)
    return resultado


def _extrair_citacoes(texto: str) -> list[str]:
    return [match.group(0).strip() for match in _CITACAO_PATTERN.finditer(texto or "")]


def verificar_item_vigencia(
    item: ItemChecklist, texto_peca: str, tabela: dict[str, dict]
) -> ResultadoItem:
    documento = item.documento_saida
    seção = item.peca
    severidade = item.severidade_default

    citacoes = _extrair_citacoes(texto_peca)

    if not citacoes:
        return ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="lookup",
            documento=documento,
            seção=seção,
            de="[OMISSÃO]",
            para="[OMISSÃO]",
            parecer=(
                "Nenhum normativo foi citado no texto analisado; "
                "não há vigência a conferir."
            ),
            fundamento=f"Busca determinística por citações de normativos em {documento}",
            classificação="pendente",
            severidade=severidade,
            risco_jurídico="informativo",
        )

    resolucoes = [(citacao, consultar_norma(tabela, citacao)) for citacao in citacoes]

    for citacao, entrada in resolucoes:
        if entrada is not None and entrada["status"] in {"revogada", "substituida"}:
            substituida_por = entrada.get("substituida_por")
            parecer = (
                f"A citação '{citacao}' refere-se a norma com status '{entrada['status']}'."
            )
            if substituida_por:
                parecer += f" Foi substituída por {substituida_por}."
            return ResultadoItem(
                checklist_id=item.id,
                origem_verificacao="lookup",
                documento=documento,
                seção=seção,
                de=citacao,
                para=substituida_por or citacao,
                parecer=parecer,
                fundamento=(
                    f"Tabela curada de vigência (origem={entrada['origem']}), "
                    f"status={entrada['status']}, conferida_em={entrada['conferida_em']}"
                ),
                classificação="risco",
                severidade=severidade,
                risco_jurídico="relevante",
            )

    for citacao, entrada in resolucoes:
        if entrada is not None and entrada["status"] == "suspensa":
            return ResultadoItem(
                checklist_id=item.id,
                origem_verificacao="lookup",
                documento=documento,
                seção=seção,
                de=citacao,
                para=citacao,
                parecer=(
                    f"A citação '{citacao}' refere-se a norma com status 'suspensa' na "
                    "tabela curada; confirmar manualmente a vigência antes de fundamentar "
                    "qualquer conclusão nesta norma."
                ),
                fundamento=(
                    f"Tabela curada de vigência (origem={entrada['origem']}), "
                    f"status={entrada['status']}, conferida_em={entrada['conferida_em']}"
                ),
                classificação="pendente",
                severidade=severidade,
                risco_jurídico="informativo",
            )

    for citacao, entrada in resolucoes:
        if entrada is None:
            return ResultadoItem(
                checklist_id=item.id,
                origem_verificacao="lookup",
                documento=documento,
                seção=seção,
                de=citacao,
                para=citacao,
                parecer=(
                    f"A citação '{citacao}' corresponde a norma não catalogada "
                    "na tabela de vigência."
                ),
                fundamento="A tabela curada de vigência de normativos não contém entrada correspondente a esta citação",
                classificação="pendente",
                severidade=severidade,
                risco_jurídico="informativo",
            )

    for citacao, entrada in resolucoes:
        if entrada is not None and entrada["status"] == "pendente_de_conferencia":
            return ResultadoItem(
                checklist_id=item.id,
                origem_verificacao="lookup",
                documento=documento,
                seção=seção,
                de=citacao,
                para=citacao,
                parecer=(
                    f"A citação '{citacao}' refere-se a norma ainda não conferida pela "
                    "curadoria humana (status 'pendente_de_conferencia'); confirmar a "
                    "vigência manualmente."
                ),
                fundamento=(
                    f"Tabela curada de vigência (origem={entrada['origem']}), "
                    f"status={entrada['status']}, conferida_em={entrada['conferida_em']}"
                ),
                classificação="pendente",
                severidade=severidade,
                risco_jurídico="informativo",
            )

    citacao, entrada = resolucoes[0]
    if entrada["status"] != "vigente":
        return ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="lookup",
            documento=documento,
            seção=seção,
            de=citacao,
            para=citacao,
            parecer=(
                f"A citação '{citacao}' refere-se a norma com status "
                f"'{entrada['status']}' não conferido; confirmar a vigência manualmente."
            ),
            fundamento=(
                f"Tabela curada de vigência (origem={entrada['origem']}), "
                f"status={entrada['status']}, conferida_em={entrada['conferida_em']}"
            ),
            classificação="pendente",
            severidade=severidade,
            risco_jurídico="informativo",
        )
    return ResultadoItem(
        checklist_id=item.id,
        origem_verificacao="lookup",
        documento=documento,
        seção=seção,
        de=citacao,
        para=citacao,
        parecer=f"A citação '{citacao}' refere-se a norma vigente conforme tabela curada.",
        fundamento=(
            f"Tabela curada de vigência (origem={entrada['origem']}), "
            f"status={entrada['status']}, conferida_em={entrada['conferida_em']}"
        ),
        classificação="conforme",
        severidade=severidade,
        risco_jurídico="informativo",
    )
