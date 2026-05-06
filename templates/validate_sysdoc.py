#!/usr/bin/env python3
"""
Validador determinístico do JSON consolidado SysDoc.

Uso:
    python templates/validate_sysdoc.py Projeto/dados_consolidados.json
"""

import json
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_TOP = [
    "titulo",
    "subtitulo",
    "modelo_ia",
    "data_análise",
    "projeto",
    "metadados",
    "documentos_analisados",
    "parecer_executivo",
    "secao_etp",
    "secao_tr",
    "itens",
    "nota_integridade",
]

REQUIRED_PROJETO = ["órgão", "processo", "valor_estimado", "objeto"]

REQUIRED_SECAO = ["classificação_documento", "parecer_documento", "numero"]

REQUIRED_ITEM = [
    "id",
    "número",
    "item",
    "documento",
    "seção",
    "de",
    "para",
    "parecer",
    "fundamento",
    "classificação",
    "severidade",
    "risco_jurídico",
    "status_delic",
    "alterado_pelo_jurídico",
]

ENUMS = {
    "documento": {"ETP", "TR"},
    "classificação": {"conforme", "ajuste_necessário", "risco", "pendente"},
    "severidade": {"crítica", "alta", "média", "baixa", "informativa"},
    "risco_jurídico": {"bloqueante", "relevante", "menor", "informativo"},
    "status_delic": {"confirmado", "novo", "divergente", None},
    "classificação_documento": {
        "aprovado",
        "aprovado_com_ressalvas",
        "reprovado",
        "pendente_de_complementação",
    },
}

PLACEHOLDER_PATTERNS = [
    r"<[^>]+>",
    r"\.\.\.",
    r"\[texto\]",
    r"\[inserir",
    r"\[preencher",
    r"\[número",
    r"\[numero",
]

GENERIC_MODELS = {"ia", "modelo", "default", "llm", "ai", "gpt", "claude", "gemini"}

PT_BR_ACCENT_TERMS = {
    "analise": "análise",
    "tecnico": "técnico",
    "tecnica": "técnica",
    "juridico": "jurídico",
    "juridica": "jurídica",
    "aquisicao": "aquisição",
    "contratacao": "contratação",
    "licitacao": "licitação",
    "combustivel": "combustível",
    "combustiveis": "combustíveis",
    "orgao": "órgão",
    "orgaos": "órgãos",
    "referencia": "referência",
    "referencias": "referências",
    "execucao": "execução",
    "fiscalizacao": "fiscalização",
    "gestao": "gestão",
    "habilitacao": "habilitação",
    "sancao": "sanção",
    "sancoes": "sanções",
    "medicao": "medição",
    "subcontratacao": "subcontratação",
    "necessario": "necessário",
    "necessaria": "necessária",
    "possivel": "possível",
    "apos": "após",
    "nao": "não",
    "tambem": "também",
    "alem": "além",
    "ate": "até",
    "atraves": "através",
    "havera": "haverá",
    "podera": "poderá",
    "devera": "deverá",
    "mantem": "mantém",
    "deverao": "deverão",
    "poderao": "poderão",
    "serao": "serão",
    "criterio": "critério",
    "criterios": "critérios",
    "numero": "número",
    "administracao": "administração",
    "publica": "pública",
    "pratica": "prática",
    "praticas": "práticas",
    "contraditorio": "contraditório",
    "contradicao": "contradição",
    "contradicoes": "contradições",
    "operacionalizacao": "operacionalização",
    "liquidacao": "liquidação",
    "vigencia": "vigência",
    "versao": "versão",
    "economica": "econômica",
    "economico": "econômico",
    "orcamentaria": "orçamentária",
    "orcamentario": "orçamentário",
    "precos": "preços",
    "preco": "preço",
    "razao": "razão",
    "razoes": "razões",
    "relacao": "relação",
    "verificacao": "verificação",
    "continua": "contínua",
    "continuo": "contínuo",
    "periodo": "período",
    "brasilia": "Brasília",
    "memoria": "memória",
    "veiculo": "veículo",
    "veiculos": "veículos",
    "aplicacao": "aplicação",
    "medio": "médio",
    "media": "média",
    "infracao": "infração",
    "infracoes": "infrações",
    "indicacao": "indicação",
    "localizacao": "localização",
    "impugnacao": "impugnação",
    "aplicavel": "aplicável",
    "aplicaveis": "aplicáveis",
    "juridicas": "jurídicas",
    "tecnicas": "técnicas",
    "conclusao": "conclusão",
    "manutencao": "manutenção",
    "regencia": "regência",
    "instrucao": "instrução",
    "servico": "serviço",
    "servicos": "serviços",
    "dedicacao": "dedicação",
    "restricao": "restrição",
    "restricoes": "restrições",
    "maximo": "máximo",
    "redacao": "redação",
    "logistica": "logística",
    "ausencia": "ausência",
    "inconsistencia": "inconsistência",
    "prorrogacao": "prorrogação",
    "uteis": "úteis",
    "presenca": "presença",
    "proprio": "próprio",
    "participacao": "participação",
    "discussao": "discussão",
    "selecao": "seleção",
    "previsao": "previsão",
    "vinculo": "vínculo",
    "motivacao": "motivação",
    "prorrogavel": "prorrogável",
    "correcao": "correção",
    "compatibilizacao": "compatibilização",
    "clausula": "cláusula",
    "clausulas": "cláusulas",
    "vicio": "vício",
    "coerencia": "coerência",
    "seguranca": "segurança",
    "sao": "são",
    "estao": "estão",
    "reducao": "redução",
    "duvida": "dúvida",
    "eletronica": "eletrônica",
    "documentacao": "documentação",
    "adequacao": "adequação",
    "vinculacao": "vinculação",
    "orientacao": "orientação",
    "revisao": "revisão",
    "formatacao": "formatação",
    "sancionatoria": "sancionatória",
    "finalizacao": "finalização",
    "inadequacao": "inadequação",
    "vedacao": "vedação",
    "correcoes": "correções",
    "inseguranca": "insegurança",
    "minimo": "mínimo",
    "minimos": "mínimos",
    "observancia": "observância",
    "emissao": "emissão",
    "operacao": "operação",
    "compativel": "compatível",
    "regiao": "região",
    "horario": "horário",
    "quilometro": "quilômetro",
    "quilometros": "quilômetros",
    "preservacao": "preservação",
    "expressao": "expressão",
    "verificavel": "verificável",
    "inclusao": "inclusão",
    "funcao": "função",
    "obrigacao": "obrigação",
    "conteudo": "conteúdo",
    "responsabilizacao": "responsabilização",
}

TRACE_STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "um", "uma", "para", "por", "com", "sem", "que", "se", "ao", "aos", "as", "os",
}


def word_count(text):
    return len(re.findall(r"\b\w+\b", str(text or ""), flags=re.UNICODE))


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def add_missing(errors, obj, keys, prefix):
    for key in keys:
        if key not in obj:
            errors.append(f"{prefix}: campo ausente `{key}`")
        elif is_blank(obj[key]) and key not in {"status_delic"}:
            errors.append(f"{prefix}: campo vazio `{key}`")


def has_placeholder(text):
    value = str(text or "").lower()
    return any(re.search(pattern, value) for pattern in PLACEHOLDER_PATTERNS)


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(char for char in normalized if not unicodedata.combining(char))


def validate_modelo_ia(errors, data):
    modelo = str(data.get("modelo_ia") or "").strip()
    if not modelo:
        return
    if modelo.lower() in GENERIC_MODELS:
        errors.append("raiz: modelo_ia deve ser o identificador real do modelo, não um valor genérico")
    if modelo != modelo.lower() or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", modelo):
        errors.append("raiz: modelo_ia deve estar em slug minúsculo, com letras, números, pontos, hífens ou underscores")


def validate_portuguese_accents(errors, value, label):
    text = str(value or "")
    for plain, accented in PT_BR_ACCENT_TERMS.items():
        match = re.search(rf"\b{re.escape(plain)}\b", text, flags=re.IGNORECASE)
        if match:
            errors.append(f"{label}: termo sem acentuação `{match.group(0)}`; use `{accented}`")


def trace_tokens(text):
    normalized = strip_accents(text).lower()
    tokens = re.findall(r"\b[\w]+\b", normalized, flags=re.UNICODE)
    return [token for token in tokens if len(token) >= 3 and token not in TRACE_STOPWORDS]


def is_traceable(excerpt, source):
    if str(excerpt or "").strip().startswith("[OMISSÃO]"):
        return True
    excerpt_tokens = trace_tokens(excerpt)
    if len(excerpt_tokens) < 3:
        return True
    source_token_string = " ".join(trace_tokens(source))
    if len(excerpt_tokens) <= 8:
        return all(token in source_token_string for token in excerpt_tokens)
    for window in (12, 10, 8, 6):
        if len(excerpt_tokens) < window:
            continue
        for index in range(0, len(excerpt_tokens) - window + 1):
            sequence = " ".join(excerpt_tokens[index:index + window])
            if sequence in source_token_string:
                return True
    return False


def resolve_project_dir(path, explicit_project_dir=None):
    if explicit_project_dir:
        return Path(explicit_project_dir).resolve()
    return Path(path).resolve().parent


def load_source_texts(project_dir):
    sources = {}
    candidates = {
        "ETP": [
            project_dir / ".sysdoc" / "cache" / "textos" / "ETP.txt",
            project_dir / "ETP.txt",
        ],
        "TR": [
            project_dir / ".sysdoc" / "cache" / "textos" / "TR.txt",
            project_dir / "TR.txt",
        ],
    }
    for doc, paths in candidates.items():
        for path in paths:
            if path.is_file():
                sources[doc] = path.read_text(encoding="utf-8", errors="replace")
                break
    return sources


def validate_document_paths(errors, data, project_dir):
    docs = data.get("documentos_analisados")
    if isinstance(docs, str):
        docs = [docs]
    if not isinstance(docs, list):
        errors.append("documentos_analisados: deve ser string ou lista")
        return
    for index, item in enumerate(docs, start=1):
        value = str(item or "").strip()
        if not value or re.match(r"^[a-z]+://", value, flags=re.IGNORECASE):
            continue
        has_known_extension = bool(re.search(r"\.(pdf|docx|txt|md|json)\b", value, flags=re.IGNORECASE))
        looks_like_path = "\\" in value or has_known_extension
        if not looks_like_path:
            continue
        candidates = [
            Path(value),
            project_dir / value,
            ROOT / value,
        ]
        if not any(candidate.is_file() for candidate in candidates):
            errors.append(f"documentos_analisados[{index}]: arquivo não localizado `{value}`")


def validate_traceability(errors, data, project_dir):
    sources = load_source_texts(project_dir)
    if not sources:
        return
    for index, item in enumerate(data.get("itens", []), start=1):
        if not isinstance(item, dict):
            continue
        doc = item.get("documento")
        if doc not in sources:
            continue
        if not is_traceable(item.get("de"), sources[doc]):
            errors.append(f"itens[{index}]: campo `de` não foi rastreado no texto extraído de {doc}; rode `python sysdoc.py prepare {project_dir.name}` e confira o trecho literal")


def validate_generated_language(errors, data):
    for key in ("titulo", "subtitulo", "parecer_executivo", "nota_integridade"):
        validate_portuguese_accents(errors, data.get(key), f"raiz.{key}")

    projeto = data.get("projeto", {})
    if isinstance(projeto, dict):
        for key in ("órgão", "objeto"):
            validate_portuguese_accents(errors, projeto.get(key), f"projeto.{key}")

    metadados = data.get("metadados", [])
    if isinstance(metadados, list):
        for index, meta in enumerate(metadados, start=1):
            if isinstance(meta, dict):
                validate_portuguese_accents(errors, meta.get("label"), f"metadados[{index}].label")
                validate_portuguese_accents(errors, meta.get("valor"), f"metadados[{index}].valor")

    for secao_key in ("secao_etp", "secao_tr"):
        secao = data.get(secao_key, {})
        if isinstance(secao, dict):
            validate_portuguese_accents(errors, secao.get("parecer_documento"), f"{secao_key}.parecer_documento")

    itens = data.get("itens", [])
    if isinstance(itens, list):
        for index, item in enumerate(itens, start=1):
            if not isinstance(item, dict):
                continue
            for key in ("item", "para", "parecer", "fundamento"):
                validate_portuguese_accents(errors, item.get(key), f"itens[{index}].{key}")


def validate_ids(errors, itens, doc):
    doc_itens = [item for item in itens if item.get("documento") == doc]
    for index, item in enumerate(doc_itens, start=1):
        expected = f"{doc}-{index:03d}"
        if item.get("id") != expected:
            errors.append(f"{doc}: id esperado `{expected}`, recebido `{item.get('id')}`")
        if item.get("número") != index:
            errors.append(f"{doc}: número esperado `{index}`, recebido `{item.get('número')}`")


def validate_item_coherence(errors, item, label):
    classificacao = item.get("classificação")
    severidade = item.get("severidade")
    risco = item.get("risco_jurídico")

    if classificacao == "risco" and risco not in {"relevante", "bloqueante"}:
        errors.append(f"{label}: item classificado como risco deve ter risco jurídico relevante ou bloqueante")
    if classificacao == "conforme" and risco != "informativo":
        errors.append(f"{label}: item conforme deve ter risco jurídico informativo")
    if risco == "bloqueante" and severidade not in {"crítica", "alta"}:
        errors.append(f"{label}: risco bloqueante exige severidade crítica ou alta")
    if item.get("alterado_pelo_jurídico") is True and item.get("de") == item.get("para"):
        errors.append(f"{label}: marcado como alterado pelo jurídico sem alteração efetiva entre de/para")


def validate(path, project_dir=None):
    errors = []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    project_dir = resolve_project_dir(path, project_dir)

    add_missing(errors, data, REQUIRED_TOP, "raiz")
    validate_modelo_ia(errors, data)
    validate_generated_language(errors, data)
    validate_document_paths(errors, data, project_dir)

    projeto = data.get("projeto", {})
    if isinstance(projeto, dict):
        add_missing(errors, projeto, REQUIRED_PROJETO, "projeto")
    else:
        errors.append("projeto: deve ser objeto")

    metadados = data.get("metadados", [])
    if not isinstance(metadados, list) or not metadados:
        errors.append("metadados: deve ser lista não vazia")
    else:
        for index, meta in enumerate(metadados, start=1):
            if not isinstance(meta, dict):
                errors.append(f"metadados[{index}]: deve ser objeto")
                continue
            add_missing(errors, meta, ["label", "valor"], f"metadados[{index}]")

    for secao_key in ("secao_etp", "secao_tr"):
        secao = data.get(secao_key, {})
        if not isinstance(secao, dict):
            errors.append(f"{secao_key}: deve ser objeto")
            continue
        add_missing(errors, secao, REQUIRED_SECAO, secao_key)
        classificacao_doc = secao.get("classificação_documento")
        if classificacao_doc not in ENUMS["classificação_documento"]:
            errors.append(f"{secao_key}: classificação_documento inválida `{classificacao_doc}`")
        if word_count(secao.get("parecer_documento")) < 120:
            errors.append(f"{secao_key}: parecer_documento deve ter pelo menos 120 palavras")

    if word_count(data.get("parecer_executivo")) < 450:
        errors.append("parecer_executivo: deve ter pelo menos 450 palavras")

    itens = data.get("itens", [])
    if not isinstance(itens, list) or not itens:
        errors.append("itens: deve ser lista não vazia")
        itens = []

    seen_ids = set()
    for index, item in enumerate(itens, start=1):
        label = f"itens[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: deve ser objeto")
            continue

        add_missing(errors, item, REQUIRED_ITEM, label)

        item_id = item.get("id")
        if item_id in seen_ids:
            errors.append(f"{label}: id duplicado `{item_id}`")
        seen_ids.add(item_id)

        documento = item.get("documento")
        if documento not in ENUMS["documento"]:
            errors.append(f"{label}: documento inválido `{documento}`")
        elif not re.fullmatch(rf"{documento}-\d{{3}}", str(item_id or "")):
            errors.append(f"{label}: id `{item_id}` não segue o padrão {documento}-NNN")

        for enum_key in ("classificação", "severidade", "risco_jurídico", "status_delic"):
            if enum_key in item and item.get(enum_key) not in ENUMS[enum_key]:
                errors.append(f"{label}: {enum_key} inválido `{item.get(enum_key)}`")

        if not isinstance(item.get("número"), int):
            errors.append(f"{label}: número deve ser inteiro")

        if has_placeholder(item.get("para")):
            errors.append(f"{label}: campo `para` contém placeholder ou reticências")

        for text_key in ("de", "para", "parecer", "fundamento"):
            if word_count(item.get(text_key)) < 3:
                errors.append(f"{label}: campo `{text_key}` está curto demais")

        validate_item_coherence(errors, item, label)

    validate_ids(errors, itens, "ETP")
    validate_ids(errors, itens, "TR")
    validate_traceability(errors, data, project_dir)

    return errors


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Validador determinístico do JSON consolidado SysDoc."
    )
    parser.add_argument("json_path", help="Caminho para dados_consolidados.json")
    parser.add_argument("project_dir", nargs="?", default=None, help="Pasta do projeto (opcional)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output estruturado em JSON (para integrações)")
    args = parser.parse_args()

    try:
        project_dir = args.project_dir
        errors = validate(args.json_path, project_dir)
    except Exception as exc:
        if args.json_output:
            print(json.dumps({"valid": False, "errors": [str(exc)]}))
        else:
            print(f"ERRO: falha ao ler/validar JSON: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        print(json.dumps({"valid": len(errors) == 0, "errors": errors}))
        return 0 if not errors else 1

    if errors:
        print("SysDoc JSON inválido:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SysDoc JSON válido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
