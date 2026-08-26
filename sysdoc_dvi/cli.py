#!/usr/bin/env python3
"""
Entry point do motor de análise DVI (`sysdoc-dvi`).

Binário separado de `sysdoc` (D-01): concentra o fluxo de análise por
checklist (`run`, `relatorio`, `config`). A CLI `sysdoc` continua sem
qualquer chamada a modelo de linguagem; este entry point é quem chama.

`run` delega a `sysdoc_dvi.pipeline.executar_run`; `relatorio` reimprime o
último relatório de execução gravado em `output/` sem reexecutar nada;
`config` grava/lista o mapeamento de modelos econômico/forte em
`~/.sysdoc/config.json` (seção `dvi`), sempre com permissão restrita
(diretório 0700, arquivo 0600) e sem nunca ecoar uma chave de API (T-05-46).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

from sysdoc_dvi import __version__
from sysdoc_dvi.config import PROVEDORES_VALIDOS

VERSION = __version__

_VAR_AMBIENTE_POR_PROVEDOR = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysdoc-dvi",
        description="Motor de análise DVI por checklist tipado e data-driven.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Exemplos:
              sysdoc-dvi run .
              sysdoc-dvi run Processo042 --tipo tic --forte
              sysdoc-dvi relatorio Processo042
              sysdoc-dvi config --listar
            """
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser(
        "run",
        help="Executa o pipeline de análise DVI sobre um projeto.",
    )
    run_parser.add_argument("project", nargs="?", default=".", help="Pasta do projeto SysDoc.")
    run_parser.add_argument(
        "--tipo",
        choices=["geral", "tic"],
        help="Aplicabilidade da análise (sobrepõe .sysdoc/config.yaml).",
    )
    run_parser.add_argument(
        "--checklist",
        help="Caminho para um checklist YAML alternativo (padrão: checklists/dvi.yaml).",
    )
    run_parser.add_argument(
        "--economico",
        help="Provedor/modelo econômico a usar (sobrepõe ~/.sysdoc/config.json).",
    )
    run_parser.add_argument(
        "--forte",
        help="Provedor/modelo forte a usar (sobrepõe ~/.sysdoc/config.json).",
    )
    run_parser.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        default=True,
        help="Retoma execução a partir do checkpoint em .sysdoc/cache/ (padrão).",
    )
    run_parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Ignora checkpoint existente e reinicia a análise do zero.",
    )

    relatorio_parser = sub.add_parser(
        "relatorio",
        help="Exibe o relatório de execução da última análise DVI do projeto.",
    )
    relatorio_parser.add_argument("project", nargs="?", default=".", help="Pasta do projeto SysDoc.")

    config_parser = sub.add_parser(
        "config",
        help="Mostra ou atualiza o mapeamento de modelos econômico/forte.",
    )
    config_parser.add_argument(
        "--economico",
        help="Define o provedor/modelo econômico padrão (ex.: openrouter/deepseek-chat).",
    )
    config_parser.add_argument(
        "--forte",
        help="Define o provedor/modelo forte padrão (ex.: anthropic/claude-opus-5).",
    )
    config_parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista o mapeamento de modelos configurado.",
    )

    parser.add_argument("--version", action="version", version=f"SysDoc DVI {VERSION}")
    return parser


def run(
    project: str,
    tipo: str | None = None,
    checklist: str | None = None,
    economico: str | None = None,
    forte: str | None = None,
    resume: bool = True,
) -> int:
    from sysdoc_dvi.pipeline import executar_run

    return executar_run(
        project,
        tipo=tipo,
        checklist=checklist,
        economico=economico,
        forte=forte,
        retomar=resume,
    )


def _config_path_padrao() -> Path:
    return Path.home() / ".sysdoc" / "config.json"


def _ultimo_relatorio(project: str) -> Path | None:
    import sysdoc

    paths = sysdoc.project_paths(project)
    candidatos = sorted(
        paths.output.glob("*_relatorio_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidatos[0] if candidatos else None


def relatorio(project: str) -> int:
    caminho = _ultimo_relatorio(project)
    if caminho is None:
        print(
            f"Nenhum relatório encontrado para '{project}'. "
            f"Rode 'sysdoc-dvi run {project}' primeiro."
        )
        return 1

    from sysdoc_dvi.relatorio import renderizar_relatorio

    dados = json.loads(caminho.read_text(encoding="utf-8"))
    print(renderizar_relatorio(dados, project))
    print(f"Relatório lido de: {caminho}")
    return 0


def config(
    economico: str | None = None,
    forte: str | None = None,
    listar: bool = False,
) -> int:
    path = _config_path_padrao()
    dados: dict = {}
    if path.is_file():
        try:
            conteudo = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"não foi possível ler {path}: {exc}")
            return 1
        if isinstance(conteudo, dict):
            dados = conteudo

    if listar:
        secao_dvi = dados.get("dvi") if isinstance(dados.get("dvi"), dict) else {}
        api_keys = dados.get("api_keys") if isinstance(dados.get("api_keys"), dict) else {}
        print(f"Configuração de modelos em {path}:")
        print(f"  econômico: {secao_dvi.get('economico') or '<não definido>'}")
        print(f"  forte: {secao_dvi.get('forte') or '<não definido>'}")
        print("  chaves de API:")
        for provedor in PROVEDORES_VALIDOS:
            var_ambiente = _VAR_AMBIENTE_POR_PROVEDOR[provedor]
            presente = bool(api_keys.get(provedor)) or bool(os.environ.get(var_ambiente))
            print(f"    - {provedor}: {'configurada' if presente else 'ausente'}")
        return 0

    if economico is None and forte is None:
        print(
            "Nada para atualizar: use --economico/--forte para definir o mapeamento "
            "ou --listar para consultar o que já está configurado."
        )
        return 1

    secao_dvi = dict(dados.get("dvi") or {})
    if economico:
        secao_dvi["economico"] = economico
    if forte:
        secao_dvi["forte"] = forte
    dados["dvi"] = secao_dvi

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

    print(f"Configuração de modelos gravada em {path}.")
    print(f"  econômico: {secao_dvi.get('economico') or '<mantido>'}")
    print(f"  forte: {secao_dvi.get('forte') or '<mantido>'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(
            args.project,
            tipo=args.tipo,
            checklist=args.checklist,
            economico=args.economico,
            forte=args.forte,
            resume=args.resume,
        )
    if args.command == "relatorio":
        return relatorio(args.project)
    if args.command == "config":
        return config(economico=args.economico, forte=args.forte, listar=args.listar)
    parser.error("comando inválido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
