"""
Testes do CLI do SysDoc (analyze, init_config, ProjectPaths.config).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402


class TestAnalyzeHelp:
    def test_analyze_command_help(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "sysdoc.py"), "analyze", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0
        assert "analyze" in result.stdout.lower() or "project" in result.stdout.lower()
        assert "--instruction" in result.stdout or "-i" in result.stdout


class TestAnalyzeBehavior:
    def test_analyze_runs_prepare(self, tmp_path, monkeypatch, capsys):
        project_dir = tmp_path / "Projeto1"
        project_dir.mkdir()
        (project_dir / "modelos").mkdir()

        called: list[str] = []

        def fake_prepare(project: str) -> int:
            called.append(project)
            paths = sysdoc.project_paths(project)
            paths.source_cache.mkdir(parents=True, exist_ok=True)
            paths.context.write_text("# contexto fake\n", encoding="utf-8")
            return 0

        monkeypatch.setattr(sysdoc, "prepare", fake_prepare)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.analyze("Projeto1")
        assert rc == 0
        assert called == ["Projeto1"], "analyze deveria invocar prepare quando cache não existe"

    def test_analyze_skips_prepare_when_cache_exists(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "Projeto2"
        project_dir.mkdir()
        (project_dir / "modelos").mkdir()
        cache = project_dir / ".sysdoc" / "cache"
        cache.mkdir(parents=True)
        (cache / "contexto_sysdoc.md").write_text("# já preparado\n", encoding="utf-8")

        called: list[str] = []
        monkeypatch.setattr(sysdoc, "prepare", lambda p: called.append(p) or 0)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.analyze("Projeto2")
        assert rc == 0
        assert called == [], "prepare não deve ser chamado quando contexto já existe"

    def test_analyze_with_instruction(self, tmp_path, monkeypatch, capsys):
        project_dir = tmp_path / "Projeto3"
        project_dir.mkdir()
        (project_dir / "modelos").mkdir()
        cache = project_dir / ".sysdoc" / "cache"
        cache.mkdir(parents=True)
        (cache / "contexto_sysdoc.md").write_text("# preparado\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.analyze("Projeto3", instruction="foco em garantia contratual")
        assert rc == 0
        captured = capsys.readouterr()
        assert "foco em garantia contratual" in captured.out


class TestInitConfig:
    def test_init_creates_config(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoConfig"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.init_config("ProjetoConfig")
        assert rc == 0

        config_file = project_dir / ".sysdoc" / "config.yaml"
        assert config_file.is_file()

    def test_init_config_does_not_overwrite(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoExistente"
        config_dir = project_dir / ".sysdoc"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        marker = "projeto: customizado\nvps_host: \"meu-host\"\n"
        config_file.write_text(marker, encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_config("ProjetoExistente")
        assert rc == 0
        assert config_file.read_text(encoding="utf-8") == marker


class TestProjectPaths:
    def test_project_paths_includes_config(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoPaths"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        paths = sysdoc.project_paths("ProjetoPaths")
        assert hasattr(paths, "config")
        assert paths.config.name == "config.yaml"
        assert paths.config.parent.name == ".sysdoc"


class TestConfigYamlFormat:
    def test_config_yaml_format(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoFmt"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        sysdoc.init_config("ProjetoFmt")
        config_file = project_dir / ".sysdoc" / "config.yaml"
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))

        assert isinstance(data, dict)
        assert "projeto" in data
        assert "vps_host" in data
        assert "vps_path" in data
        assert "modelo_ia_padrao" in data
        assert data["projeto"] == "ProjetoFmt"

    def test_load_config_returns_dict(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoLoad"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        sysdoc.init_config("ProjetoLoad")
        paths = sysdoc.project_paths("ProjetoLoad")
        config = sysdoc.load_config(paths)
        assert isinstance(config, dict)
        assert config.get("projeto") == "ProjetoLoad"

    def test_load_config_missing_returns_empty(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "SemConfig"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        paths = sysdoc.project_paths("SemConfig")
        config = sysdoc.load_config(paths)
        assert config == {}
