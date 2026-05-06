#!/usr/bin/env python3
"""
Renderizador determinístico de análise SysDoc.

Recebe JSON consolidado (stdin ou arquivo) e gera HTML final
usando o template fixo analise_template.html.

Uso:
    python render_analise.py dados.json [projeto_dir]
    cat dados.json | python render_analise.py - [projeto_dir]

O HTML é salvo em [projeto_dir]/analise_<modelo_ia>_<data>.html.
Se já existir, preserva histórico com sufixo incremental _2, _3, etc.
Se projeto_dir não for informado, imprime no stdout.
"""

import json
import sys
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape


SCRIPT_DIR = Path(__file__).parent
TEMPLATE_PATH = SCRIPT_DIR / "analise_template.html"

CLASSIFICACAO_DOC_LABELS = {
    "aprovado": "Aprovado",
    "aprovado_com_ressalvas": "Aprovado com Ressalvas",
    "reprovado": "Reprovado",
    "pendente_de_complementação": "Pendente de Complementação",
    "pendente_de_complementacao": "Pendente de Complementação",
}

CLASSIFICACAO_DOC_CSS = {
    "aprovado": "conforme",
    "aprovado_com_ressalvas": "conforme",
    "reprovado": "risco",
    "pendente_de_complementação": "ajuste",
    "pendente_de_complementacao": "ajuste",
}

SEVERIDADE_LABELS = {
    "crítica": "Crítica",
    "critica": "Crítica",
    "alta": "Alta",
    "média": "Média",
    "media": "Média",
    "baixa": "Baixa",
    "informativa": "Informativa",
}

SEVERIDADE_CSS = {
    "crítica": "critica",
    "critica": "critica",
    "alta": "alta",
    "média": "media",
    "media": "media",
    "baixa": "baixa",
    "informativa": "informativa",
}

RISCO_LABELS = {
    "bloqueante": "Bloqueante",
    "relevante": "Relevante",
    "menor": "Menor",
    "informativo": "Informativo",
}

STATUS_DELIC_LABELS = {
    "confirmado": "Confirmado",
    "novo": "Novo",
    "divergente": "Divergente",
    None: "",
}

DOC_NAMES = {
    "ETP": "Estudo Técnico Preliminar",
    "TR": "Termo de Referência",
}


def esc(text):
    if text is None:
        return ""
    return escape(str(text))


def count_items(itens, campo, valor):
    return sum(1 for i in itens if normalize_key(i.get(campo, "")) == valor)


def normalize_key(val):
    if val is None:
        return ""
    return (
        str(val)
        .lower()
        .replace("í", "i")
        .replace("é", "e")
        .replace("ã", "a")
        .replace("ç", "c")
        .replace("ê", "e")
        .strip()
    )


def calc_resumo(itens):
    return {
        "por_classificacao": {
            "conformes": count_items(itens, "classificação", "conforme") or count_items(itens, "classificacao", "conforme"),
            "ajustes_necessarios": count_items(itens, "classificação", "ajuste_necessario") or count_items(itens, "classificacao", "ajuste_necessario"),
            "riscos": count_items(itens, "classificação", "risco") or count_items(itens, "classificacao", "risco"),
            "pendentes": count_items(itens, "classificação", "pendente") or count_items(itens, "classificacao", "pendente"),
        },
        "por_severidade": {
            "criticas": count_items(itens, "severidade", "critica"),
            "altas": count_items(itens, "severidade", "alta"),
            "medias": count_items(itens, "severidade", "media"),
            "baixas": count_items(itens, "severidade", "baixa"),
            "informativas": count_items(itens, "severidade", "informativa"),
        },
        "por_risco_juridico": {
            "bloqueantes": count_items(itens, "risco_jurídico", "bloqueante") or count_items(itens, "risco_juridico", "bloqueante"),
            "relevantes": count_items(itens, "risco_jurídico", "relevante") or count_items(itens, "risco_juridico", "relevante"),
            "menores": count_items(itens, "risco_jurídico", "menor") or count_items(itens, "risco_juridico", "menor"),
            "informativos": count_items(itens, "risco_jurídico", "informativo") or count_items(itens, "risco_juridico", "informativo"),
        },
    }


def get_field(item, *keys):
    for k in keys:
        if k in item and item[k] is not None:
            return item[k]
    return None


def format_parecer_executivo(text):
    if not text:
        return ""
    paragraphs = text.strip().split("\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        p_escaped = esc(p)
        p_escaped = re.sub(
            r'\*\*(.+?)\*\*',
            r'<strong>\1</strong>',
            p_escaped
        )
        html_parts.append(f"<p>{p_escaped}</p>")
    return "\n                    ".join(html_parts)


def slug_filename_part(value):
    text = str(value or "").strip().lower()
    text = (
        text.replace("á", "a").replace("à", "a").replace("â", "a").replace("ã", "a")
        .replace("é", "e").replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o").replace("ô", "o").replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    return text.strip("-._") or "modelo"


def extract_date_for_filename(data_analise):
    text = str(data_analise or "").strip()
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    tz = timezone(timedelta(hours=-3))
    return datetime.now(tz).strftime("%Y-%m-%d")


def resolve_next_filename(projeto_dir, data):
    modelo_ia = get_field(data, "modelo_ia", "nome_modelo_ia", "modelo") or "gpt-5"
    data_analise = get_field(data, "data_análise", "data_analise")
    stem = f"analise_{slug_filename_part(modelo_ia)}_{extract_date_for_filename(data_analise)}"
    base = Path(projeto_dir) / f"{stem}.html"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = Path(projeto_dir) / f"{stem}_{n}.html"
        if not candidate.exists():
            return candidate
        n += 1


def render(data):
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

    projeto = data.get("projeto", {})
    metadados_raw = data.get("metadados", [])
    if not metadados_raw and projeto:
        metadados_raw = []
        field_map = [
            ("órgão", "Órgão"), ("orgao", "Órgão"),
            ("processo", "Processo"),
            ("valor_estimado", "Valor Estimado"),
            ("marco_normativo", "Marco Normativo"),
            ("data_análise", "Data da Análise"), ("data_analise", "Data da Análise"),
        ]
        seen = set()
        for key, label in field_map:
            if label in seen:
                continue
            val = projeto.get(key) or data.get(key)
            if val:
                metadados_raw.append({"label": label, "valor": val})
                seen.add(label)
        for extra in data.get("metadados_extra", []):
            metadados_raw.append(extra)

    all_itens = data.get("itens", [])
    docs_order = []
    seen_docs = set()
    for item in all_itens:
        doc = get_field(item, "documento") or "ETP"
        if doc not in seen_docs:
            docs_order.append(doc)
            seen_docs.add(doc)

    if not docs_order:
        docs_order = ["ETP", "TR"]

    documentos = []
    all_itens_flat = []

    for doc_sigla in docs_order:
        doc_itens = [i for i in all_itens if get_field(i, "documento") == doc_sigla]
        doc_data = data.get(f"secao_{doc_sigla.lower()}", {}) or data.get(doc_sigla.lower(), {}) or {}

        classificacao_doc = get_field(doc_data, "classificação_documento", "classificacao_documento") or "pendente_de_complementacao"
        parecer_doc = get_field(doc_data, "parecer_documento") or ""

        tem_delic = any(get_field(i, "status_delic") is not None for i in doc_itens)

        rendered_itens = []
        for item in doc_itens:
            sev_raw = normalize_key(get_field(item, "severidade"))
            risco_raw = normalize_key(get_field(item, "risco_jurídico", "risco_juridico"))
            status_raw = get_field(item, "status_delic")
            alterado = get_field(item, "alterado_pelo_jurídico", "alterado_pelo_juridico") or False

            rendered_itens.append({
                "id": esc(get_field(item, "id")),
                "secao": esc(get_field(item, "seção", "secao")),
                "severidade": SEVERIDADE_CSS.get(sev_raw, sev_raw),
                "severidade_label": SEVERIDADE_LABELS.get(sev_raw, sev_raw.title()),
                "risco_juridico": risco_raw,
                "risco_juridico_label": RISCO_LABELS.get(risco_raw, risco_raw.title()),
                "de": esc(get_field(item, "de")),
                "para": esc(get_field(item, "para")),
                "fundamento": esc(get_field(item, "fundamento")),
                "parecer": esc(get_field(item, "parecer")),
                "alterado_pelo_juridico": alterado,
                "status_delic": status_raw or "",
                "status_delic_label": STATUS_DELIC_LABELS.get(status_raw, str(status_raw or "").title()),
            })

        resumo = calc_resumo(doc_itens)

        classificacao_css = CLASSIFICACAO_DOC_CSS.get(
            normalize_key(classificacao_doc), "ajuste"
        )
        classificacao_label = CLASSIFICACAO_DOC_LABELS.get(
            normalize_key(classificacao_doc),
            classificacao_doc.replace("_", " ").title()
        )

        documentos.append({
            "sigla": doc_sigla,
            "nome_completo": f"{DOC_NAMES.get(doc_sigla, doc_sigla)} ({doc_sigla} {get_field(doc_data, 'numero', 'número') or ''})",
            "classificacao_documento_css": classificacao_css,
            "classificacao_documento_label": classificacao_label,
            "parecer_documento": esc(parecer_doc),
            "total_itens": len(doc_itens),
            "resumo": resumo,
            "tem_status_delic": tem_delic,
            "itens": rendered_itens,
        })

        all_itens_flat.extend(doc_itens)

    resumo_geral = calc_resumo(all_itens_flat)
    resumo_geral["total_itens"] = len(all_itens_flat)

    tz = timezone(timedelta(hours=-3))
    now_iso = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
    data_analise = get_field(data, "data_análise", "data_analise") or now_iso

    parecer_exec = get_field(data, "parecer_executivo") or ""
    parecer_html = format_parecer_executivo(parecer_exec)

    titulo = get_field(data, "titulo", "título") or "Análise Comparativa Técnica e Jurídica"
    subtitulo = get_field(data, "subtitulo", "subtítulo") or get_field(projeto, "objeto") or ""

    docs_analisados = get_field(data, "documentos_analisados")
    if isinstance(docs_analisados, list):
        docs_analisados = ", ".join(docs_analisados)
    docs_analisados = docs_analisados or ""

    nota = get_field(data, "nota_integridade") or (
        "Este documento contém análise técnica e jurídica gerada a partir de template determinístico. "
        "Tabelas e totais calculados automaticamente a partir do JSON validado pelo orchestrator. "
        "Recomendações devem ser avaliadas pela alta administração e áreas jurídica antes de publicação."
    )

    versao = get_field(data, "versao", "versão") or "1.0"

    html = render_template(
        template_text,
        titulo=esc(titulo),
        subtitulo=esc(subtitulo),
        metadados=metadados_raw,
        resumo_geral=resumo_geral,
        documentos=documentos,
        parecer_executivo=parecer_html,
        data_analise=esc(data_analise),
        versao=esc(versao),
        documentos_analisados=esc(docs_analisados),
        nota_integridade=esc(nota),
    )

    return html


def render_template(template, **ctx):
    """
    Mini template engine — processa Jinja2-like syntax sem dependências externas.
    Suporta: {{ var }}, {% for %}, {% endfor %}, {% if %}, {% endif %}, {% else %}
    """
    lines = template.split("\n")
    output = []
    stack = []  # (type, iterator_or_condition, var_name, collection)

    i = 0
    while i < len(lines):
        line = lines[i]

        # {% for item in collection %} / {% for item in obj.collection %}
        for_match = re.match(r'\s*\{%\s*for\s+(\w+)\s+in\s+([\w.]+)\s*%\}', line)
        if for_match:
            var_name = for_match.group(1)
            coll_expr = for_match.group(2)
            collection = resolve_value(coll_expr, ctx)
            if not isinstance(collection, (list, tuple)):
                collection = []
            block_lines = []
            depth = 1
            i += 1
            while i < len(lines) and depth > 0:
                if re.match(r'\s*\{%\s*for\s+', lines[i]):
                    depth += 1
                if re.match(r'\s*\{%\s*endfor\s*%\}', lines[i]):
                    depth -= 1
                    if depth == 0:
                        break
                block_lines.append(lines[i])
                i += 1
            for idx, item in enumerate(collection):
                sub_ctx = dict(ctx)
                sub_ctx[var_name] = item
                sub_ctx["loop"] = {"index": idx, "index0": idx, "first": idx == 0, "last": idx == len(collection) - 1}
                rendered = render_template("\n".join(block_lines), **sub_ctx)
                output.append(rendered)
            i += 1
            continue

        # {% if condition %}
        if_match = re.match(r'\s*\{%\s*if\s+(.+?)\s*%\}', line)
        if if_match:
            cond_expr = if_match.group(1)
            cond_result = eval_condition(cond_expr, ctx)
            block_true = []
            block_false = []
            current_block = block_true
            depth = 1
            i += 1
            while i < len(lines) and depth > 0:
                if re.match(r'\s*\{%\s*if\s+', lines[i]):
                    depth += 1
                    current_block.append(lines[i])
                elif re.match(r'\s*\{%\s*endif\s*%\}', lines[i]):
                    depth -= 1
                    if depth == 0:
                        break
                    current_block.append(lines[i])
                elif re.match(r'\s*\{%\s*else\s*%\}', lines[i]) and depth == 1:
                    current_block = block_false
                else:
                    current_block.append(lines[i])
                i += 1
            chosen = block_true if cond_result else block_false
            if chosen:
                rendered = render_template("\n".join(chosen), **ctx)
                output.append(rendered)
            i += 1
            continue

        # {{ variable }}
        rendered_line = re.sub(r'\{\{\s*(.+?)\s*\}\}', lambda m: resolve_var(m.group(1), ctx), line)
        output.append(rendered_line)
        i += 1

    return "\n".join(output)


def eval_condition(expr, ctx):
    expr = expr.strip()

    # "not X"
    if expr.startswith("not "):
        return not eval_condition(expr[4:], ctx)

    # "X > N", "X == N", etc.
    comp_match = re.match(r'(.+?)\s*(>|<|>=|<=|==|!=)\s*(.+)', expr)
    if comp_match:
        left = resolve_var(comp_match.group(1).strip(), ctx)
        op = comp_match.group(2)
        right_str = comp_match.group(3).strip()
        try:
            left_num = float(left) if left else 0
            right_num = float(right_str)
            if op == ">": return left_num > right_num
            if op == "<": return left_num < right_num
            if op == ">=": return left_num >= right_num
            if op == "<=": return left_num <= right_num
            if op == "==": return left_num == right_num
            if op == "!=": return left_num != right_num
        except (ValueError, TypeError):
            if op == "==": return str(left) == right_str
            if op == "!=": return str(left) != right_str
            return False

    # simple truthiness
    val = resolve_value(expr, ctx)
    return bool(val)


def resolve_var(expr, ctx):
    expr = expr.strip()

    # Handle addition: a + b
    if " + " in expr:
        parts = expr.split(" + ")
        total = 0
        for p in parts:
            val = resolve_var(p.strip(), ctx)
            try:
                total += float(val) if val else 0
            except (ValueError, TypeError):
                return str(val)
        result = int(total) if total == int(total) else total
        return str(result)

    current = resolve_value(expr, ctx)

    if isinstance(current, (int, float)):
        return str(int(current)) if current == int(current) else str(current)
    return str(current) if current is not None else ""


def resolve_value(expr, ctx):
    expr = expr.strip()

    # Handle dot notation: obj.key.subkey
    parts = expr.split(".")
    current = ctx
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return ""
        if current is None:
            return ""
    return current


def main():
    if len(sys.argv) < 2:
        print("Uso: python render_analise.py <arquivo.json> [projeto_dir]", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    projeto_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if json_path == "-":
        data = json.load(sys.stdin)
    else:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    html = render(data)

    if projeto_dir:
        out_path = resolve_next_filename(projeto_dir, data)
        out_path.write_text(html, encoding="utf-8")
        print(f"HTML gerado: {out_path}", file=sys.stderr)
    else:
        print(html)


if __name__ == "__main__":
    main()
