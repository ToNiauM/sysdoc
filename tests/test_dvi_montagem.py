"""
Testes do motor DVI: montagem do dados_consolidados.json (RNF5), relatório
de execução (RF9) e checkpoint incremental de retomada (D-04).

Cobertura:
  - TestMontagem: JSON completo e válido pelo validador vigente
  - TestIds: renumeração por documento e preservação do checklist_id
  - TestCoerencia: correções automáticas e erros de coerência
  - TestRelatorio: contagens, custo, duração e ausência de segredo
  - TestCheckpoint: gravação incremental, invalidação por hash, retomada
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.montagem import ErroMontagem, montar_json  # noqa: E402
from sysdoc_dvi.tipos import ResultadoItem, UsoModelo  # noqa: E402


CHECKLIST_HASH = hashlib.sha256(b"checklist-dvi-teste").hexdigest()
OUTRO_HASH = hashlib.sha256(b"checklist-dvi-outro").hexdigest()


def _resultado(
    documento="ETP",
    checklist_id="DVI-GER-001",
    seção="1.1",
    de="O objeto desta contratação é a aquisição de combustível para veículos oficiais.",
    para="O objeto deve detalhar as especificações técnicas do combustível, conforme exigido.",
    parecer="Há omissão de especificações técnicas obrigatórias na descrição do objeto.",
    fundamento="Art. 40 da Lei 14.133, de 1º de abril de 2021.",
    classificação="ajuste_necessário",
    severidade="média",
    risco_jurídico="relevante",
    origem_verificacao="llm",
    uso=None,
    falha_estruturada=None,
    falha_grounding=False,
):
    return ResultadoItem(
        checklist_id=checklist_id,
        origem_verificacao=origem_verificacao,
        documento=documento,
        seção=seção,
        de=de,
        para=para,
        parecer=parecer,
        fundamento=fundamento,
        classificação=classificação,
        severidade=severidade,
        risco_jurídico=risco_jurídico,
        uso=uso,
        falha_estruturada=falha_estruturada,
        falha_grounding=falha_grounding,
    )


def _secao_valida(numero="ETP-001"):
    return {
        "classificação_documento": "aprovado_com_ressalvas",
        "parecer_documento": "Documento " + ("palavra " * 130),
        "numero": numero,
    }


def _pareceres_validos():
    return {
        "parecer_executivo": "Este parecer " + ("palavra " * 460),
        "secao_etp": _secao_valida("ETP-001"),
        "secao_tr": _secao_valida("TR-001"),
    }


def _projeto_valido():
    return {
        "órgão": "Organização de Exemplo",
        "processo": "12345.000001/2026-01",
        "valor_estimado": "R$ 100.000,00",
        "objeto": "Aquisição de combustível",
    }


def _montar(itens, **overrides):
    kwargs = {
        "itens": itens,
        "pareceres": _pareceres_validos(),
        "projeto": _projeto_valido(),
        "modelo_ia": "deepseek-chat",
        "checklist_hash": CHECKLIST_HASH,
        "documentos_analisados": ["ETP.pdf", "TR.pdf"],
        "data_analise": "2026-08-26",
    }
    kwargs.update(overrides)
    return montar_json(**kwargs)


# ---------------------------------------------------------------------------
# TestMontagem
# ---------------------------------------------------------------------------

class TestMontagem:
    def test_json_completo_passa_no_validador(self, tmp_path):
        (tmp_path / "ETP.pdf").write_bytes(b"%PDF-1.4 placeholder")
        (tmp_path / "TR.pdf").write_bytes(b"%PDF-1.4 placeholder")

        itens = [
            _resultado(documento="ETP", checklist_id="DVI-GER-001"),
            _resultado(documento="TR", checklist_id="DVI-GER-002"),
        ]
        dados = _montar(itens)

        json_file = tmp_path / "dados_consolidados.json"
        json_file.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

        resultado = subprocess.run(
            [sys.executable, str(ROOT / "templates" / "validate_sysdoc.py"), str(json_file), str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr

    def test_modelo_ia_generico_levanta_erro(self):
        itens = [_resultado()]
        with pytest.raises(ErroMontagem):
            _montar(itens, modelo_ia="modelo")

    def test_modelo_ia_com_maiuscula_levanta_erro(self):
        itens = [_resultado()]
        with pytest.raises(ErroMontagem):
            _montar(itens, modelo_ia="DeepSeek-Chat")

    def test_checklist_hash_invalido_levanta_erro(self):
        itens = [_resultado()]
        with pytest.raises(ErroMontagem):
            _montar(itens, checklist_hash="hash-invalido")

    def test_checklist_id_preservado(self):
        itens = [_resultado(checklist_id="DVI-AMB-003")]
        dados = _montar(itens)
        assert dados["itens"][0]["checklist_id"] == "DVI-AMB-003"

    def test_origem_verificacao_preenchida(self):
        itens = [_resultado(origem_verificacao="deterministico")]
        dados = _montar(itens)
        assert dados["itens"][0]["origem_verificacao"] == "deterministico"

    def test_status_delic_novo_e_alterado_falso(self):
        itens = [_resultado()]
        dados = _montar(itens)
        item = dados["itens"][0]
        assert item["status_delic"] == "novo"
        assert item["alterado_pelo_jurídico"] is False

    def test_metadados_contem_labels_esperados(self):
        itens = [_resultado()]
        dados = _montar(itens)
        labels = {meta["label"] for meta in dados["metadados"]}
        assert {
            "Hash do checklist",
            "Versão do schema",
            "Itens verificados",
            "Origem das verificações",
        } <= labels

    def test_schema_version_e_checklist_hash_na_raiz(self):
        itens = [_resultado()]
        dados = _montar(itens)
        assert dados["schema_version"] == "1.1"
        assert dados["checklist_hash"] == CHECKLIST_HASH

    def test_campo_de_curto_demais_levanta_erro(self):
        itens = [_resultado(de="Curto")]
        with pytest.raises(ErroMontagem):
            _montar(itens)

    def test_campo_para_curto_demais_levanta_erro(self):
        itens = [_resultado(para="Ok")]
        with pytest.raises(ErroMontagem):
            _montar(itens)

    def test_campo_parecer_vazio_levanta_erro(self):
        itens = [_resultado(parecer="")]
        with pytest.raises(ErroMontagem):
            _montar(itens)

    def test_documento_invalido_levanta_erro(self):
        itens = [_resultado(documento="MCP")]
        with pytest.raises(ErroMontagem):
            _montar(itens)

    def test_sem_itens_levanta_erro(self):
        with pytest.raises(ErroMontagem):
            _montar([])

    def test_pareceres_sem_secao_tr_levanta_erro(self):
        itens = [_resultado()]
        pareceres = _pareceres_validos()
        del pareceres["secao_tr"]
        with pytest.raises(ErroMontagem):
            _montar(itens, pareceres=pareceres)

    def test_projeto_incompleto_levanta_erro(self):
        itens = [_resultado()]
        projeto = _projeto_valido()
        del projeto["objeto"]
        with pytest.raises(ErroMontagem):
            _montar(itens, projeto=projeto)


# ---------------------------------------------------------------------------
# TestIds
# ---------------------------------------------------------------------------

class TestIds:
    def test_renumeracao_por_documento(self):
        itens = [
            _resultado(documento="TR", checklist_id="DVI-GER-010"),
            _resultado(documento="ETP", checklist_id="DVI-GER-011"),
            _resultado(documento="ETP", checklist_id="DVI-GER-012"),
            _resultado(documento="TR", checklist_id="DVI-GER-013"),
        ]
        dados = _montar(itens)
        etp_itens = [item for item in dados["itens"] if item["documento"] == "ETP"]
        tr_itens = [item for item in dados["itens"] if item["documento"] == "TR"]

        assert [item["id"] for item in etp_itens] == ["ETP-001", "ETP-002"]
        assert [item["número"] for item in etp_itens] == [1, 2]
        assert [item["id"] for item in tr_itens] == ["TR-001", "TR-002"]
        assert [item["número"] for item in tr_itens] == [1, 2]

    def test_ordem_original_preservada_dentro_do_documento(self):
        itens = [
            _resultado(documento="ETP", checklist_id="DVI-GER-020"),
            _resultado(documento="ETP", checklist_id="DVI-GER-021"),
        ]
        dados = _montar(itens)
        etp_itens = [item for item in dados["itens"] if item["documento"] == "ETP"]
        assert [item["checklist_id"] for item in etp_itens] == ["DVI-GER-020", "DVI-GER-021"]

    def test_ids_seguem_padrao_documento_nnn(self):
        itens = [_resultado(documento="ETP"), _resultado(documento="TR")]
        dados = _montar(itens)
        import re

        for item in dados["itens"]:
            assert re.fullmatch(rf"{item['documento']}-\d{{3}}", item["id"])
