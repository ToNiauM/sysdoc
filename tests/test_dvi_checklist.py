"""
Testes do carregador de checklist DVI (sysdoc_dvi.checklist).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.checklist import (  # noqa: E402
    ErroChecklist,
    carregar_checklist,
    filtrar_itens,
    hash_checklist,
)
from sysdoc_dvi.tipos import ItemChecklist  # noqa: E402


VALID_ITEM = {
    "id": "DVI-AMB-001",
    "aplicabilidade": "ambos",
    "peca": "ETP",
    "tipo": "presenca",
    "pergunta": "A necessidade da contratação está descrita?",
    "base_legal_texto": "pendente",
    "referencia": "Lei 14.133/2021, art. 18, §1º, I",
    "severidade_default": "média",
    "modelo_alvo": "economico",
    "ativo": True,
}


def _write_checklist(tmp_path, itens, versao="1.0", descricao="Checklist de teste"):
    path = tmp_path / "checklist.yaml"
    data = {"versao": versao, "descricao": descricao, "itens": itens}
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


class TestCarregarChecklistMeta:
    def test_meta_traz_versao_e_descricao(self, tmp_path):
        path = _write_checklist(tmp_path, [dict(VALID_ITEM)])
        meta, itens = carregar_checklist(path)
        assert meta["versao"] == "1.0"
        assert meta["descricao"] == "Checklist de teste"
        assert len(itens) == 1
        assert isinstance(itens[0], ItemChecklist)


class TestCampoObrigatorio:
    @pytest.mark.parametrize(
        "campo",
        [
            "id",
            "aplicabilidade",
            "peca",
            "tipo",
            "pergunta",
            "base_legal_texto",
            "referencia",
            "severidade_default",
            "modelo_alvo",
            "ativo",
        ],
    )
    def test_campo_ausente_levanta_erro(self, tmp_path, campo):
        item = dict(VALID_ITEM)
        del item[campo]
        path = _write_checklist(tmp_path, [item])
        with pytest.raises(ErroChecklist) as exc_info:
            carregar_checklist(path)
        assert campo in str(exc_info.value)

    def test_mensagem_cita_id_e_campo_do_item(self, tmp_path):
        item = dict(VALID_ITEM)
        del item["pergunta"]
        path = _write_checklist(tmp_path, [item])
        with pytest.raises(ErroChecklist) as exc_info:
            carregar_checklist(path)
        message = str(exc_info.value)
        assert "DVI-AMB-001" in message
        assert "pergunta" in message


class TestValorForaDoDominio:
    def test_tipo_acentuado_invalido(self, tmp_path):
        item = dict(VALID_ITEM)
        item["tipo"] = "presença"
        path = _write_checklist(tmp_path, [item])
        with pytest.raises(ErroChecklist):
            carregar_checklist(path)

    def test_aplicabilidade_maiuscula_invalida(self, tmp_path):
        item = dict(VALID_ITEM)
        item["aplicabilidade"] = "TIC"
        path = _write_checklist(tmp_path, [item])
        with pytest.raises(ErroChecklist):
            carregar_checklist(path)


class TestIdChecklist:
    def test_id_fora_do_padrao_levanta_erro(self, tmp_path):
        item = dict(VALID_ITEM)
        item["id"] = "DVI-XYZ-001"
        path = _write_checklist(tmp_path, [item])
        with pytest.raises(ErroChecklist):
            carregar_checklist(path)

    def test_id_duplicado_levanta_erro(self, tmp_path):
        item1 = dict(VALID_ITEM)
        item2 = dict(VALID_ITEM)
        path = _write_checklist(tmp_path, [item1, item2])
        with pytest.raises(ErroChecklist):
            carregar_checklist(path)


class TestDocumentoSaida:
    def test_default_etp_para_peca_etp(self, tmp_path):
        item = dict(VALID_ITEM)
        item["peca"] = "ETP"
        path = _write_checklist(tmp_path, [item])
        _, itens = carregar_checklist(path)
        assert itens[0].documento_saida == "ETP"

    def test_default_tr_para_peca_tr(self, tmp_path):
        item = dict(VALID_ITEM)
        item["peca"] = "TR"
        path = _write_checklist(tmp_path, [item])
        _, itens = carregar_checklist(path)
        assert itens[0].documento_saida == "TR"

    def test_documento_saida_explicito_invalido_levanta_erro(self, tmp_path):
        item = dict(VALID_ITEM)
        item["documento_saida"] = "MCP"
        path = _write_checklist(tmp_path, [item])
        with pytest.raises(ErroChecklist):
            carregar_checklist(path)


class TestFiltrarItens:
    def _checklist_misto(self, tmp_path):
        geral = dict(VALID_ITEM, id="DVI-GER-001", aplicabilidade="geral")
        tic = dict(VALID_ITEM, id="DVI-TIC-001", aplicabilidade="tic")
        ambos = dict(VALID_ITEM, id="DVI-AMB-001", aplicabilidade="ambos")
        inativo = dict(VALID_ITEM, id="DVI-GER-002", aplicabilidade="geral", ativo=False)
        return _write_checklist(tmp_path, [geral, tic, ambos, inativo])

    def test_filtra_geral(self, tmp_path):
        path = self._checklist_misto(tmp_path)
        _, itens = carregar_checklist(path)
        filtrados = filtrar_itens(itens, "geral")
        assert {i.id for i in filtrados} == {"DVI-GER-001", "DVI-AMB-001"}

    def test_filtra_tic(self, tmp_path):
        path = self._checklist_misto(tmp_path)
        _, itens = carregar_checklist(path)
        filtrados = filtrar_itens(itens, "tic")
        assert {i.id for i in filtrados} == {"DVI-TIC-001", "DVI-AMB-001"}


class TestHashChecklist:
    def test_hash_reproduzivel(self, tmp_path):
        path = _write_checklist(tmp_path, [dict(VALID_ITEM)])
        assert hash_checklist(path) == hash_checklist(path)
        assert len(hash_checklist(path)) == 64

    def test_hash_muda_com_byte_alterado(self, tmp_path):
        path = _write_checklist(tmp_path, [dict(VALID_ITEM)])
        h1 = hash_checklist(path)
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n# comentário extra\n")
        h2 = hash_checklist(path)
        assert h1 != h2


class TestChecklistReal:
    def test_carrega_checklist_dvi_real_sem_erro(self):
        checklist_path = ROOT / "checklists" / "dvi.yaml"
        meta, itens = carregar_checklist(checklist_path)
        assert meta["versao"]
        assert len(itens) >= 6
        ids = {item.id for item in itens}
        assert len(ids) == len(itens)
