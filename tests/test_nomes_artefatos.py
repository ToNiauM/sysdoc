"""
Testes do padrão de nomes de artefatos xx_nome_tipo_data.extensao (D-08/D-09).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402


class TestContador:
    def test_primeiro_nome_usa_contador_01(self, tmp_path):
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2026-08-26", ".docx")
        assert resultado.name == "01_processo-042_dvi_2026-08-26.docx"

    def test_incrementa_apos_arquivo_existente(self, tmp_path):
        (tmp_path / "01_processo-042_dvi_2026-08-26.docx").write_text("x", encoding="utf-8")
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2026-08-27", ".docx")
        assert resultado.name == "02_processo-042_dvi_2026-08-27.docx"

    def test_nunca_sobrescreve_nem_reutiliza(self, tmp_path):
        primeiro = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2026-08-26", ".docx")
        primeiro.write_text("v1", encoding="utf-8")
        segundo = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2026-08-26", ".docx")
        assert segundo != primeiro
        segundo.write_text("v2", encoding="utf-8")
        terceiro = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2026-08-26", ".docx")
        assert terceiro.name == "03_processo-042_dvi_2026-08-26.docx"

    def test_contador_e_por_tipo(self, tmp_path):
        (tmp_path / "01_processo-042_dvi_2026-08-26.docx").write_text("x", encoding="utf-8")
        (tmp_path / "02_processo-042_dvi_2026-08-27.docx").write_text("x", encoding="utf-8")
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "relatorio", "2026-08-27", ".docx")
        assert resultado.name == "01_processo-042_relatorio_2026-08-27.docx"

    def test_contador_ignora_data(self, tmp_path):
        (tmp_path / "01_processo-042_dvi_2026-01-01.docx").write_text("x", encoding="utf-8")
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2099-12-31", ".docx")
        assert resultado.name == "02_processo-042_dvi_2099-12-31.docx"

    def test_imune_a_nomes_legados(self, tmp_path):
        (tmp_path / "analise_gpt-5_2026-01-01.html").write_text("x", encoding="utf-8")
        (tmp_path / "dados_consolidados_gpt-5_2026-01-01.json").write_text("{}", encoding="utf-8")
        (tmp_path / "tr_gpt-5_2026-01-01.docx").write_text("x", encoding="utf-8")
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "analise", "2026-08-26", ".html")
        assert resultado.name == "01_processo-042_analise_2026-08-26.html"

    def test_diretorio_inexistente_comeca_em_01(self, tmp_path):
        destino = tmp_path / "nao-existe"
        resultado = sysdoc.proximo_nome_artefato(destino, "Processo 042", "dvi", "2026-08-26", ".docx")
        assert resultado.name == "01_processo-042_dvi_2026-08-26.docx"


class TestSlugProjeto:
    def test_slug_remove_acentos_e_espacos(self, tmp_path):
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Análise Técnica", "relatorio", "2026-08-26", ".docx")
        assert resultado.name == "01_analise-tecnica_relatorio_2026-08-26.docx"

    def test_slug_processo_com_numero(self, tmp_path):
        resultado = sysdoc.proximo_nome_artefato(tmp_path, "Processo 042", "dvi", "2026-08-26", ".docx")
        assert "processo-042" in resultado.name

    def test_slug_e_consistente_entre_chamadas(self, tmp_path):
        primeiro = sysdoc.proximo_nome_artefato(tmp_path, "Análise Técnica", "relatorio", "2026-08-26", ".docx")
        primeiro.write_text("x", encoding="utf-8")
        segundo = sysdoc.proximo_nome_artefato(tmp_path, "Análise Técnica", "relatorio", "2026-08-27", ".docx")
        assert segundo.name == "02_analise-tecnica_relatorio_2026-08-27.docx"


class TestRendererNome:
    RENDER_SCRIPT = ROOT / "templates" / "render_analise.py"

    def _dados_minimos(self) -> dict:
        return {
            "titulo": "t", "subtitulo": "s", "modelo_ia": "gpt-5",
            "data_análise": "2026-08-26", "projeto": {"objeto": "Objeto"},
            "metadados": [], "documentos_analisados": [], "parecer_executivo": "x",
            "secao_etp": {}, "secao_tr": {}, "itens": [], "nota_integridade": "x",
        }

    def _render(self, json_path: Path, projeto_dir: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.RENDER_SCRIPT), str(json_path), str(projeto_dir)],
            capture_output=True,
            text=True,
        )

    def test_deriva_projeto_da_pasta_output(self, tmp_path):
        project_dir = tmp_path / "MeuProjeto"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True)
        json_path = tmp_path / "dados.json"
        json_path.write_text(json.dumps(self._dados_minimos(), ensure_ascii=False), encoding="utf-8")

        result = self._render(json_path, output_dir)

        assert result.returncode == 0, result.stderr
        arquivos = list(output_dir.iterdir())
        assert len(arquivos) == 1
        assert arquivos[0].name == "01_meuprojeto_analise_2026-08-26.html"

    def test_deriva_projeto_da_raiz(self, tmp_path):
        project_dir = tmp_path / "OutraPasta"
        project_dir.mkdir()
        json_path = tmp_path / "dados.json"
        json_path.write_text(json.dumps(self._dados_minimos(), ensure_ascii=False), encoding="utf-8")

        result = self._render(json_path, project_dir)

        assert result.returncode == 0, result.stderr
        arquivos = list(project_dir.iterdir())
        nomes = [p.name for p in arquivos if p.name != "dados.json"]
        assert nomes == ["01_outrapasta_analise_2026-08-26.html"]

    def test_duas_renderizacoes_incrementam(self, tmp_path):
        project_dir = tmp_path / "MeuProjeto"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True)
        json_path = tmp_path / "dados.json"
        json_path.write_text(json.dumps(self._dados_minimos(), ensure_ascii=False), encoding="utf-8")

        self._render(json_path, output_dir)
        self._render(json_path, output_dir)

        nomes = sorted(p.name for p in output_dir.iterdir())
        assert nomes == [
            "01_meuprojeto_analise_2026-08-26.html",
            "02_meuprojeto_analise_2026-08-26.html",
        ]

    def test_modelo_ia_nao_aparece_no_nome(self, tmp_path):
        project_dir = tmp_path / "MeuProjeto"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True)
        json_path = tmp_path / "dados.json"
        json_path.write_text(json.dumps(self._dados_minimos(), ensure_ascii=False), encoding="utf-8")

        self._render(json_path, output_dir)

        nome = next(output_dir.iterdir()).name
        assert "gpt-5" not in nome


class TestCompatibilidadeGlobs:
    def _make_project(self, tmp_path, name="ProjetoGlobs"):
        project_dir = tmp_path / name
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True)
        return project_dir, output_dir

    def test_status_conta_legado_e_novo(self, tmp_path, monkeypatch, capsys):
        project_dir, output_dir = self._make_project(tmp_path)
        (output_dir / "analise_gpt-5_2026-01-01.html").write_text("legado", encoding="utf-8")
        (output_dir / "01_projetoglobs_analise_2026-08-26.html").write_text("novo", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.status()

        assert rc == 0
        captured = capsys.readouterr()
        linhas = [linha for linha in captured.out.splitlines() if linha.startswith("ProjetoGlobs")]
        assert len(linhas) == 1
        colunas = linhas[0].split()
        assert colunas[0] == "ProjetoGlobs"
        assert colunas[-2] == "2"

    def test_deploy_seleciona_mais_recente_entre_padroes(self, tmp_path, monkeypatch):
        project_dir, output_dir = self._make_project(tmp_path)
        legado = output_dir / "analise_gpt-5_2026-01-01.html"
        novo = output_dir / "01_projetoglobs_analise_2026-08-26.html"
        legado.write_text("legado", encoding="utf-8")
        novo.write_text("novo", encoding="utf-8")
        agora = time.time()
        os.utime(legado, (agora - 100, agora - 100))
        os.utime(novo, (agora, agora))

        calls: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = "1"
            stderr = ""

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return FakeResult()

        monkeypatch.setattr(sysdoc.subprocess, "run", fake_run)
        monkeypatch.chdir(tmp_path)

        rc = sysdoc.deploy("ProjetoGlobs")

        assert rc == 0
        assert calls, "subprocess.run deveria ter sido chamado (ssh + scp)"
        scp_call = calls[-1]
        assert str(novo) in scp_call
        assert str(legado) not in scp_call

    def test_compare_le_padrao_legado_e_novo(self, tmp_path, monkeypatch, capsys):
        project_dir, output_dir = self._make_project(tmp_path)
        legado = output_dir / "dados_consolidados_gpt-5_2026-01-01.json"
        novo = output_dir / "01_projetoglobs_dados_2026-08-26.json"
        legado.write_text(
            json.dumps({"modelo_ia": "gpt-5", "data_análise": "2026-01-01", "itens": []}),
            encoding="utf-8",
        )
        novo.write_text(
            json.dumps({"modelo_ia": "gpt-5", "data_análise": "2026-08-26", "itens": []}),
            encoding="utf-8",
        )

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.compare("ProjetoGlobs")

        assert rc == 0
        captured = capsys.readouterr()
        assert legado.name in captured.out
        assert novo.name in captured.out
