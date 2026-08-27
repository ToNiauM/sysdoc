"""
Guarda permanente do contrato IA-agnóstico contra a interface web (Plano 07-08).

D-21 de `07-CONTEXT.md`: `README.md` e `CHANGELOG.md` registram a web para
humanos, mas `AGENTS.md`, `skills/sysdoc/SKILL.md` e os dois wrappers de
skill (`.claude/skills/sysdoc-analise/SKILL.md`,
`.opencode/skills/sysdoc-analise/SKILL.md`) **não** mudam de contrato — a web
não é um caminho para agentes de IA, e o fluxo canônico do agente continua
sendo o da CLI. Este módulo é só leitura de arquivo: sem Django, sem
`importorskip`, roda sempre.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TERMOS_WEB = re.compile(r"docker|django|localhost:8000|sysdoc_web", re.IGNORECASE)

_ARQUIVOS_CONTRATO_CANONICO = (
    ROOT / "skills" / "sysdoc" / "SKILL.md",
    ROOT / "AGENTS.md",
)

_ARQUIVOS_WRAPPERS = (
    ROOT / ".claude" / "skills" / "sysdoc-analise" / "SKILL.md",
    ROOT / ".opencode" / "skills" / "sysdoc-analise" / "SKILL.md",
)


def _ocorrencias_de_termos_web(caminho: Path) -> list[str]:
    texto = caminho.read_text(encoding="utf-8")
    ocorrencias = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        achado = _TERMOS_WEB.search(linha)
        if achado:
            ocorrencias.append(f"{caminho.relative_to(ROOT)}:{numero}: {achado.group(0)!r} -> {linha.strip()!r}")
    return ocorrencias


class TestContratoIaAgnostico:
    def test_skill_canonica_nao_menciona_a_web(self):
        skill = ROOT / "skills" / "sysdoc" / "SKILL.md"
        ocorrencias = _ocorrencias_de_termos_web(skill)
        assert not ocorrencias, (
            "skills/sysdoc/SKILL.md não pode mencionar a web (D-21):\n" + "\n".join(ocorrencias)
        )

    def test_agents_md_nao_menciona_a_web(self):
        agents = ROOT / "AGENTS.md"
        ocorrencias = _ocorrencias_de_termos_web(agents)
        assert not ocorrencias, (
            "AGENTS.md não pode mencionar a web (D-21):\n" + "\n".join(ocorrencias)
        )

    def test_wrappers_de_skill_nao_mencionam_a_web(self):
        ocorrencias = []
        for wrapper in _ARQUIVOS_WRAPPERS:
            ocorrencias.extend(_ocorrencias_de_termos_web(wrapper))
        assert not ocorrencias, (
            "Wrappers de skill não podem mencionar a web (D-21):\n" + "\n".join(ocorrencias)
        )

    def test_readme_registra_a_web(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "docker compose up" in readme
        assert "createsuperuser" in readme

    def test_changelog_registra_a_web(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "sysdoc_web" in changelog
        assert "1.6.0" in changelog

    def test_django_fora_das_dependencias_base(self):
        import tomllib

        with (ROOT / "pyproject.toml").open("rb") as arquivo:
            dados = tomllib.load(arquivo)

        dependencias = dados["project"]["dependencies"]
        assert not any("django" in dependencia.lower() for dependencia in dependencias), (
            "django não pode constar em [project.dependencies] — deve permanecer "
            "só em [project.optional-dependencies].web"
        )
