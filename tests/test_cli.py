"""
Testes do CLI do SysDoc (analyze, init_config, ProjectPaths.config).
"""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
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
        (project_dir / "documentos").mkdir()

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
        (project_dir / "documentos").mkdir()
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
        (project_dir / "documentos").mkdir()
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

    def test_init_command_existing_nonempty_is_idempotent(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoExistente"
        project_dir.mkdir()
        marker = project_dir / "arquivo_usuario.txt"
        marker.write_text("não sobrescrever\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_command("ProjetoExistente")

        assert rc == 0
        assert marker.read_text(encoding="utf-8") == "não sobrescrever\n"
        assert (project_dir / "documentos").is_dir()
        assert (project_dir / "referencias").is_dir()
        assert (project_dir / "output").is_dir()
        assert (project_dir / ".sysdoc" / "config.yaml").is_file()

    def test_init_command_current_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_command(".")

        assert rc == 0
        assert (tmp_path / "documentos").is_dir()
        assert (tmp_path / "referencias").is_dir()
        assert (tmp_path / "output").is_dir()
        assert (tmp_path / ".sysdoc" / "config.yaml").is_file()


class TestAllCommand:
    def test_all_initializes_and_prepares_project(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoAll"
        called: list[str] = []

        def fake_prepare(project: str) -> int:
            called.append(project)
            paths = sysdoc.project_paths(project)
            paths.source_cache.mkdir(parents=True, exist_ok=True)
            paths.context.write_text("# contexto fake\n", encoding="utf-8")
            return 0

        monkeypatch.setattr(sysdoc, "prepare", fake_prepare)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.all_command("ProjetoAll", instruction="foco em preço")

        assert rc == 0
        assert Path(called[0]) == project_dir.resolve()
        assert (project_dir / "documentos").is_dir()
        assert (project_dir / "referencias").is_dir()
        assert (project_dir / "output").is_dir()
        assert (project_dir / ".sysdoc" / "config.yaml").is_file()
        assert (project_dir / ".sysdoc" / "cache" / "contexto_sysdoc.md").is_file()


class TestConfigCommand:
    def test_config_updates_vps_fields(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoConfigCli"

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.config_command(
            "ProjetoConfigCli",
            vps_host="root@exemplo",
            vps_path="/var/www/sysdoc",
            modelo_ia_padrao="gpt-5",
        )

        assert rc == 0
        config_file = project_dir / ".sysdoc" / "config.yaml"
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["vps_host"] == "root@exemplo"
        assert data["vps_path"] == "/var/www/sysdoc"
        assert data["modelo_ia_padrao"] == "gpt-5"

    def test_config_cli_accepts_short_vps_and_path_flags(self, tmp_path):
        project_dir = tmp_path / "ProjetoConfigCurto"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "sysdoc.py"),
                "config",
                "--vps",
                "root@exemplo",
                "--path",
                "/var/www/sysdoc",
                str(project_dir),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert result.returncode == 0
        data = yaml.safe_load((project_dir / ".sysdoc" / "config.yaml").read_text(encoding="utf-8"))
        assert data["vps_host"] == "root@exemplo"
        assert data["vps_path"] == "/var/www/sysdoc"


class TestProjectPaths:
    def test_project_paths_includes_config(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoPaths"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        paths = sysdoc.project_paths("ProjetoPaths")
        assert hasattr(paths, "config")
        assert hasattr(paths, "documentos")
        assert hasattr(paths, "referencias")
        assert hasattr(paths, "output")
        assert paths.config.name == "config.yaml"
        assert paths.config.parent.name == ".sysdoc"


class TestPrepareStructure:
    def test_prepare_extracts_documents_and_references(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoPrepare"
        docs = project_dir / "documentos"
        refs = project_dir / "referencias"
        docs.mkdir(parents=True)
        refs.mkdir()
        (docs / "TR.txt").write_text("1 Objeto\nContratação de serviço continuado.", encoding="utf-8")
        (refs / "modelo.txt").write_text("Referência de garantia e pagamento.", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.prepare("ProjetoPrepare")

        assert rc == 0
        assert (project_dir / ".sysdoc" / "cache" / "textos" / "documentos" / "TR.txt").is_file()
        assert (project_dir / ".sysdoc" / "cache" / "textos" / "referencias" / "REF-01_modelo.txt").is_file()
        manifest = (project_dir / ".sysdoc" / "cache" / "manifest.json").read_text(encoding="utf-8")
        assert '"category": "documentos"' in manifest
        assert '"category": "referencias"' in manifest


class TestRenderAndCreate:
    def test_create_command_help(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "sysdoc.py"), "create", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0
        assert "create" in result.stdout.lower()
        assert "--tipo" in result.stdout

    def test_create_defaults_to_tr_for_project(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoDefaultTR"
        project_dir.mkdir()
        captured: dict[str, str | None] = {}

        def fake_create(project: str, tipo: str, json_arg: str | None = None, template_arg: str | None = None) -> int:
            captured["project"] = project
            captured["tipo"] = tipo
            captured["json_arg"] = json_arg
            captured["template_arg"] = template_arg
            return 0

        monkeypatch.setattr(sysdoc, "create", fake_create)

        rc = sysdoc.main(["create", str(project_dir)])

        assert rc == 0
        assert captured == {
            "project": str(project_dir),
            "tipo": "tr",
            "json_arg": None,
            "template_arg": None,
        }

    def test_create_tipo_flag_overrides_positional_type(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoTipoFlag"
        project_dir.mkdir()
        captured: dict[str, str | None] = {}

        def fake_create(project: str, tipo: str, json_arg: str | None = None, template_arg: str | None = None) -> int:
            captured["project"] = project
            captured["tipo"] = tipo
            captured["json_arg"] = json_arg
            captured["template_arg"] = template_arg
            return 0

        monkeypatch.setattr(sysdoc, "create", fake_create)

        rc = sysdoc.main(["create", str(project_dir), "documento", "--tipo", "tr"])

        assert rc == 0
        assert captured["project"] == str(project_dir)
        assert captured["tipo"] == "tr"

    def test_render_uses_output_directory_and_json_override(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoRender"
        project_dir.mkdir()
        json_file = project_dir / "custom.json"
        json_file.write_text("{}", encoding="utf-8")
        calls: list[list[str]] = []

        def fake_run(args: list[str]) -> int:
            calls.append(args)
            return 0

        monkeypatch.setattr(sysdoc, "run_python_script", fake_run)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.render("ProjetoRender", json_arg=str(json_file))

        assert rc == 0
        assert (project_dir / "output").is_dir()
        assert calls[0][-1] == str(project_dir / "output")

    def test_create_fills_docx_placeholders(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoCreate"
        refs = project_dir / "referencias"
        refs.mkdir(parents=True)
        json_file = project_dir / "dados_consolidados.json"
        json_file.write_text(
            '{"modelo_ia":"gpt-5","data_análise":"2026-05-12","projeto":{"objeto":"Objeto teste"}}',
            encoding="utf-8",
        )
        template = refs / "modelo_tr.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("word/document.xml", "<w:document>{{projeto.objeto}}</w:document>")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoCreate", "tr")

        assert rc == 0
        output = project_dir / "tr_gpt-5_2026-05-12.docx"
        assert output.is_file()
        with zipfile.ZipFile(output) as zf:
            assert "Objeto teste" in zf.read("word/document.xml").decode("utf-8")

    def test_create_tr_applies_etp_revisions(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoTR"
        refs = project_dir / "referencias"
        cache = project_dir / ".sysdoc" / "cache" / "textos"
        refs.mkdir(parents=True)
        cache.mkdir(parents=True)

        json_file = project_dir / "dados_consolidados.json"
        json_file.write_text(
            json.dumps({
                "modelo_ia": "gpt-5",
                "data_análise": "2026-05-12",
                "projeto": {"objeto": "Aquisição de combustível"},
                "itens": [
                    {
                        "id": "ETP-001",
                        "documento": "ETP",
                        "classificação": "ajuste_necessário",
                        "de": "cláusula antiga",
                        "para": "cláusula revisada",
                    }
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        (cache / "ETP.txt").write_text(
            "Texto inicial cláusula antiga texto final", encoding="utf-8"
        )

        template = refs / "modelo_compras.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr(
                "word/document.xml",
                "<w:document>{{corpo_etp}}</w:document>",
            )

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoTR", "tr")

        assert rc == 0
        output = project_dir / "tr_gpt-5_2026-05-12.docx"
        assert output.is_file()
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
            assert "cláusula revisada" in xml
            assert "cláusula antiga" not in xml

    def test_create_tr_reports_pending_substitution(self, tmp_path, monkeypatch, capsys):
        project_dir = tmp_path / "ProjetoPending"
        refs = project_dir / "referencias"
        cache = project_dir / ".sysdoc" / "cache" / "textos"
        refs.mkdir(parents=True)
        cache.mkdir(parents=True)

        json_file = project_dir / "dados_consolidados.json"
        json_file.write_text(
            json.dumps({
                "modelo_ia": "gpt-5",
                "data_análise": "2026-05-12",
                "projeto": {"objeto": "Serviço de limpeza"},
                "itens": [
                    {
                        "id": "ETP-001",
                        "documento": "ETP",
                        "classificação": "risco",
                        "de": "texto que não existe no ETP",
                        "para": "texto substituto",
                    }
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        (cache / "ETP.txt").write_text(
            "Texto do ETP sem correspondência", encoding="utf-8"
        )

        template = refs / "modelo_servicos.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr(
                "word/document.xml",
                "<w:document>{{substituicoes_pendentes}}</w:document>",
            )

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoPending", "tr")

        assert rc == 0
        captured = capsys.readouterr()
        assert "Substituições pendentes: 1" in captured.out
        output = project_dir / "tr_gpt-5_2026-05-12.docx"
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
            assert "ETP-001" in xml

    def test_create_tr_ignores_omission_markers(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoOmissao"
        refs = project_dir / "referencias"
        cache = project_dir / ".sysdoc" / "cache" / "textos"
        refs.mkdir(parents=True)
        cache.mkdir(parents=True)

        json_file = project_dir / "dados_consolidados.json"
        json_file.write_text(
            json.dumps({
                "modelo_ia": "gpt-5",
                "data_análise": "2026-05-12",
                "projeto": {"objeto": "Obra de reforma"},
                "itens": [
                    {
                        "id": "ETP-001",
                        "documento": "ETP",
                        "classificação": "ajuste_necessário",
                        "de": "[OMISSÃO] texto omitido",
                        "para": "texto preenchido",
                    }
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        (cache / "ETP.txt").write_text("ETP sem alteração", encoding="utf-8")

        template = refs / "modelo_obras.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr(
                "word/document.xml",
                "<w:document>{{corpo_etp}}</w:document>",
            )

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoOmissao", "tr")

        assert rc == 0
        output = project_dir / "tr_gpt-5_2026-05-12.docx"
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
            assert "ETP sem alteração" in xml

    def test_create_tr_missing_json_fails(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoNoJson"
        refs = project_dir / "referencias"
        refs.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            sysdoc.create("ProjetoNoJson", "tr")

    def test_create_tr_auto_prepare_when_etp_missing(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoAutoPrep"
        refs = project_dir / "referencias"
        docs = project_dir / "documentos"
        refs.mkdir(parents=True)
        docs.mkdir()

        json_file = project_dir / "dados_consolidados.json"
        json_file.write_text(
            json.dumps({
                "modelo_ia": "gpt-5",
                "data_análise": "2026-05-12",
                "projeto": {"objeto": "Aquisição de materiais"},
                "itens": [
                    {
                        "id": "ETP-001",
                        "documento": "ETP",
                        "classificação": "ajuste_necessário",
                        "de": "item antigo",
                        "para": "item novo",
                    }
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        (docs / "ETP.txt").write_text("Texto com item antigo final", encoding="utf-8")

        template = refs / "modelo_compras.docx"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr(
                "word/document.xml",
                "<w:document>{{corpo_etp}}</w:document>",
            )

        prepare_called: list[str] = []

        def fake_prepare(project: str) -> int:
            prepare_called.append(project)
            p = sysdoc.project_paths(project)
            p.source_cache.mkdir(parents=True, exist_ok=True)
            (p.source_cache / "ETP.txt").write_text(
                "Texto com item antigo final", encoding="utf-8"
            )
            return 0

        monkeypatch.setattr(sysdoc, "prepare", fake_prepare)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.create("ProjetoAutoPrep", "tr")

        assert rc == 0
        assert len(prepare_called) == 1

    def test_create_selects_compras_template(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoCompras"
        refs = project_dir / "referencias"
        refs.mkdir(parents=True)

        json_file = project_dir / "dados_consolidados.json"
        json_file.write_text(
            json.dumps({
                "modelo_ia": "gpt-5",
                "data_análise": "2026-05-12",
                "projeto": {"objeto": "Aquisição de materiais de escritório"},
                "itens": [],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        compras_tpl = refs / "modelo_compras.docx"
        with zipfile.ZipFile(compras_tpl, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("word/document.xml", "<w:document>COMPRAS {{projeto.objeto}}</w:document>")

        servicos_tpl = refs / "modelo_servicos.docx"
        with zipfile.ZipFile(servicos_tpl, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types></Types>")
            zf.writestr("word/document.xml", "<w:document>SERVICOS {{projeto.objeto}}</w:document>")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.create("ProjetoCompras", "tr")

        assert rc == 0
        output = project_dir / "tr_gpt-5_2026-05-12.docx"
        with zipfile.ZipFile(output) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
            assert "COMPRAS" in xml


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


class TestHandoffBox:
    def _make_paths(self, tmp_path: Path) -> sysdoc.ProjectPaths:
        project_dir = tmp_path / "ProjetoHandoff"
        project_dir.mkdir()
        (project_dir / "documentos").mkdir()
        return sysdoc.project_paths(str(project_dir))

    def test_handoff_box_states_no_analysis(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        paths = self._make_paths(tmp_path)
        output = sysdoc._render_handoff_box(paths)
        assert "NÃO executa análise" in output

    def test_handoff_box_lists_harnesses(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        paths = self._make_paths(tmp_path)
        output = sysdoc._render_handoff_box(paths)
        for harness in ("Claude Code", "OpenCode", "Codex", "Gemini"):
            assert harness in output, f"harness {harness!r} ausente do handoff"

    def test_handoff_box_shows_slash_command(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        paths = self._make_paths(tmp_path)
        output = sysdoc._render_handoff_box(paths)
        assert "/sysdoc analyze" in output

    def test_handoff_box_contains_paths(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        paths = self._make_paths(tmp_path)
        output = sysdoc._render_handoff_box(paths)
        assert sysdoc.rel(paths.cache) in output
        assert sysdoc.rel(paths.context) in output

    def test_handoff_with_instruction(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        paths = self._make_paths(tmp_path)
        output = sysdoc._render_handoff_box(paths, instruction="foco em garantia contratual")
        assert "foco em garantia contratual" in output
        assert "Instrução adicional" in output

    def test_handoff_box_does_not_mention_auto(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        paths = self._make_paths(tmp_path)
        output_lower = sysdoc._render_handoff_box(paths).lower()
        for forbidden in ("--auto", "openrouter", "api key", "autônomo", "autonomo"):
            assert forbidden not in output_lower, (
                f"princípio violado: handoff menciona {forbidden!r}"
            )


class TestAnalyzeDryRun:
    def test_analyze_dry_run_skips_prepare(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjDry"
        project_dir.mkdir()
        (project_dir / "documentos").mkdir()
        cache = project_dir / ".sysdoc" / "cache"
        cache.mkdir(parents=True)
        ctx = cache / "contexto_sysdoc.md"
        ctx.write_text("# original\n", encoding="utf-8")
        original_mtime = ctx.stat().st_mtime

        called: list[str] = []
        monkeypatch.setattr(sysdoc, "prepare", lambda p: called.append(p) or 0)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.analyze("ProjDry", dry_run=True)
        assert rc == 0
        assert called == [], "dry-run não deve chamar prepare"
        assert ctx.stat().st_mtime == original_mtime

    def test_analyze_dry_run_without_cache_fails(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjNoCache"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        called: list[str] = []
        monkeypatch.setattr(sysdoc, "prepare", lambda p: called.append(p) or 0)

        rc = sysdoc.analyze("ProjNoCache", dry_run=True)
        assert rc != 0
        assert called == [], "dry-run sem cache não deve chamar prepare"


class TestGuia:
    def test_guia_help(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "sysdoc.py"), "guia", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0
        assert "guia" in result.stdout.lower() or "project" in result.stdout.lower()

    def test_guia_non_tty_returns_1(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjGNonTty"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        class FakeStdin:
            def isatty(self) -> bool:
                return False

        monkeypatch.setattr(sys, "stdin", FakeStdin())
        input_calls: list = []
        monkeypatch.setattr("builtins.input", lambda *a, **kw: input_calls.append(a) or "")

        rc = sysdoc.guia("ProjGNonTty")
        assert rc == 1
        assert input_calls == [], "guia em não-TTY não deve chamar input"

    def test_guia_creates_roteiro(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjGRoteiro"
        project_dir.mkdir()
        docs = project_dir / "documentos"
        refs = project_dir / "referencias"
        docs.mkdir()
        refs.mkdir()
        (docs / "TR.txt").write_text("Objeto: contratação de serviço de apoio.", encoding="utf-8")

        class FakeStdin:
            def isatty(self) -> bool:
                return True

        monkeypatch.setattr(sys, "stdin", FakeStdin())
        responses = iter(["n", "1"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(responses))

        def fake_prepare(project: str) -> int:
            paths = sysdoc.project_paths(project)
            paths.source_cache.mkdir(parents=True, exist_ok=True)
            paths.context.write_text("# ctx fake\n", encoding="utf-8")
            return 0

        monkeypatch.setattr(sysdoc, "prepare", fake_prepare)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.guia("ProjGRoteiro")
        assert rc == 0
        roteiro = project_dir / ".sysdoc" / "cache" / "roteiro.txt"
        assert roteiro.is_file()
        content = roteiro.read_text(encoding="utf-8")
        assert "/sysdoc analyze" in content
        assert "Claude Code" in content

    def test_guia_missing_inputs(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjGFalta"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        class FakeStdin:
            def isatty(self) -> bool:
                return True

        monkeypatch.setattr(sys, "stdin", FakeStdin())
        monkeypatch.setattr("builtins.input", lambda *a, **kw: "")

        rc = sysdoc.guia("ProjGFalta")
        assert rc == 1
