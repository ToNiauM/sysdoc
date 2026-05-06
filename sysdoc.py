#!/usr/bin/env python3
"""
CLI operacional do SysDoc.

Mantém o fluxo agnóstico a modelo e concentra tarefas determinísticas:
status, preparação de contexto, validação, renderização e publicação.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
IGNORED_DIRS = {".git", ".claude", "backup", "skills", "templates"}
TEXT_SUFFIXES = {".txt", ".md"}
SUPPORTED_REFERENCE_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
DEFAULT_LLM_MODEL = "gpt-4o-mini"
MAX_LLM_CONTEXT_CHARS = int(os.environ.get("SYSDOC_MAX_LLM_CONTEXT_CHARS", "700000"))

CONFIG_FILE = Path.home() / ".sysdoc" / "config.json"

KEY_TERMS = [
    "objeto",
    "garantia",
    "sanções",
    "recebimento",
    "liquidação",
    "pagamento",
    "vigência",
    "subcontratação",
    "habilitação",
    "reajuste",
    "desempate",
    "desconto",
    "pesquisa de preços",
    "sustentabilidade",
    "cooperativas",
]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    modelos: Path | None
    cache: Path
    source_cache: Path
    manifest: Path
    context: Path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def project_paths(project: str | Path) -> ProjectPaths:
    root = (Path.cwd() / project).resolve() if not Path(project).is_absolute() else Path(project).resolve()
    modelos = None
    for candidate in (root / "modelos", root / "Modelos"):
        if candidate.is_dir():
            modelos = candidate
            break
    cache = root / ".sysdoc" / "cache"
    return ProjectPaths(
        root=root,
        modelos=modelos,
        cache=cache,
        source_cache=cache / "textos",
        manifest=cache / "manifest.json",
        context=cache / "contexto_sysdoc.md",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_project_inputs(paths: ProjectPaths) -> None:
    missing = []
    if not (paths.root / "ETP.pdf").is_file():
        missing.append("ETP.pdf")
    if not (paths.root / "TR.pdf").is_file():
        missing.append("TR.pdf")
    if paths.modelos is None:
        missing.append("modelos/ ou Modelos/")
    if missing:
        raise SystemExit(f"Entradas obrigatórias ausentes em {rel(paths.root)}: {', '.join(missing)}")


def sanitize_filename(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return value.strip("._") or "arquivo"


def extract_pdf(path: Path) -> str:
    try:
        import PyPDF2
    except ImportError as exc:
        raise RuntimeError("PyPDF2 não está instalado; instale ou use uma referência .txt") from exc

    reader = PyPDF2.PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n--- Página {index} ---\n{text.strip()}")
    return "\n".join(pages).strip()


def extract_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for para in root.findall(".//w:p", ns):
        parts = [node.text for node in para.findall(".//w:t", ns) if node.text]
        if parts:
            paragraphs.append("".join(parts))
    return "\n".join(paragraphs).strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path)
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace")
    raise RuntimeError(f"Formato não suportado: {path.name}")


def list_reference_files(paths: ProjectPaths) -> list[Path]:
    if paths.modelos is None:
        return []
    return sorted(
        [
            path
            for path in paths.modelos.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_REFERENCE_SUFFIXES
        ],
        key=lambda p: rel(p).lower(),
    )


def write_extracted_text(paths: ProjectPaths, source: Path, label: str) -> dict:
    text = extract_text(source)
    out_name = f"{sanitize_filename(label)}.txt"
    out_path = paths.source_cache / out_name
    out_path.write_text(text, encoding="utf-8")
    return {
        "label": label,
        "source": rel(source),
        "cache": rel(out_path),
        "sha256": sha256(source),
        "chars": len(text),
        "words": count_words(text),
    }


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or "", flags=re.UNICODE))


def iter_lines(text: str) -> Iterable[tuple[int, str]]:
    for number, line in enumerate(text.splitlines(), start=1):
        clean = re.sub(r"\s+", " ", line).strip()
        if clean:
            yield number, clean


def detect_process(texts: dict[str, str]) -> str:
    pattern = re.compile(r"\b\d{10,20}\.\d{6}/\d{4}-\d{2}\b")
    for text in texts.values():
        match = pattern.search(text)
        if match:
            return match.group(0)
    return "não identificado"


def detect_values(texts: dict[str, str]) -> list[str]:
    values: list[str] = []
    pattern = re.compile(r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}")
    for text in texts.values():
        for value in pattern.findall(text):
            if value not in values:
                values.append(value)
            if len(values) >= 8:
                return values
    return values


def detect_object(texts: dict[str, str]) -> str:
    candidates = []
    for label in ("TR", "ETP"):
        text = texts.get(label, "")
        for _, line in iter_lines(text):
            lower = line.lower()
            if "contratação" in lower or "aquisição" in lower or "objeto" in lower:
                if 80 <= len(line) <= 500:
                    candidates.append(line)
                elif len(line) > 500:
                    candidates.append(line[:500].rstrip() + "...")
            if candidates:
                return candidates[0]
    return "não identificado"


def detect_sections(text: str, limit: int = 80) -> list[str]:
    sections = []
    pattern = re.compile(r"^\s*(\d+(?:\.\d+)*\.?)\s+(.{3,160})$")
    for number, line in iter_lines(text):
        match = pattern.match(line)
        if not match:
            continue
        title = re.sub(r"\s+", " ", match.group(2)).strip()
        sections.append(f"L{number}: {match.group(1)} {title}")
        if len(sections) >= limit:
            break
    return sections


def snippets_for_term(text: str, term: str, limit: int = 2) -> list[str]:
    hits = []
    term_norm = term.lower()
    for number, line in iter_lines(text):
        if term_norm in line.lower():
            hits.append(f"L{number}: {line[:280]}")
            if len(hits) >= limit:
                break
    return hits


def render_context(paths: ProjectPaths, manifest: dict, texts: dict[str, str]) -> str:
    process = detect_process(texts)
    values = detect_values(texts)
    obj = detect_object(texts)

    sections_etp = detect_sections(texts.get("ETP", ""))
    sections_tr = detect_sections(texts.get("TR", ""))

    lines: list[str] = []
    lines.append("# Contexto SysDoc")
    lines.append("")
    lines.append("Arquivo determinístico para economizar leitura do modelo. Use-o como mapa, não como substituto da conferência dos trechos relevantes nos textos extraídos.")
    lines.append("")
    lines.append("## Manifesto")
    lines.append("")
    lines.append("- Produzir análise comparativa técnica e jurídica de ETP e TR.")
    lines.append("- Preservar separação entre ETP e TR.")
    lines.append("- Selecionar apenas achados relevantes, com `de` literal, `para` pronto para colar, parecer objetivo e fundamento específico.")
    lines.append("- Escrever todos os campos gerados em norma culta do português brasileiro, com acentuação correta.")
    lines.append("")
    lines.append("## Entradas")
    lines.append("")
    for item in manifest["files"]:
        lines.append(f"- {item['label']}: `{item['source']}` -> `{item['cache']}` ({item['words']} palavras, sha256 {item['sha256'][:12]})")
    lines.append("")
    lines.append("## Briefing Detectado")
    lines.append("")
    lines.append(f"- Processo: {process}")
    lines.append(f"- Objeto provável: {obj}")
    lines.append(f"- Valores encontrados: {', '.join(values) if values else 'não identificados'}")
    lines.append("")
    lines.append("## Mapa De Seções")
    lines.append("")
    lines.append("### ETP")
    lines.extend(f"- {section}" for section in sections_etp[:60])
    lines.append("")
    lines.append("### TR")
    lines.extend(f"- {section}" for section in sections_tr[:80])
    lines.append("")
    lines.append("## Extratos Orientadores Por Tema")
    lines.append("")
    for term in KEY_TERMS:
        lines.append(f"### {term}")
        found_any = False
        for label in ("ETP", "TR"):
            hits = snippets_for_term(texts.get(label, ""), term)
            if hits:
                found_any = True
                lines.append(f"- {label}:")
                lines.extend(f"  - {hit}" for hit in hits)
        if not found_any:
            lines.append("- Não localizado nos textos principais.")
        lines.append("")
    lines.append("## Saída Obrigatória")
    lines.append("")
    lines.append("- Gerar `[pasta]/dados_consolidados.json` no schema canônico.")
    lines.append("- Validar com `python templates/validate_sysdoc.py [pasta]/dados_consolidados.json`.")
    lines.append("- Renderizar com `python templates/render_analise.py [pasta]/dados_consolidados.json [pasta]`.")
    lines.append("")
    return "\n".join(lines)


def prepare(project: str) -> int:
    paths = project_paths(project)
    ensure_project_inputs(paths)
    paths.source_cache.mkdir(parents=True, exist_ok=True)

    manifest = {
        "project": rel(paths.root),
        "files": [],
    }
    texts: dict[str, str] = {}

    for label, source in (("ETP", paths.root / "ETP.pdf"), ("TR", paths.root / "TR.pdf")):
        item = write_extracted_text(paths, source, label)
        manifest["files"].append(item)
        texts[label] = Path(item["cache"]).read_text(encoding="utf-8") if Path(item["cache"]).is_absolute() else (Path.cwd() / item["cache"]).read_text(encoding="utf-8")

    for index, source in enumerate(list_reference_files(paths), start=1):
        label = f"REF-{index:02d}_{source.stem}"
        item = write_extracted_text(paths, source, label)
        manifest["files"].append(item)
        texts[label] = Path(item["cache"]).read_text(encoding="utf-8") if Path(item["cache"]).is_absolute() else (Path.cwd() / item["cache"]).read_text(encoding="utf-8")

    paths.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.context.write_text(render_context(paths, manifest, texts), encoding="utf-8")

    print(f"Contexto preparado: {rel(paths.context)}")
    print(f"Textos extraídos: {rel(paths.source_cache)}")
    return 0


def status() -> int:
    print("Projetos SysDoc:")
    for directory in sorted([p for p in Path.cwd().iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        if directory.name in IGNORED_DIRS or directory.name.startswith("."):
            continue
        paths = project_paths(directory)
        has_etp = (directory / "ETP.pdf").is_file()
        has_tr = (directory / "TR.pdf").is_file()
        has_modelos = paths.modelos is not None
        has_json = (directory / "dados_consolidados.json").is_file()
        html_count = len(list(directory.glob("analise_*.html")))
        prepared = paths.context.is_file()
        if not any([has_etp, has_tr, has_modelos, has_json, html_count]):
            continue
        print(
            f"- {directory.name}: "
            f"ETP={'ok' if has_etp else 'faltando'}; "
            f"TR={'ok' if has_tr else 'faltando'}; "
            f"modelos={'ok' if has_modelos else 'faltando'}; "
            f"json={'ok' if has_json else 'não'}; "
            f"html={html_count}; "
            f"prepare={'ok' if prepared else 'não'}"
        )
    return 0


def run_python_script(args: list[str]) -> int:
    completed = subprocess.run([sys.executable, *args], cwd=ROOT)
    return completed.returncode


def validate(project: str) -> int:
    paths = project_paths(project)
    json_path = paths.root / "dados_consolidados.json"
    if not json_path.is_file():
        raise SystemExit(f"JSON não encontrado: {rel(json_path)}")
    return run_python_script(["templates/validate_sysdoc.py", str(json_path), str(paths.root)])


def render(project: str) -> int:
    paths = project_paths(project)
    json_path = paths.root / "dados_consolidados.json"
    if not json_path.is_file():
        raise SystemExit(f"JSON não encontrado: {rel(json_path)}")
    return run_python_script(["templates/render_analise.py", str(json_path), str(paths.root)])


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(config: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def connect_command() -> int:
    config = load_config()
    print("--- Configuração de Provedor de IA (SysDoc) ---")
    print("Selecione o provedor que deseja utilizar:")
    print("1. OpenRouter (Recomendado/Padrão)")
    print("2. OpenAI")
    print("3. Google Gemini")
    print("4. Anthropic")
    print("---------------------------------------------")
    
    choice = input("Digite o número da sua escolha [1]: ").strip()
    
    provider_map = {
        "1": "openrouter",
        "2": "openai",
        "3": "gemini",
        "4": "anthropic"
    }
    
    provider = provider_map.get(choice, "openrouter")
    config["active_provider"] = provider
    print(f"\nProvedor selecionado: {provider.upper()}")
    
    current_key = config.get(f"{provider}_api_key")
    mask = "***" if current_key else "nenhuma"
    new_key = input(f"Insira sua API Key para {provider.upper()} (atual: {mask}): ").strip()
    
    if new_key:
        config[f"{provider}_api_key"] = new_key
        print("Nova chave configurada com sucesso!")
    elif current_key:
        print("Mantendo a chave atual.")
    else:
        print("Nenhuma chave inserida. O provedor pode não funcionar até que você configure uma chave.")
        
    save_config(config)
    print(f"\nProvedor ativo atualizado para: {provider.upper()} em {CONFIG_FILE}")
    print("Dica: Use 'sysdoc models' para ver os modelos disponíveis e escolher um modelo padrão.")
    return 0


def models_command() -> int:
    config = load_config()
    provider = config.get("active_provider", "openrouter")
    api_key = config.get(f"{provider}_api_key")
    
    if not api_key:
        print(f"Erro: Chave de API para '{provider}' não encontrada.")
        print("Use 'sysdoc connect' primeiro para configurar sua chave.")
        return 1
        
    print(f"Buscando modelos disponíveis no provedor: {provider.upper()}...")
    try:
        models = fetch_models(provider, api_key)
    except Exception as e:
        print(f"Erro ao buscar modelos: {e}")
        return 1
        
    if not models:
        print("Nenhum modelo encontrado ou erro na API.")
        return 1
        
    print("\n--- Modelos Disponíveis ---")
    for i, model in enumerate(models, start=1):
        print(f"[{i}] {model}")
        
    print("\n---------------------------")
    choice = input("Digite o número do modelo para definir como PADRÃO (ou ENTER para sair): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(models):
        selected = models[int(choice) - 1]
        config["default_model"] = selected
        save_config(config)
        print(f"\nModelo '{selected}' definido como padrão com sucesso!")
    else:
        print("\nNenhuma alteração realizada.")
    return 0


def fetch_models(provider: str, api_key: str) -> list[str]:
    if provider == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    elif provider == "openai":
        url = "https://api.openai.com/v1/models"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    elif provider == "anthropic":
        url = "https://api.anthropic.com/v1/models"
        req = urllib.request.Request(url, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"})
    elif provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        req = urllib.request.Request(url)
    else:
        raise ValueError("Provedor inválido.")
        
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        
    models = []
    if provider in ("openrouter", "openai"):
        # Ambos retornam lista em data["data"]
        for item in data.get("data", []):
            models.append(item.get("id"))
    elif provider == "anthropic":
        # Anthropic retorna em data["data"]
        for item in data.get("data", []):
            models.append(item.get("id"))
    elif provider == "gemini":
        # Gemini retorna em data["models"], formato "models/nome"
        for item in data.get("models", []):
            name = item.get("name", "").replace("models/", "")
            models.append(name)
            
    # Filtro básico para OpenAI
    if provider == "openai":
        models = [m for m in models if "gpt" in m or "o1" in m or "o3" in m]
        
    return sorted(models)


def analyze(project: str, model: str | None = None, extra_instruction: str | None = None) -> int:
    config = load_config()
    provider = config.get("active_provider", "openrouter")
    
    # Se não passou flag, tenta usar o default configurado. Se não, fallback.
    model = model or config.get("default_model") or os.environ.get("SYSDOC_OPENAI_MODEL") or DEFAULT_LLM_MODEL
    
    api_key = config.get(f"{provider}_api_key") or os.environ.get(f"{provider.upper()}_API_KEY")
    if not api_key:
        raise SystemExit(
            f"Chave de API para o provedor '{provider}' não encontrada.\n"
            f"Configure usando: sysdoc config\n"
            f"Ou defina a variável de ambiente: {provider.upper()}_API_KEY"
        )

    print(f"Preparando contexto do projeto {project}...")
    prepare(project)

    paths = project_paths(project)
    prompt = build_llm_prompt(paths, model, extra_instruction)
    schema = json.loads((TEMPLATES / "schema_sysdoc.json").read_text(encoding="utf-8"))

    print(f"Chamando modelo: {model} (Provedor: {provider})")
    data = call_llm_json(provider=provider, api_key=api_key, model=model, prompt=prompt, schema=schema)
    data["modelo_ia"] = slug(model)

    out_path = paths.root / "dados_consolidados.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"JSON gravado: {rel(out_path)}")

    validation = validate(project)
    if validation != 0:
        print("A validacao falhou. Ajuste o JSON ou rode novamente com uma instrucao mais especifica.")
        return validation
    return publish(project)


def build_llm_prompt(paths: ProjectPaths, model: str, extra_instruction: str | None) -> str:
    context = paths.context.read_text(encoding="utf-8", errors="replace")
    skill = (ROOT / "skills" / "sysdoc" / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    schema_text = (TEMPLATES / "schema_sysdoc.json").read_text(encoding="utf-8", errors="replace")
    texts = load_llm_texts(paths)
    text_block = trim_llm_texts(texts)

    extra = extra_instruction.strip() if extra_instruction else "Nenhuma."
    return textwrap.dedent(
        f"""
        Voce e o motor de analise do SysDoc. Produza exclusivamente JSON valido no schema fornecido.

        Modelo real em uso: {model}
        Campo modelo_ia obrigatorio: {slug(model)}
        Projeto: {rel(paths.root)}
        Instrucao extra do usuario: {extra}

        Regras criticas:
        - Siga o fluxo canonico abaixo.
        - Gere entre 5 e 10 itens relevantes, salvo se a base for insuficiente.
        - Preserve o campo "de" como trecho literal do ETP ou TR; se houver omissao, use o marcador previsto na skill.
        - Nao invente artigo, acordao, numero SEI, valor, data ou clausula.
        - Preencha parecer_executivo com pelo menos 450 palavras.
        - Preencha parecer_documento de ETP e TR com pelo menos 120 palavras cada.
        - Use portugues brasileiro culto nos campos gerados.
        - Responda apenas com o objeto JSON final.

        # Fluxo canonico
        {skill}

        # Schema canonico
        {schema_text}

        # Contexto deterministico
        {context}

        # Textos extraidos para rastreabilidade
        {text_block}
        """
    ).strip()


def load_llm_texts(paths: ProjectPaths) -> list[tuple[str, str]]:
    items = []
    for path in sorted(paths.source_cache.glob("*.txt"), key=lambda p: p.name.lower()):
        items.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
    return items


def trim_llm_texts(texts: list[tuple[str, str]]) -> str:
    if not texts:
        return "[sem textos extraidos]"

    remaining = MAX_LLM_CONTEXT_CHARS
    blocks = []
    for name, text in texts:
        if remaining <= 0:
            blocks.append(f"\n## {name}\n[omitido por limite de contexto]")
            continue
        piece = text[:remaining]
        remaining -= len(piece)
        suffix = "\n[TRUNCADO POR LIMITE DE CONTEXTO]" if len(piece) < len(text) else ""
        blocks.append(f"\n## {name}\n{piece}{suffix}")
    return "\n".join(blocks)


def detect_provider(model: str) -> str:
    lower = model.lower()
    if "gemini" in lower:
        return "gemini"
    if "claude" in lower:
        return "anthropic"
    return "openai"


def call_llm_json(provider: str, api_key: str, model: str, prompt: str, schema: dict) -> dict:
    if provider == "openrouter":
        return call_openrouter_json(api_key, model, prompt, schema)
    elif provider == "openai":
        return call_openai_json(api_key, model, prompt, schema)
    elif provider == "gemini":
        return call_gemini_json(api_key, model, prompt, schema)
    elif provider == "anthropic":
        return call_anthropic_json(api_key, model, prompt, schema)
    else:
        raise RuntimeError(f"Provedor desconhecido: {provider}")


def call_openrouter_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Voce gera analises SysDoc em JSON estrito, sem Markdown e sem texto fora do JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {
            "type": "json_object" # OpenRouter usa type json_object muitas vezes, ou repassamos json_schema dependendo da LLM
        },
    }
    # OpenRouter suporta json_schema formal em modelos OpenAI/gemini recentes, 
    # mas json_object é mais universal lá. Vamos injetar o schema no system prompt.
    payload["messages"][0]["content"] += f"\nSchema obrigatório: {json.dumps(schema)}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sysdoc.local",
            "X-Title": "SysDoc CLI"
        },
        method="POST",
    )
    return execute_llm_request(request, extract_openai_chat_text)


def call_openai_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    # Usamos o endpoint padrão de Chat Completions se não for o "responses" que o SysDoc antigo usava
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Voce gera analises SysDoc em JSON estrito, sem Markdown e sem texto fora do JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "sysdoc_consolidated_analysis",
                "schema": schema,
                "strict": False,
            }
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return execute_llm_request(request, extract_openai_chat_text)


def extract_openai_chat_text(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"]
    except KeyError:
        return ""


def call_gemini_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "systemInstruction": {
            "parts": [{"text": "Você gera análises SysDoc em JSON estrito, sem Markdown e sem texto fora do JSON."}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return execute_llm_request(request, extract_gemini_text)


def extract_gemini_text(data: dict) -> str:
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return ""


def call_anthropic_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 8192,
        "system": f"Você gera análises SysDoc em JSON estrito, sem Markdown e sem texto fora do JSON. Responda exclusivamente com o JSON válido para este schema: {json.dumps(schema)}",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        method="POST",
    )
    return execute_llm_request(request, extract_anthropic_text)


def extract_anthropic_text(data: dict) -> str:
    try:
        return data["content"][0]["text"]
    except (KeyError, IndexError):
        return ""


def execute_llm_request(request: urllib.request.Request, extractor) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro da API ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Falha de rede: {exc}") from exc

    response_data = json.loads(raw)
    text = extractor(response_data)
    if not text:
        raise RuntimeError(f"Resposta da LLM sem texto utilizável: {raw[:1000]}")
    return parse_json_object(text)





def parse_json_object(text: str) -> dict:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(clean[start : end + 1])
    if not isinstance(data, dict):
        raise RuntimeError("A LLM retornou JSON, mas nao retornou um objeto no topo.")
    return data


def publish(project: str) -> int:
    paths = project_paths(project)
    json_path = paths.root / "dados_consolidados.json"
    if not json_path.is_file():
        raise SystemExit(f"JSON não encontrado: {rel(json_path)}")
    validation = validate(project)
    if validation != 0:
        return validation

    data = json.loads(json_path.read_text(encoding="utf-8"))
    model = slug(data.get("modelo_ia", "modelo"))
    date = extract_date(data.get("data_análise", ""))
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    archive = resolve_next_json_archive(paths.root, model, date, payload)
    if archive.exists():
        print(f"JSON versionado já existe: {rel(archive)}")
    else:
        archive.write_text(payload, encoding="utf-8")
        print(f"JSON versionado: {rel(archive)}")
    return render(project)


def resolve_next_json_archive(project_dir: Path, model: str, date: str, payload: str) -> Path:
    stem = f"dados_consolidados_{model}_{date}"
    first = project_dir / f"{stem}.json"
    if not first.exists() or first.read_text(encoding="utf-8", errors="replace") == payload:
        return first
    index = 2
    while True:
        candidate = project_dir / f"{stem}_{index}.json"
        if not candidate.exists() or candidate.read_text(encoding="utf-8", errors="replace") == payload:
            return candidate
        index += 1


def slug(value: str) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("á", "a").replace("à", "a").replace("â", "a").replace("ã", "a")
        .replace("é", "e").replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o").replace("ô", "o").replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return re.sub(r"[^a-z0-9._-]+", "-", text).strip("-._") or "modelo"


def extract_date(value: str) -> str:
    text = str(value or "")
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return datetime.now().strftime("%Y-%m-%d")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysdoc.py",
        description="Workflow determinístico do SysDoc.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Exemplos:
              python sysdoc.py status
              python sysdoc.py prepare Combustivel
              python sysdoc.py validate Combustivel
              python sysdoc.py render Combustivel
              python sysdoc.py publish Combustivel
            """
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Lista projetos e estado operacional.")
    sub.add_parser("connect", help="Configura o provedor ativo (OpenRouter, OpenAI, Gemini, Anthropic) e a chave de API.")
    sub.add_parser("models", help="Lista os modelos do provedor conectado e permite definir um padrão.")
    analyze_parser = sub.add_parser("analyze", help="Prepara, chama a LLM configurada, valida e publica.")
    analyze_parser.add_argument("project", help="Pasta do projeto SysDoc.")
    analyze_parser.add_argument("--model", default=None, help=f"Modelo OpenAI. Padrao: {DEFAULT_LLM_MODEL}.")
    analyze_parser.add_argument("--instruction", default=None, help="Instrucao extra para a analise.")

    for command in ("prepare", "validate", "render", "publish"):
        item = sub.add_parser(command, help=f"Executa {command} em um projeto.")
        item.add_argument("project", help="Pasta do projeto SysDoc.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "connect":
        return connect_command()
    if args.command == "models":
        return models_command()
    if args.command == "status":
        return status()
    if args.command == "prepare":
        return prepare(args.project)
    if args.command == "validate":
        return validate(args.project)
    if args.command == "render":
        return render(args.project)
    if args.command == "analyze":
        return analyze(args.project, model=args.model, extra_instruction=args.instruction)
    if args.command == "publish":
        return publish(args.project)
    parser.error("comando inválido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
