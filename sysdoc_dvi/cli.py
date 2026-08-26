#!/usr/bin/env python3
"""
Entry point do motor de análise DVI (`sysdoc-dvi`).

Binário separado de `sysdoc` (D-01): concentra o fluxo de análise por
checklist (`run`, `relatorio`, `config`). A CLI `sysdoc` continua sem
qualquer chamada a modelo de linguagem; este entry point é quem chama.

Esqueleto nesta task: os três handlers ainda não implementam o pipeline
(planos seguintes desta fase preenchem `run`/`relatorio`/`config`).
"""

from __future__ import annotations

import argparse
import sys
import textwrap

from sysdoc_dvi import __version__

VERSION = __version__


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
    print("sysdoc-dvi run: não implementado")
    return 2


def relatorio(project: str) -> int:
    print("sysdoc-dvi relatorio: não implementado")
    return 2


def config(
    economico: str | None = None,
    forte: str | None = None,
    listar: bool = False,
) -> int:
    print("sysdoc-dvi config: não implementado")
    return 2


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
