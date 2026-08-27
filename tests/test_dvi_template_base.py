"""
Testes da semeadura de template DVI por `sysdoc init` (P6 - 260826-o2d).

`templates/dvi_base.docx` e `templates/build_dvi_base.py` (o antigo formato
relatório) foram aposentados no Plano 07 da Rodada 1 desta fase — decisão do
usuário registrada em `CHANGELOG.md`. `sysdoc init` semeia hoje a variante
correspondente de `templates/dvi/` (`despacho_geral.docx`/`despacho_tic.docx`,
Plano 05), e é essa semeadura que este módulo continua cobrindo.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sysdoc  # noqa: E402

TEMPLATE_DESPACHO_GERAL = ROOT / "templates" / "dvi" / "despacho_geral.docx"


class TestSeedDviTemplate:
    def test_init_cria_referencias_dvi_docx_byte_identico(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_command("ProjetoSemente")
        assert rc == 0

        destino = tmp_path / "ProjetoSemente" / "referencias" / "dvi.docx"
        assert destino.is_file()
        # 06-05 (D-14): a semeadura passou a usar as variantes de
        # templates/dvi/, não mais templates/dvi_base.docx (formato
        # relatório aposentado por esta rodada).
        assert destino.read_bytes() == TEMPLATE_DESPACHO_GERAL.read_bytes()

    def test_init_nao_sobrescreve_quando_rodado_duas_vezes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoDuplicado")
        destino = tmp_path / "ProjetoDuplicado" / "referencias" / "dvi.docx"
        destino.write_bytes(b"conteudo customizado do usuario")

        rc = sysdoc.init_command("ProjetoDuplicado")
        assert rc == 0
        assert destino.read_bytes() == b"conteudo customizado do usuario"

    def test_init_nao_sobrescreve_modelo_dvi_ja_presente(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoComModeloProprio"
        refs = project_dir / "referencias"
        refs.mkdir(parents=True)
        (refs / "modelo_dvi.docx").write_bytes(b"modelo institucional do usuario")

        monkeypatch.chdir(tmp_path)
        rc = sysdoc.init_command("ProjetoComModeloProprio")
        assert rc == 0

        assert (refs / "modelo_dvi.docx").read_bytes() == b"modelo institucional do usuario"
        assert not (refs / "dvi.docx").is_file()

    def test_seed_dvi_template_devolve_none_quando_ja_existe(self, tmp_path):
        paths = sysdoc.project_paths(tmp_path / "ProjetoDireto")
        paths.referencias.mkdir(parents=True)
        (paths.referencias / "dvi.docx").write_bytes(b"ja existe")

        resultado = sysdoc.seed_dvi_template(paths)
        assert resultado is None
        assert (paths.referencias / "dvi.docx").read_bytes() == b"ja existe"
