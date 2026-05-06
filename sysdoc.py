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
import shutil
import subprocess
import sys
import textwrap
import time
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
DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"
MAX_LLM_CONTEXT_CHARS = int(os.environ.get("SYSDOC_MAX_LLM_CONTEXT_CHARS", "700000"))

VERSION = "1.1.0"

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


def _find_file_case_insensitive(directory: Path, name: str) -> Path | None:
    """Encontra um arquivo no diretório ignorando capitalização (D4)."""
    name_lower = name.lower()
    for entry in directory.iterdir():
        if entry.is_file() and entry.name.lower() == name_lower:
            return entry
    return None


def ensure_project_inputs(paths: ProjectPaths) -> None:
    missing = []
    if _find_file_case_insensitive(paths.root, "ETP.pdf") is None:
        missing.append("ETP.pdf")
    if _find_file_case_insensitive(paths.root, "TR.pdf") is None:
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
        import pypdf
    except ImportError as exc:
        raise RuntimeError("pypdf não está instalado; instale com: pip install pypdf") from exc

    reader = pypdf.PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n--- Página {index} ---\n{text.strip()}")
    text = "\n".join(pages).strip()
    if len(text) < 100:
        print(f"⚠️  {path.name}: texto extraído muito curto ({len(text)} chars).")
        print("   Este PDF pode ser escaneado (sem camada de texto).")
        print("   Tente converter com: pdftotext -layout arquivo.pdf saida.txt")
    return text


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
    for table in root.findall(".//w:tbl", ns):
        for row in table.findall(".//w:tr", ns):
            cells = []
            for cell in row.findall(".//w:tc", ns):
                parts = [n.text for n in cell.findall(".//w:t", ns) if n.text]
                cells.append("".join(parts))
            if cells:
                paragraphs.append(" | ".join(cells))
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
    # Tenta formato SEI: NNNNN.NNNNNN/AAAA-NN
    sei_pattern = re.compile(r"\b\d{5,6}\.\d{6}/\d{4}-\d{2}\b")
    # Tenta formato CNPJ-like: NN.NNN.NNN/NNNN-NN
    cnpj_pattern = re.compile(r"\b\d{2,3}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
    for text in texts.values():
        for pattern in (sei_pattern, cnpj_pattern):
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

    for label, file_name in (("ETP", "ETP.pdf"), ("TR", "TR.pdf")):
        source = _find_file_case_insensitive(paths.root, file_name) or (paths.root / file_name)
        item = write_extracted_text(paths, source, label)
        manifest["files"].append(item)
        cache_path = Path(item["cache"])
        if not cache_path.is_absolute():
            cache_path = paths.source_cache / cache_path.name
        texts[label] = cache_path.read_text(encoding="utf-8")

    for index, source in enumerate(list_reference_files(paths), start=1):
        label = f"REF-{index:02d}_{source.stem}"
        item = write_extracted_text(paths, source, label)
        manifest["files"].append(item)
        cache_path = Path(item["cache"])
        if not cache_path.is_absolute():
            cache_path = paths.source_cache / cache_path.name
        texts[label] = cache_path.read_text(encoding="utf-8")

    paths.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.context.write_text(render_context(paths, manifest, texts), encoding="utf-8")

    print(f"Contexto preparado: {rel(paths.context)}")
    print(f"Textos extraídos: {rel(paths.source_cache)}")
    return 0


def status() -> int:
    COL = 30
    header = f"{'PROJETO':<{COL}} {'ETP':>5} {'TR':>5} {'MODELOS':>8} {'JSON':>5} {'HTML':>5} {'PREP':>5}"
    rows = []
    for directory in sorted([p for p in Path.cwd().iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        if directory.name in IGNORED_DIRS or directory.name.startswith("."):
            continue
        paths = project_paths(directory)
        has_etp = _find_file_case_insensitive(directory, "ETP.pdf") is not None
        has_tr = _find_file_case_insensitive(directory, "TR.pdf") is not None
        has_modelos = paths.modelos is not None
        has_json = (directory / "dados_consolidados.json").is_file()
        html_count = len(list(directory.glob("analise_*.html")))
        prepared = paths.context.is_file()
        if not any([has_etp, has_tr, has_modelos, has_json, html_count]):
            continue
        name = directory.name[:COL]
        etp_s = "ok" if has_etp else "---"
        tr_s = "ok" if has_tr else "---"
        mod_s = "ok" if has_modelos else "---"
        json_s = "ok" if has_json else "---"
        html_s = str(html_count) if html_count else "---"
        prep_s = "ok" if prepared else "---"
        rows.append(f"{name:<{COL}} {etp_s:>5} {tr_s:>5} {mod_s:>8} {json_s:>5} {html_s:>5} {prep_s:>5}")
    if not rows:
        print("Nenhum projeto SysDoc encontrado neste diretório.")
        return 0
    print(header)
    print("-" * len(header))
    for row in rows:
        print(row)
    print(f"\n{len(rows)} projeto(s) encontrado(s).")
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


def run_validate_and_capture(project: str) -> list[str]:
    """Retorna linhas de erro do validador para uso no retry automático (M2-A)."""
    paths = project_paths(project)
    json_path = paths.root / "dados_consolidados.json"
    result = subprocess.run(
        [sys.executable, str(TEMPLATES / "validate_sysdoc.py"), str(json_path), str(paths.root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


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
        # Validação simples da chave antes de salvar (U2)
        print(f"Validando chave para {provider.upper()}...")
        config[f"{provider}_api_key"] = new_key
        try:
            fetch_models(provider, new_key)
            print("✅ Chave válida — conexão OK.")
        except Exception as exc:
            print(f"⚠️  Não foi possível validar a chave: {exc}")
            print("Chave salva, mas verifique se está correta antes de usar.")
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

    # Filtro por termo (U3)
    filtro = input("Filtrar modelos (ENTER para listar todos): ").strip().lower()
    filtered = [m for m in models if not filtro or filtro in m.lower()]

    if not filtered:
        print(f"Nenhum modelo encontrado com o filtro '{filtro}'.")
        return 1

    # Paginação para listas grandes
    page_size = 30
    total = len(filtered)
    page = 0
    while True:
        start = page * page_size
        end = min(start + page_size, total)
        print(f"\n--- Modelos Disponíveis ({start + 1}-{end} de {total}) ---")
        for i, model in enumerate(filtered[start:end], start=start + 1):
            current = " ← atual" if model == config.get("default_model") else ""
            print(f"[{i}] {model}{current}")
        print("---")
        nav = []
        if end < total:
            nav.append("[P]róxima página")
        if page > 0:
            nav.append("[V]oltar")
        nav.append("[Núomero] selecionar")
        nav.append("[ENTER] sair")
        print(" | ".join(nav))
        choice = input("> ").strip()
        if choice.upper() == "P" and end < total:
            page += 1
        elif choice.upper() == "V" and page > 0:
            page -= 1
        elif choice.isdigit() and 1 <= int(choice) <= total:
            selected = filtered[int(choice) - 1]
            config["default_model"] = selected
            save_config(config)
            print(f"\nModelo '{selected}' definido como padrão com sucesso!")
            break
        else:
            print("\nNenhuma alteração realizada.")
            break
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


def analyze(project: str, model: str | None = None, extra_instruction: str | None = None, dry_run: bool = False) -> int:
    config = load_config()
    provider = config.get("active_provider", "openrouter")

    # Se não passou flag, tenta usar o default configurado. Se não, fallback.
    model = model or config.get("default_model") or os.environ.get("SYSDOC_OPENAI_MODEL") or DEFAULT_LLM_MODEL

    if not dry_run:
        api_key = config.get(f"{provider}_api_key") or os.environ.get(f"{provider.upper()}_API_KEY")
        if not api_key:
            raise SystemExit(
                f"Chave de API para o provedor '{provider}' não encontrada.\n"
                f"Configure usando: sysdoc connect\n"
                f"Ou defina a variável de ambiente: {provider.upper()}_API_KEY"
            )
    else:
        api_key = None

    print(f"Preparando contexto do projeto {project}...")
    prepare(project)

    paths = project_paths(project)
    schema = json.loads((TEMPLATES / "schema_sysdoc.json").read_text(encoding="utf-8"))

    if dry_run:
        prompt = build_llm_prompt(paths, model, extra_instruction)
        print("\n" + "=" * 60)
        print("[DRY-RUN] Prompt que seria enviado à LLM:")
        print("=" * 60)
        print(prompt[:4000])
        if len(prompt) > 4000:
            print(f"\n... [truncado — {len(prompt)} chars no total]")
        print("=" * 60)
        print(f"\nModelo: {model} | Provedor: {provider}")
        print("Nenhuma chamada de API foi realizada (--dry-run).")
        return 0

    out_path = paths.root / "dados_consolidados.json"
    current_instruction = extra_instruction
    validation = 1

    for attempt in range(1, 3):
        attempt_label = f" [tentativa {attempt}/2]" if attempt > 1 else ""
        print(f"Chamando modelo: {model} (Provedor: {provider})...{attempt_label}")
        prompt = build_llm_prompt(paths, model, current_instruction)
        data = call_llm_json(provider=provider, api_key=api_key, model=model, prompt=prompt, schema=schema)
        data["modelo_ia"] = slug(model)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"JSON gravado: {rel(out_path)}")

        validation = validate(project)
        if validation == 0:
            break
        if attempt < 2:
            errors = run_validate_and_capture(project)
            if errors:
                err_summary = "; ".join(errors[:10])
                print(f"⚠️  Validação falhou ({len(errors)} erro(s)). Tentativa de correção automática...")
                current_instruction = f"Corrija os seguintes erros de validação: {err_summary}"
            else:
                print("A validação falhou. Ajuste o JSON ou rode novamente com uma instrução mais específica.")
                return validation

    if validation != 0:
        print("A validação falhou mesmo após correção automática. Ajuste o JSON manualmente.")
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


def _call_openai_compatible_json(
    api_key: str,
    model: str,
    prompt: str,
    schema: dict,
    base_url: str,
    extra_headers: dict | None = None,
    use_json_schema: bool = True,
) -> dict:
    """Base compartilhada para OpenAI e OpenRouter (C1)."""
    system_msg = "Voce gera analises SysDoc em JSON estrito, sem Markdown e sem texto fora do JSON."
    if not use_json_schema:
        system_msg += f"\nSchema obrigatorio: {json.dumps(schema)}"

    response_format: dict
    if use_json_schema:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "sysdoc_consolidated_analysis",
                "schema": schema,
                "strict": False,
            },
        }
    else:
        response_format = {"type": "json_object"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "response_format": response_format,
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    request = urllib.request.Request(
        base_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    return execute_llm_request(request, _read_openai_stream)


def call_openrouter_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    # OpenAI e Google via OpenRouter suportam json_schema formal; demais usam json_object (M2-B)
    use_schema = model.startswith("openai/") or model.startswith("google/")
    return _call_openai_compatible_json(
        api_key=api_key,
        model=model,
        prompt=prompt,
        schema=schema,
        base_url="https://openrouter.ai/api/v1/chat/completions",
        extra_headers={"HTTP-Referer": "https://sysdoc.local", "X-Title": "SysDoc CLI"},
        use_json_schema=use_schema,
    )


def call_openai_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    return _call_openai_compatible_json(
        api_key=api_key,
        model=model,
        prompt=prompt,
        schema=schema,
        base_url="https://api.openai.com/v1/chat/completions",
        use_json_schema=True,
    )


def _read_openai_stream(response) -> str:
    """Lê SSE do OpenAI/OpenRouter token a token e imprime progresso em tempo real."""
    accumulated: list[str] = []
    char_count = 0
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").rstrip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
            delta = ((chunk.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
            if delta:
                accumulated.append(delta)
                char_count += len(delta)
                print(f"\r  ✍  Gerando... {char_count} chars", end="", flush=True)
        except (json.JSONDecodeError, IndexError, TypeError):
            pass
    if char_count:
        print(f"\r  ✅ Gerado: {char_count} chars{'':<20}", flush=True)
    return "".join(accumulated)


def _read_anthropic_stream(response) -> str:
    """Lê SSE da Anthropic token a token e imprime progresso em tempo real."""
    accumulated: list[str] = []
    char_count = 0
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").rstrip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        try:
            chunk = json.loads(data_str)
            if chunk.get("type") == "content_block_delta":
                delta = (chunk.get("delta") or {}).get("text") or ""
                if delta:
                    accumulated.append(delta)
                    char_count += len(delta)
                    print(f"\r  ✍  Gerando... {char_count} chars", end="", flush=True)
        except (json.JSONDecodeError, TypeError):
            pass
    if char_count:
        print(f"\r  ✅ Gerado: {char_count} chars{'':<20}", flush=True)
    return "".join(accumulated)


def _read_gemini_response(response) -> str:
    """Lê resposta completa do Gemini e extrai texto."""
    raw = response.read().decode("utf-8")
    data = json.loads(raw)
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        text = ""
    if text:
        print(f"  ✅ Gerado: {len(text)} chars", flush=True)
    return text


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
            "responseSchema": schema,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return execute_llm_request(request, _read_gemini_response)


def call_anthropic_json(api_key: str, model: str, prompt: str, schema: dict) -> dict:
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 8192,
        "stream": True,
        "system": f"Você gera análises SysDoc em JSON estrito, sem Markdown e sem texto fora do JSON. Responda exclusivamente com o JSON válido para este schema: {json.dumps(schema)}",
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    return execute_llm_request(request, _read_anthropic_stream)


def execute_llm_request(request: urllib.request.Request, response_reader, max_retries: int = 3) -> dict:
    """Executa a requisição HTTP com retry + backoff exponencial para erros 429/5xx."""
    delay = 5.0
    text = ""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  ⏳ Conectando... (tentativa {attempt}/{max_retries})", flush=True)
            with urllib.request.urlopen(request, timeout=900) as response:
                text = response_reader(response)
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                print(f"  ⚠️  Erro {exc.code} — aguardando {delay:.0f}s antes de tentar novamente...")
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"Erro da API ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries:
                print(f"  ⚠️  Falha de rede — aguardando {delay:.0f}s...")
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"Falha de rede: {exc}") from exc
    if not text:
        raise RuntimeError("Resposta da LLM sem texto utilizável.")
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


def init_command(project: str) -> int:
    """Cria a estrutura base de um projeto SysDoc (U7)."""
    template = ROOT / "templates" / "projeto-padrao"
    dest = (Path.cwd() / project).resolve()
    if dest.exists() and any(dest.iterdir()):
        answer = input(f"A pasta '{project}' já existe e não está vazia. Continuar mesmo assim? [s/N] ").strip().lower()
        if answer not in ("s", "sim", "y", "yes"):
            print("Operação cancelada.")
            return 1
    if template.exists():
        shutil.copytree(template, dest, dirs_ok=True)
        print(f"Projeto criado a partir do template: {dest}")
    else:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "modelos").mkdir(exist_ok=True)
        (dest / "README.md").write_text(
            f"# {project}\n\nCopie ETP.pdf e TR.pdf para esta pasta, adicione referências em modelos/ e rode:\n\n```bash\nsysdoc analyze {project}\n```\n",
            encoding="utf-8",
        )
        print(f"Estrutura básica criada em: {dest}")
    print(f"  Próximo passo: copie ETP.pdf e TR.pdf para {dest}")
    return 0


def extract_date(value: str) -> str:
    text = str(value or "")
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return datetime.now().strftime("%Y-%m-%d")


def compare(project: str) -> int:
    """Lista JSONs versionados de um projeto e compara itens, classificações e riscos (M3-C)."""
    paths = project_paths(project)
    jsons = sorted(paths.root.glob("dados_consolidados_*.json"))
    if not jsons:
        print("Nenhuma versão encontrada. Rode 'sysdoc publish' para versionar.")
        return 1
    header = f"{'ARQUIVO':<50} {'MODELO':<28} {'DATA':<12} {'ITENS':>6} {'BLOQ':>6} {'RELEV':>6}"
    print(header)
    print("-" * len(header))
    for json_file in jsons:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  {json_file.name}: erro ao ler — {exc}")
            continue
        itens = data.get("itens", [])
        modelo = str(data.get("modelo_ia", "?"))[:28]
        data_a = str(data.get("data_análise", "?"))[:12]
        bloq = sum(1 for i in itens if i.get("risco_jurídico") == "bloqueante")
        relev = sum(1 for i in itens if i.get("risco_jurídico") == "relevante")
        name = json_file.name[:50]
        print(f"{name:<50} {modelo:<28} {data_a:<12} {len(itens):>6} {bloq:>6} {relev:>6}")
    return 0


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
    init_parser = sub.add_parser("init", help="Cria a estrutura de um novo projeto SysDoc.")
    init_parser.add_argument("project", help="Nome da pasta do novo projeto.")
    analyze_parser = sub.add_parser("analyze", help="Prepara, chama a LLM configurada, valida e publica.")
    analyze_parser.add_argument("project", help="Pasta do projeto SysDoc.")
    analyze_parser.add_argument("--model", default=None, help="Modelo a usar (ex: anthropic/claude-3.7-sonnet, openai/gpt-4o). Padrão: lido do config.")
    analyze_parser.add_argument("--instruction", default=None, help="Instrucao extra para a analise.")
    analyze_parser.add_argument("--dry-run", action="store_true", help="Prepara o contexto e exibe o prompt sem chamar a LLM.")

    compare_parser = sub.add_parser("compare", help="Compara versões de análise de um projeto.")
    compare_parser.add_argument("project", help="Pasta do projeto SysDoc.")

    for command in ("prepare", "validate", "render", "publish"):
        item = sub.add_parser(command, help=f"Executa {command} em um projeto.")
        item.add_argument("project", help="Pasta do projeto SysDoc.")
    parser.add_argument("--version", action="version", version=f"SysDoc {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "connect":
        return connect_command()
    if args.command == "models":
        return models_command()
    if args.command == "init":
        return init_command(args.project)
    if args.command == "status":
        return status()
    if args.command == "prepare":
        return prepare(args.project)
    if args.command == "validate":
        return validate(args.project)
    if args.command == "render":
        return render(args.project)
    if args.command == "analyze":
        return analyze(args.project, model=args.model, extra_instruction=args.instruction, dry_run=getattr(args, 'dry_run', False))
    if args.command == "publish":
        return publish(args.project)
    if args.command == "compare":
        return compare(args.project)
    parser.error("comando inválido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
