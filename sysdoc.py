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

VERSION = "1.2.0"

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
    config: Path


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
        config=root / ".sysdoc" / "config.yaml",
    )


def load_config(paths: ProjectPaths) -> dict:
    if not paths.config.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        data = yaml.safe_load(paths.config.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def init_config(project: str | Path) -> int:
    paths = project_paths(project)
    paths.config.parent.mkdir(parents=True, exist_ok=True)
    if paths.config.is_file():
        return 0
    content = (
        f"projeto: {paths.root.name}\n"
        f"vps_host: \"\"\n"
        f"vps_path: \"\"\n"
        f"modelo_ia_padrao: \"\"\n"
    )
    paths.config.write_text(content, encoding="utf-8")
    return 0


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


def analyze(project: str, instruction: str = "") -> int:
    paths = project_paths(project)
    if not paths.context.is_file():
        result = prepare(project)
        if result != 0:
            return result
    print(f"Contexto: {rel(paths.context)}")
    print(f"Textos extraídos: {rel(paths.source_cache)}")
    if paths.manifest.is_file():
        print(f"Manifest: {rel(paths.manifest)}")
    if instruction:
        print(f"Instrução adicional: {instruction}")
    print("")
    print("Próximo passo: o Agente de IA deve ler os arquivos acima,")
    print("gerar dados_consolidados.json e rodar 'sysdoc publish'.")
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



def render(project: str) -> int:
    paths = project_paths(project)
    json_path = paths.root / "dados_consolidados.json"
    if not json_path.is_file():
        raise SystemExit(f"JSON não encontrado: {rel(json_path)}")
    return run_python_script(["templates/render_analise.py", str(json_path), str(paths.root)])


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


def deploy(project: str) -> int:
    """Envia o último HTML gerado para a VPS garantindo índice único (index{X}.html)."""
    paths = project_paths(project)
    htmls = sorted(paths.root.glob("analise_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not htmls:
        print(f"Nenhum HTML encontrado em {rel(paths.root)}. Rode 'sysdoc publish' primeiro.")
        return 1

    latest_html = htmls[0]
    print(f"Iniciando deploy do arquivo: {rel(latest_html)}")

    config = load_config(paths)
    vps_host = (config.get("vps_host") or "").strip() or "root@76.13.170.15"
    vps_path = (config.get("vps_path") or "").strip() or "/opt/web/cfc-analise/html"

    print(f"Consultando {vps_host} via SSH para encontrar próximo índice disponível...")
    ssh_cmd = [
        "ssh", vps_host,
        f"idx=1; while [ -f {vps_path}/index${{idx}}.html ]; do idx=$((idx+1)); done; echo $idx"
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=True)
        next_idx = result.stdout.strip()
        if not next_idx.isdigit():
            print(f"Falha ao interpretar retorno do servidor: {next_idx}")
            return 1
    except subprocess.CalledProcessError as exc:
        print(f"Erro na conexão SSH: {exc.stderr}")
        return 1

    target_name = f"index{next_idx}.html"
    target_path = f"{vps_host}:{vps_path}/{target_name}"

    print(f"Enviando para {target_path} ...")
    scp_cmd = ["scp", str(latest_html), target_path]
    try:
        subprocess.run(scp_cmd, check=True)
        print("✅ Deploy concluído com sucesso!")
        return 0
    except subprocess.CalledProcessError:
        print("❌ Erro durante o envio SCP.")
        return 1


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
    init_config(dest)
    print(f"  Configuração: {rel(project_paths(dest).config)}")
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
    init_parser = sub.add_parser("init", help="Cria a estrutura de um novo projeto SysDoc.")
    init_parser.add_argument("project", help="Nome da pasta do novo projeto.")

    compare_parser = sub.add_parser("compare", help="Compara versões de análise de um projeto.")
    compare_parser.add_argument("project", help="Pasta do projeto SysDoc.")

    deploy_parser = sub.add_parser("deploy", help="Envia o último HTML gerado para a VPS por SSH.")
    deploy_parser.add_argument("project", help="Pasta do projeto SysDoc.")

    analyze_parser = sub.add_parser(
        "analyze",
        help="Prepara contexto e exibe instruções para análise por LLM do harness.",
    )
    analyze_parser.add_argument("project", help="Pasta do projeto SysDoc.")
    analyze_parser.add_argument(
        "--instruction", "-i",
        default="",
        help="Instrução extra para a LLM (foco temático, severidade, etc.).",
    )

    for command in ("prepare", "validate", "render", "publish"):
        item = sub.add_parser(command, help=f"Executa {command} em um projeto.")
        item.add_argument("project", help="Pasta do projeto SysDoc.")
    parser.add_argument("--version", action="version", version=f"SysDoc {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
    if args.command == "publish":
        return publish(args.project)
    if args.command == "deploy":
        return deploy(args.project)
    if args.command == "compare":
        return compare(args.project)
    if args.command == "analyze":
        return analyze(args.project, instruction=args.instruction)
    parser.error("comando inválido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
