"""
Testes da tabela curada de vigência de normativos (sysdoc_dvi.normas).

Cobre carga (global + override por projeto), normalização de citações,
lookup determinístico, aviso de curadoria vencida e a verificação de
vigência `vigencia` do motor DVI (RF4/RF7, D-10..D-13).
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.normas import (  # noqa: E402
    ErroVigencia,
    carregar_vigencia,
    consultar_norma,
    normalizar_citacao,
    normas_desatualizadas,
    verificar_item_vigencia,
)
from sysdoc_dvi.tipos import ItemChecklist  # noqa: E402


VALID_ENTRY = {
    "norma": "Lei nº 14.133, de 1º de abril de 2021",
    "aliases": ["Lei 14.133/2021", "NLLC"],
    "status": "vigente",
    "substituida_por": None,
    "conferida_em": "2026-08-26",
}


def _write_tabela(tmp_path, entradas, nome="vigencia.yaml"):
    path = tmp_path / nome
    path.write_text(
        yaml.safe_dump({"normas": entradas}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _item(tipo="vigencia", severidade="alta"):
    return ItemChecklist(
        id="DVI-AMB-004",
        aplicabilidade="ambos",
        peca="PROCESSO",
        documento_saida="TR",
        tipo=tipo,
        pergunta="Os normativos citados continuam vigentes?",
        base_legal_texto="pendente",
        referencia="normas/vigencia.yaml (tabela curada de vigência normativa)",
        severidade_default=severidade,
        modelo_alvo="economico",
        ativo=True,
        parametros={},
    )


class TestCarga:
    def test_tabela_indexada_por_citacao_normalizada(self, tmp_path):
        path = _write_tabela(tmp_path, [dict(VALID_ENTRY)])
        tabela = carregar_vigencia(path)
        assert normalizar_citacao(VALID_ENTRY["norma"]) in tabela

    def test_alias_aponta_para_mesma_entrada(self, tmp_path):
        path = _write_tabela(tmp_path, [dict(VALID_ENTRY)])
        tabela = carregar_vigencia(path)
        chave_norma = normalizar_citacao(VALID_ENTRY["norma"])
        chave_alias = normalizar_citacao("NLLC")
        assert tabela[chave_norma]["norma"] == tabela[chave_alias]["norma"]

    def test_entrada_sem_norma_levanta_erro_citando_indice(self, tmp_path):
        entrada = dict(VALID_ENTRY)
        del entrada["norma"]
        path = _write_tabela(tmp_path, [entrada])
        with pytest.raises(ErroVigencia) as exc_info:
            carregar_vigencia(path)
        assert "0" in str(exc_info.value)

    def test_entrada_sem_status_levanta_erro(self, tmp_path):
        entrada = dict(VALID_ENTRY)
        del entrada["status"]
        path = _write_tabela(tmp_path, [entrada])
        with pytest.raises(ErroVigencia):
            carregar_vigencia(path)

    def test_entrada_sem_conferida_em_levanta_erro(self, tmp_path):
        entrada = dict(VALID_ENTRY)
        del entrada["conferida_em"]
        path = _write_tabela(tmp_path, [entrada])
        with pytest.raises(ErroVigencia):
            carregar_vigencia(path)

    def test_status_fora_do_dominio_levanta_erro(self, tmp_path):
        entrada = dict(VALID_ENTRY, status="cancelada")
        path = _write_tabela(tmp_path, [entrada])
        with pytest.raises(ErroVigencia):
            carregar_vigencia(path)

    def test_status_substituida_sem_substituida_por_levanta_erro(self, tmp_path):
        entrada = dict(VALID_ENTRY, status="substituida", substituida_por=None)
        path = _write_tabela(tmp_path, [entrada])
        with pytest.raises(ErroVigencia):
            carregar_vigencia(path)

    def test_status_substituida_com_substituida_por_carrega_sem_erro(self, tmp_path):
        entrada = dict(
            VALID_ENTRY,
            status="substituida",
            substituida_por="Resolução CFC 1.799/2026",
        )
        path = _write_tabela(tmp_path, [entrada])
        tabela = carregar_vigencia(path)
        assert tabela[normalizar_citacao(VALID_ENTRY["norma"])]["status"] == "substituida"

    def test_arquivo_projeto_ausente_ignorado_sem_erro(self, tmp_path):
        global_path = _write_tabela(tmp_path, [dict(VALID_ENTRY)])
        projeto_path = tmp_path / "projeto" / "vigencia.yaml"
        tabela = carregar_vigencia(global_path, projeto_path)
        assert normalizar_citacao(VALID_ENTRY["norma"]) in tabela

    def test_carrega_tabela_global_real_sem_erro(self):
        tabela = carregar_vigencia(ROOT / "normas" / "vigencia.yaml")
        assert "nllc" in " ".join(tabela)


class TestOverride:
    def test_projeto_sobrepoe_entrada_global_mesma_norma(self, tmp_path):
        global_path = _write_tabela(
            tmp_path, [dict(VALID_ENTRY, status="vigente")], nome="global.yaml"
        )
        projeto_entry = dict(
            VALID_ENTRY,
            status="revogada",
            substituida_por=None,
        )
        projeto_path = _write_tabela(tmp_path, [projeto_entry], nome="projeto.yaml")
        tabela = carregar_vigencia(global_path, projeto_path)
        chave = normalizar_citacao(VALID_ENTRY["norma"])
        assert tabela[chave]["status"] == "revogada"
        assert tabela[chave]["origem"] == "projeto"

    def test_norma_apenas_global_permanece_apos_override_de_outra_norma(self, tmp_path):
        outra = dict(
            VALID_ENTRY,
            norma="Decreto nº 10.024, de 20 de setembro de 2019",
            aliases=["Decreto 10.024/2019"],
        )
        global_path = _write_tabela(
            tmp_path, [dict(VALID_ENTRY), outra], nome="global.yaml"
        )
        projeto_path = _write_tabela(
            tmp_path, [dict(VALID_ENTRY, status="suspensa")], nome="projeto.yaml"
        )
        tabela = carregar_vigencia(global_path, projeto_path)
        chave_outra = normalizar_citacao(outra["norma"])
        assert tabela[chave_outra]["origem"] == "global"


class TestNormalizacao:
    @pytest.mark.parametrize(
        "citacao",
        [
            "Lei nº 14.133, de 1º de abril de 2021",
            "Lei n° 14.133/2021",
            "LEI No 14133/2021",
            "lei 14.133 de 2021",
        ],
    )
    def test_normalizar_citacao_iguala_variantes(self, citacao):
        referencia = normalizar_citacao("Lei nº 14.133, de 1º de abril de 2021")
        assert normalizar_citacao(citacao) == referencia

    def test_normalizar_citacao_remove_acentos_caixa_e_pontuacao_de_milhar(self):
        assert normalizar_citacao("ACÓRDÃO Nº 1.872/2018") == normalizar_citacao(
            "acordao 1872/2018"
        )


class TestLookup:
    def test_consultar_norma_por_alias(self, tmp_path):
        path = _write_tabela(tmp_path, [dict(VALID_ENTRY)])
        tabela = carregar_vigencia(path)
        entrada = consultar_norma(tabela, "NLLC")
        assert entrada is not None
        assert entrada["norma"] == VALID_ENTRY["norma"]

    def test_consultar_norma_inexistente_retorna_none(self, tmp_path):
        path = _write_tabela(tmp_path, [dict(VALID_ENTRY)])
        tabela = carregar_vigencia(path)
        assert consultar_norma(tabela, "Portaria XPTO 1/2030") is None


class TestCuradoria:
    def test_normas_desatualizadas_lista_vencidas_sem_duplicar_aliases(self, tmp_path):
        vencida = dict(
            VALID_ENTRY,
            norma="Decreto nº 10.024, de 20 de setembro de 2019",
            aliases=["Decreto 10.024/2019"],
            conferida_em="2020-01-01",
        )
        recente = dict(
            VALID_ENTRY,
            conferida_em="2026-08-01",
        )
        path = _write_tabela(tmp_path, [vencida, recente])
        tabela = carregar_vigencia(path)
        resultado = normas_desatualizadas(tabela, 180, hoje=date(2026, 8, 26))
        assert resultado == [vencida["norma"]]

    def test_normas_desatualizadas_limiar_default_e_180_dias(self, tmp_path):
        vencida = dict(VALID_ENTRY, conferida_em="2026-01-01")
        path = _write_tabela(tmp_path, [vencida])
        tabela = carregar_vigencia(path)
        resultado = normas_desatualizadas(tabela, hoje=date(2026, 8, 26))
        assert resultado == [vencida["norma"]]

    def test_normas_desatualizadas_nao_lista_dentro_do_limiar(self, tmp_path):
        recente = dict(VALID_ENTRY, conferida_em="2026-08-01")
        path = _write_tabela(tmp_path, [recente])
        tabela = carregar_vigencia(path)
        resultado = normas_desatualizadas(tabela, 180, hoje=date(2026, 8, 26))
        assert resultado == []


class TestVerificacaoVigencia:
    def _tabela(self, tmp_path, entradas):
        path = _write_tabela(tmp_path, entradas)
        return carregar_vigencia(path)

    def test_norma_vigente_citada_gera_conforme(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY)])
        texto = "Aplica-se a Lei nº 14.133/2021 a este processo."
        resultado = verificar_item_vigencia(_item(), texto, tabela)
        assert resultado.classificação == "conforme"
        assert resultado.risco_jurídico == "informativo"
        assert resultado.origem_verificacao == "lookup"

    def test_norma_revogada_citada_gera_risco_relevante_com_substituta(self, tmp_path):
        entrada = dict(
            VALID_ENTRY,
            status="substituida",
            substituida_por="Resolução CFC 1.799/2026",
        )
        tabela = self._tabela(tmp_path, [entrada])
        texto = "Nos termos da Lei nº 14.133/2021, observa-se o rito."
        resultado = verificar_item_vigencia(_item(), texto, tabela)
        assert resultado.classificação == "risco"
        assert resultado.risco_jurídico == "relevante"
        assert "Resolução CFC 1.799/2026" in resultado.parecer

    def test_norma_suspensa_gera_pendente_sem_certificar_vigencia(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY, status="suspensa")])
        texto = "Aplica-se a Lei nº 14.133/2021 a este processo."
        resultado = verificar_item_vigencia(_item(), texto, tabela)
        assert resultado.classificação == "pendente"
        assert resultado.risco_jurídico == "informativo"
        assert "suspensa" in resultado.parecer
        assert "vigente conforme tabela curada" not in resultado.parecer

    def test_norma_pendente_de_conferencia_gera_pendente_sem_certificar_vigencia(self, tmp_path):
        tabela = self._tabela(
            tmp_path, [dict(VALID_ENTRY, status="pendente_de_conferencia")]
        )
        texto = "Aplica-se a Lei nº 14.133/2021 a este processo."
        resultado = verificar_item_vigencia(_item(), texto, tabela)
        assert resultado.classificação == "pendente"
        assert resultado.risco_jurídico == "informativo"
        assert "não conferida" in resultado.parecer
        assert "vigente conforme tabela curada" not in resultado.parecer

    def test_norma_nao_catalogada_gera_pendente(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY)])
        texto = "Aplica-se a Portaria nº 999/2099 a este processo."
        resultado = verificar_item_vigencia(_item(), texto, tabela)
        assert resultado.classificação == "pendente"
        assert "norma não catalogada" in resultado.parecer

    def test_nenhum_normativo_citado_gera_pendente(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY)])
        resultado = verificar_item_vigencia(_item(), "Texto sem qualquer citação legal.", tabela)
        assert resultado.classificação == "pendente"
        assert resultado.de == "[OMISSÃO]"

    def test_de_e_sempre_trecho_literal_da_citacao(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY)])
        texto = "Conforme a Lei nº 14.133/2021, o processo segue."
        resultado = verificar_item_vigencia(_item(), texto, tabela)
        assert resultado.de in texto

    def test_severidade_vem_do_item(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY)])
        texto = "Aplica-se a Lei nº 14.133/2021."
        resultado = verificar_item_vigencia(_item(severidade="crítica"), texto, tabela)
        assert resultado.severidade == "crítica"

    def test_modulo_sem_import_de_rede(self):
        codigo = (ROOT / "sysdoc_dvi" / "normas.py").read_text(encoding="utf-8")
        assert not re.search(r"\brequests\b|\burllib\b|\bhttp\b", codigo, flags=re.IGNORECASE)

    def test_regex_citacao_processa_texto_grande_rapidamente(self, tmp_path):
        tabela = self._tabela(tmp_path, [dict(VALID_ENTRY)])
        texto_grande = ("parágrafo sem citações relevantes. " * 30000) + "Lei nº 14.133/2021."
        inicio = time.monotonic()
        resultado = verificar_item_vigencia(_item(), texto_grande, tabela)
        duracao = time.monotonic() - inicio
        assert duracao < 2.0
        assert resultado.classificação == "conforme"
