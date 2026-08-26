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

from sysdoc_dvi import provedores  # noqa: E402
from sysdoc_dvi.checkpoint import (  # noqa: E402
    carregar_checkpoint,
    limpar_checkpoint,
    registrar_item,
)
from sysdoc_dvi.montagem import ErroMontagem, montar_json  # noqa: E402
from sysdoc_dvi.relatorio import montar_relatorio, renderizar_relatorio  # noqa: E402
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
# TestCoerencia
# ---------------------------------------------------------------------------

class TestCoerencia:
    def test_conforme_com_risco_relevante_e_corrigido_para_informativo(self):
        itens = [_resultado(classificação="conforme", risco_jurídico="relevante")]
        dados = _montar(itens)
        assert dados["itens"][0]["risco_jurídico"] == "informativo"

    def test_conforme_ja_informativo_permanece_informativo(self):
        itens = [_resultado(classificação="conforme", risco_jurídico="informativo")]
        dados = _montar(itens)
        assert dados["itens"][0]["risco_jurídico"] == "informativo"

    def test_risco_sem_risco_juridico_adequado_levanta_erro(self):
        itens = [_resultado(classificação="risco", risco_jurídico="menor")]
        with pytest.raises(ErroMontagem):
            _montar(itens)

    def test_bloqueante_exige_severidade_alta_ou_critica(self):
        itens = [
            _resultado(
                classificação="risco",
                risco_jurídico="bloqueante",
                severidade="baixa",
            )
        ]
        with pytest.raises(ErroMontagem):
            _montar(itens)

    def test_bloqueante_com_severidade_alta_passa(self):
        itens = [
            _resultado(
                classificação="risco",
                risco_jurídico="bloqueante",
                severidade="alta",
            )
        ]
        dados = _montar(itens)
        assert dados["itens"][0]["risco_jurídico"] == "bloqueante"

    def test_erro_de_coerencia_cita_checklist_id(self):
        itens = [
            _resultado(
                checklist_id="DVI-GER-099",
                classificação="risco",
                risco_jurídico="menor",
            )
        ]
        with pytest.raises(ErroMontagem, match="DVI-GER-099"):
            _montar(itens)


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


# ---------------------------------------------------------------------------
# TestRelatorio
# ---------------------------------------------------------------------------

class TestRelatorio:
    def setup_method(self):
        provedores.limpar_registro_chamadas()

    def teardown_method(self):
        provedores.limpar_registro_chamadas()

    def test_relatorio_contem_chaves_esperadas(self):
        itens = [_resultado(documento="ETP", classificação="conforme", risco_jurídico="informativo")]
        relatorio = montar_relatorio(
            itens=itens,
            checklist_hash=CHECKLIST_HASH,
            schema_version="1.1",
            duracao_total_s=12.5,
        )
        for chave in (
            "itens_por_status",
            "itens_por_tipo",
            "itens_por_origem",
            "falhas_grounding",
            "falhas_estruturadas",
            "tokens_por_modelo",
            "custo_por_modelo",
            "custo_total",
            "duracao_total_s",
            "checklist_hash",
            "schema_version",
            "pecas_mapeadas",
            "avisos",
        ):
            assert chave in relatorio

    def test_itens_por_status_e_por_documento(self):
        itens = [
            _resultado(documento="ETP", classificação="conforme", risco_jurídico="informativo"),
            _resultado(documento="ETP", classificação="risco", risco_jurídico="relevante"),
            _resultado(documento="TR", classificação="pendente"),
        ]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 1.0)
        assert relatorio["itens_por_status"] == {"conforme": 1, "risco": 1, "pendente": 1}
        assert relatorio["itens_por_tipo"] == {"ETP": 2, "TR": 1}

    def test_falhas_grounding_listadas(self):
        itens = [
            _resultado(checklist_id="DVI-GER-030", falha_grounding=True),
            _resultado(checklist_id="DVI-GER-031", falha_grounding=False),
        ]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 1.0)
        assert relatorio["falhas_grounding"] == {"total": 1, "itens": ["DVI-GER-030"]}

    def test_falhas_estruturadas_listadas(self):
        itens = [
            _resultado(checklist_id="DVI-GER-040", falha_estruturada="erro de parsing"),
        ]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 1.0)
        assert relatorio["falhas_estruturadas"] == {"total": 1, "itens": ["DVI-GER-040"]}

    def test_sem_chamadas_llm_reporta_custo_zero(self):
        itens = [_resultado(origem_verificacao="deterministico")]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 0.3)
        assert relatorio["custo_total"] == 0.0
        assert relatorio["tokens_por_modelo"] == {}
        assert relatorio["custo_por_modelo"] == {}

    def test_tokens_e_custo_por_modelo_a_partir_do_registro(self):
        registro = [
            {
                "provedor": "openrouter",
                "modelo": "deepseek-chat",
                "tokens_entrada": 100,
                "tokens_saida": 50,
                "custo_estimado": 0.02,
                "duracao_s": 1.1,
            },
            {
                "provedor": "openrouter",
                "modelo": "deepseek-chat",
                "tokens_entrada": 40,
                "tokens_saida": 10,
                "custo_estimado": 0.01,
                "duracao_s": 0.5,
            },
        ]
        itens = [_resultado()]
        relatorio = montar_relatorio(
            itens, CHECKLIST_HASH, "1.1", 1.6, registro_chamadas=registro
        )
        assert relatorio["tokens_por_modelo"]["openrouter/deepseek-chat"] == {
            "entrada": 140,
            "saida": 60,
        }
        assert relatorio["custo_por_modelo"]["openrouter/deepseek-chat"] == pytest.approx(0.03)
        assert relatorio["custo_total"] == pytest.approx(0.03)

    def test_alvo_sem_preco_gera_aviso(self):
        registro = [
            {
                "provedor": "openrouter",
                "modelo": "modelo-sem-preco",
                "tokens_entrada": 100,
                "tokens_saida": 50,
                "custo_estimado": 0.0,
                "duracao_s": 1.0,
            }
        ]
        itens = [_resultado()]
        relatorio = montar_relatorio(
            itens, CHECKLIST_HASH, "1.1", 1.0, registro_chamadas=registro
        )
        assert any("openrouter/modelo-sem-preco" in aviso for aviso in relatorio["avisos"])

    def test_norma_desatualizada_gera_aviso(self):
        tabela = {
            "lei x": {
                "norma": "Lei X",
                "status": "vigente",
                "conferida_em": "2020-01-01",
            }
        }
        itens = [_resultado()]
        relatorio = montar_relatorio(
            itens, CHECKLIST_HASH, "1.1", 1.0, tabela_vigencia=tabela, limiar_dias_vigencia=180
        )
        assert any("Lei X" in aviso for aviso in relatorio["avisos"])

    def test_registro_usa_registro_chamadas_padrao_do_provedor(self):
        uso = UsoModelo(
            provedor="anthropic",
            modelo="claude-opus-4",
            tokens_entrada=10,
            tokens_saida=5,
            custo_estimado=0.001,
            duracao_s=0.2,
        )
        provedores.REGISTRO_CHAMADAS.append(
            {
                "provedor": uso.provedor,
                "modelo": uso.modelo,
                "tokens_entrada": uso.tokens_entrada,
                "tokens_saida": uso.tokens_saida,
                "tokens_cache_leitura": 0,
                "tokens_cache_escrita": 0,
                "custo_estimado": uso.custo_estimado,
                "duracao_s": uso.duracao_s,
            }
        )
        itens = [_resultado()]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 1.0)
        assert "anthropic/claude-opus-4" in relatorio["tokens_por_modelo"]

    def test_nenhum_campo_sensivel_no_relatorio(self):
        itens = [_resultado()]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 1.0)
        serializado = json.dumps(relatorio)
        for termo in ("api_key", "Authorization", "prompt_bruto"):
            assert termo not in serializado

    def test_renderizar_relatorio_contem_proximo_comando(self):
        itens = [_resultado()]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 1.0)
        texto = renderizar_relatorio(relatorio, projeto="ProcessoDemo")
        assert "sysdoc create dvi" in texto
        assert "ProcessoDemo" in texto

    def test_renderizar_relatorio_tem_passos_numerados_e_custo(self):
        itens = [_resultado()]
        relatorio = montar_relatorio(itens, CHECKLIST_HASH, "1.1", 2.5)
        texto = renderizar_relatorio(relatorio)
        assert "1)" in texto
        assert "Custo total estimado" in texto
        assert "Duração total" in texto


# ---------------------------------------------------------------------------
# TestCheckpoint
# ---------------------------------------------------------------------------

class TestCheckpoint:
    def _caminho(self, projeto: Path) -> Path:
        return projeto / ".sysdoc" / "cache" / "dvi_checkpoint.json"

    def test_registrar_item_grava_arquivo(self, tmp_path):
        resultado = _resultado(checklist_id="DVI-GER-050")
        registrar_item(tmp_path, CHECKLIST_HASH, resultado)

        caminho = self._caminho(tmp_path)
        assert caminho.is_file()
        conteudo = json.loads(caminho.read_text(encoding="utf-8"))
        assert conteudo["checklist_hash"] == CHECKLIST_HASH
        assert "DVI-GER-050" in conteudo["itens"]

    def test_carregar_checkpoint_devolve_itens_gravados(self, tmp_path):
        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-051"))
        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-052"))

        itens = carregar_checkpoint(tmp_path, CHECKLIST_HASH)
        assert set(itens) == {"DVI-GER-051", "DVI-GER-052"}
        assert isinstance(itens["DVI-GER-051"], ResultadoItem)
        assert itens["DVI-GER-051"].checklist_id == "DVI-GER-051"

    def test_carregar_checkpoint_com_uso_reconstroi_usomodelo(self, tmp_path):
        uso = UsoModelo(
            provedor="openrouter",
            modelo="deepseek-chat",
            tokens_entrada=10,
            tokens_saida=5,
            custo_estimado=0.01,
            duracao_s=0.5,
        )
        resultado = _resultado(checklist_id="DVI-GER-053", uso=uso)
        registrar_item(tmp_path, CHECKLIST_HASH, resultado)

        itens = carregar_checkpoint(tmp_path, CHECKLIST_HASH)
        assert isinstance(itens["DVI-GER-053"].uso, UsoModelo)
        assert itens["DVI-GER-053"].uso.modelo == "deepseek-chat"

    def test_carregar_checkpoint_hash_diferente_descarta(self, tmp_path):
        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-054"))

        itens = carregar_checkpoint(tmp_path, OUTRO_HASH)
        assert itens == {}
        assert not self._caminho(tmp_path).is_file()

    def test_carregar_checkpoint_arquivo_corrompido_devolve_vazio(self, tmp_path):
        caminho = self._caminho(tmp_path)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("{ isso nao e json valido", encoding="utf-8")

        with pytest.warns(UserWarning):
            itens = carregar_checkpoint(tmp_path, CHECKLIST_HASH)
        assert itens == {}

    def test_carregar_checkpoint_sem_arquivo_devolve_vazio(self, tmp_path):
        assert carregar_checkpoint(tmp_path, CHECKLIST_HASH) == {}

    def test_limpar_checkpoint_remove_arquivo(self, tmp_path):
        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-055"))
        assert self._caminho(tmp_path).is_file()

        limpar_checkpoint(tmp_path)
        assert not self._caminho(tmp_path).is_file()

    def test_limpar_checkpoint_idempotente_sem_arquivo(self, tmp_path):
        limpar_checkpoint(tmp_path)
        limpar_checkpoint(tmp_path)

    def test_retomada_reaproveita_itens_ja_resolvidos(self, tmp_path):
        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-056"))
        itens_primeira_execucao = carregar_checkpoint(tmp_path, CHECKLIST_HASH)
        assert set(itens_primeira_execucao) == {"DVI-GER-056"}

        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-057"))
        itens_segunda_execucao = carregar_checkpoint(tmp_path, CHECKLIST_HASH)
        assert set(itens_segunda_execucao) == {"DVI-GER-056", "DVI-GER-057"}

    def test_escrita_e_atomica_via_tempfile(self, tmp_path):
        registrar_item(tmp_path, CHECKLIST_HASH, _resultado(checklist_id="DVI-GER-058"))
        arquivos_cache = list((tmp_path / ".sysdoc" / "cache").iterdir())
        nomes_temporarios = [f for f in arquivos_cache if f.name.endswith(".tmp")]
        assert nomes_temporarios == []
