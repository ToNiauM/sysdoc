"""
Invariantes de conteúdo do checklist DVI real (`checklists/dvi.yaml`) e da
tabela de vigência (`normas/vigencia.yaml`) — plano 05-13, Task 3.

Estes testes travam a conversão dos dois prompts DVI monolíticos (processos
gerais e TIC) em dados: nenhum item ativo pode ter base legal pendente,
toda norma citada em `referencia` (exceto verificações puramente internas,
prefixadas com "Padrão interno:") precisa ser encontrada na tabela curada de
vigência, ids são únicos e sequenciais por prefixo, itens `mecanica`
declaram `parametros.verificacao` válido, itens `calculo` declaram
`parametros.tolerancia_absoluta`, e a distribuição por aplicabilidade cobre
geral, tic e ambos. O teste de mutação prova CA4 do PRD (editar o YAML muda
o resultado da análise sem qualquer mudança de código).
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.checklist import carregar_checklist, filtrar_itens  # noqa: E402
from sysdoc_dvi.normas import carregar_vigencia, consultar_norma  # noqa: E402
from sysdoc_dvi.verificacoes.mecanica import _DISPATCH as MECANICA_VERIFICACOES  # noqa: E402

CHECKLIST_PATH = ROOT / "checklists" / "dvi.yaml"
VIGENCIA_PATH = ROOT / "normas" / "vigencia.yaml"

_PADRAO_INTERNO_PREFIXO = "Padrão interno:"
_ID_PATTERN = re.compile(r"^DVI-(GER|TIC|AMB)-(\d{3})$")


@pytest.fixture(scope="module")
def checklist():
    meta, itens = carregar_checklist(CHECKLIST_PATH)
    return meta, itens


@pytest.fixture(scope="module")
def tabela_vigencia():
    return carregar_vigencia(VIGENCIA_PATH)


class TestBaseLegalDeItemAtivo:
    def test_todo_item_ativo_tem_base_legal_nao_vazia_e_diferente_de_pendente(self, checklist):
        _, itens = checklist
        violacoes = [
            item.id
            for item in itens
            if item.ativo and (not item.base_legal_texto or item.base_legal_texto.strip() == "pendente")
        ]
        assert violacoes == [], f"itens ativos com base_legal_texto pendente/vazio: {violacoes}"


class TestCoberturaNormaChecklist:
    def test_toda_referencia_de_item_ativo_nao_interna_e_encontrada_na_tabela(
        self, checklist, tabela_vigencia
    ):
        _, itens = checklist
        nao_encontradas = []
        for item in itens:
            if not item.ativo:
                continue
            if item.referencia.strip().startswith(_PADRAO_INTERNO_PREFIXO):
                continue
            if consultar_norma(tabela_vigencia, item.referencia) is None:
                nao_encontradas.append((item.id, item.referencia))
        assert nao_encontradas == [], (
            "referência de item ativo não encontrada em normas/vigencia.yaml "
            f"(consultar_norma retornou None): {nao_encontradas}"
        )

    def test_falha_se_referencia_de_item_ativo_nao_catalogada(self, tmp_path, tabela_vigencia):
        from sysdoc_dvi.tipos import ItemChecklist

        item_falso = ItemChecklist(
            id="DVI-AMB-999",
            aplicabilidade="ambos",
            peca="TR",
            documento_saida="TR",
            tipo="presenca",
            pergunta="item de teste com norma não catalogada",
            base_legal_texto="texto de teste",
            referencia="Lei Fictícia nº 99.999/2099",
            severidade_default="média",
            modelo_alvo="economico",
            ativo=True,
            parametros={},
        )
        assert consultar_norma(tabela_vigencia, item_falso.referencia) is None


class TestIdsUnicosESequenciais:
    def test_ids_unicos(self, checklist):
        _, itens = checklist
        ids = [item.id for item in itens]
        assert len(ids) == len(set(ids))

    def test_ids_sequenciais_por_prefixo(self, checklist):
        _, itens = checklist
        por_prefixo: dict[str, list[int]] = defaultdict(list)
        for item in itens:
            match = _ID_PATTERN.match(item.id)
            assert match, f"id fora do padrão: {item.id}"
            prefixo, numero = match.groups()
            por_prefixo[prefixo].append(int(numero))

        for prefixo, numeros in por_prefixo.items():
            numeros_ordenados = sorted(numeros)
            esperado = list(range(1, len(numeros_ordenados) + 1))
            assert numeros_ordenados == esperado, (
                f"ids do prefixo {prefixo} não são sequenciais/contínuos: {numeros_ordenados}"
            )


class TestParametrosPorTipo:
    def test_todo_item_mecanica_declara_verificacao_valida(self, checklist):
        _, itens = checklist
        for item in itens:
            if item.tipo != "mecanica":
                continue
            verificacao = item.parametros.get("verificacao")
            assert verificacao in MECANICA_VERIFICACOES, (
                f"item '{item.id}': parametros.verificacao ausente ou inválido: {verificacao!r}"
            )

    def test_todo_item_calculo_declara_tolerancia_absoluta(self, checklist):
        _, itens = checklist
        for item in itens:
            if item.tipo != "calculo":
                continue
            assert "tolerancia_absoluta" in item.parametros, (
                f"item '{item.id}': parametros.tolerancia_absoluta ausente"
            )


class TestDistribuicaoPorAplicabilidade:
    def test_cobre_geral_tic_e_ambos(self, checklist):
        _, itens = checklist
        aplicabilidades = {item.aplicabilidade for item in itens}
        assert aplicabilidades == {"geral", "tic", "ambos"}

    def test_cada_aplicabilidade_tem_pelo_menos_um_item_ativo(self, checklist):
        _, itens = checklist
        for aplicabilidade in ("geral", "tic", "ambos"):
            ativos = [item for item in itens if item.aplicabilidade == aplicabilidade and item.ativo]
            assert ativos, f"nenhum item ativo com aplicabilidade '{aplicabilidade}'"


class TestVigenciaTabelaCobertura:
    def test_tabela_tem_pelo_menos_dez_normas(self):
        dados = yaml.safe_load(VIGENCIA_PATH.read_text(encoding="utf-8"))
        assert len(dados["normas"]) >= 10

    def test_entradas_substituidas_declaram_substituida_por(self):
        dados = yaml.safe_load(VIGENCIA_PATH.read_text(encoding="utf-8"))
        for entrada in dados["normas"]:
            if entrada["status"] == "substituida":
                assert entrada.get("substituida_por"), (
                    f"norma '{entrada['norma']}': status substituida sem substituida_por"
                )


class TestMutacaoDesativaItem:
    def test_desativar_item_no_yaml_muda_filtrar_itens_sem_alteracao_de_codigo(self, tmp_path):
        dados = yaml.safe_load(CHECKLIST_PATH.read_text(encoding="utf-8"))

        alvo = next(item for item in dados["itens"] if item["id"] == "DVI-GER-002")
        assert alvo["ativo"] is True

        meta_original, itens_original = carregar_checklist(CHECKLIST_PATH)
        antes = {item.id for item in filtrar_itens(itens_original, "geral")}
        assert "DVI-GER-002" in antes

        alvo["ativo"] = False
        copia_path = tmp_path / "checklist_mutado.yaml"
        copia_path.write_text(
            yaml.safe_dump(dados, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        _, itens_mutados = carregar_checklist(copia_path)
        depois = {item.id for item in filtrar_itens(itens_mutados, "geral")}

        assert "DVI-GER-002" not in depois
        assert depois == antes - {"DVI-GER-002"}
