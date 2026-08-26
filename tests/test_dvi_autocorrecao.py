"""
Testes de sysdoc_dvi.autocorrecao (P2 - 260826-o2d).

Cobre: mensagem em norma culta de `_verificar_fundamentacao`, parsing dos
erros de acentuação do validador imutável, aplicação determinística das
correções no JSON, e o comportamento ponta a ponta do passo 8 do pipeline
(autocorreção + revalidação única). Nenhum teste chama modelo real.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "templates"))

import sysdoc  # noqa: E402
from sysdoc_dvi import pipeline  # noqa: E402
from sysdoc_dvi.autocorrecao import (  # noqa: E402
    aplicar_correcoes_acentuacao,
    autocorrigir_json,
    coletar_erros_validacao,
    parsear_erros_acentuacao,
)
from sysdoc_dvi.despacho import _verificar_fundamentacao  # noqa: E402
from sysdoc_dvi.tipos import ItemChecklist, ResultadoItem, UsoModelo  # noqa: E402
from validate_sysdoc import validate, validate_portuguese_accents  # noqa: E402


def _dados_validos(**overrides) -> dict:
    parecer_executivo = " ".join(["análise"] * 460)
    parecer_secao = " ".join(["análise"] * 130)
    dados = {
        "titulo": "Documento de Verificação Inicial",
        "subtitulo": "Análise comparativa de ETP e TR",
        "modelo_ia": "claude-opus-4",
        "data_análise": "2026-08-26",
        "schema_version": "1.1",
        "projeto": {
            "órgão": "Secretaria de Teste",
            "processo": "0001/2026",
            "valor_estimado": "R$ 100.000,00",
            "objeto": "Aquisição de materiais de teste",
        },
        "metadados": [
            {"label": "Processo", "valor": "0001/2026"},
        ],
        "documentos_analisados": ["ETP", "TR"],
        "parecer_executivo": parecer_executivo,
        "secao_etp": {
            "classificação_documento": "aprovado",
            "parecer_documento": parecer_secao,
            "numero": "01",
        },
        "secao_tr": {
            "classificação_documento": "aprovado",
            "parecer_documento": parecer_secao,
            "numero": "01",
        },
        "itens": [
            {
                "id": "ETP-001",
                "número": 1,
                "item": "Item 1",
                "documento": "ETP",
                "seção": "3.2",
                "de": "texto original localizado no documento",
                "para": "texto revisado permanece igual ao original",
                "parecer": "Parecer determinístico de teste sem inconsistências identificadas.",
                "fundamento": "Fundamentação de teste sem citação de normativo específico.",
                "classificação": "conforme",
                "severidade": "média",
                "risco_jurídico": "informativo",
                "status_delic": None,
                "alterado_pelo_jurídico": False,
            },
        ],
        "nota_integridade": "Nenhuma inconsistência estrutural identificada nesta análise.",
    }
    dados.update(overrides)
    return dados


class TestMensagemFundamentacaoForaDaBaseLegal:
    def test_mensagem_reclassificacao_passa_no_validador_de_acentuacao(self):
        item = ItemChecklist(
            id="DVI-GER-001",
            aplicabilidade="geral",
            peca="ETP",
            documento_saida="ETP",
            tipo="julgamento",
            pergunta="O objeto está descrito?",
            base_legal_texto="Lei 14.133/2021, art. 18.",
            referencia="art. 18 da Lei 14.133/2021",
            severidade_default="média",
            modelo_alvo="economico",
            ativo=True,
            parametros={},
        )
        resultado = ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="llm",
            documento="ETP",
            seção="1",
            de="trecho localizado no documento original",
            para="trecho localizado no documento original",
            parecer="Parecer determinístico de teste sem inconsistências identificadas.",
            fundamento="Acórdão 1234/2020 do TCU",
            classificação="risco",
            severidade="alta",
            risco_jurídico="relevante",
        )
        reclassificado = _verificar_fundamentacao(resultado, item)
        assert reclassificado.classificação == "pendente"

        erros: list[str] = []
        validate_portuguese_accents(erros, reclassificado.parecer, "itens[1].parecer")
        assert erros == []


class TestParsearErrosAcentuacao:
    def test_extrai_label_encontrado_e_acentuado(self):
        erro = "itens[3].parecer: termo sem acentuação `referencia`; use `referência`"
        correcoes = parsear_erros_acentuacao([erro])
        assert correcoes == [("itens[3].parecer", "referencia", "referência")]

    def test_ignora_erros_de_outra_natureza(self):
        erros = [
            "raiz: campo ausente `titulo`",
            "itens[1]: campo `parecer` está curto demais",
            "itens[2].fundamento: termo sem acentuação `orgao`; use `órgão`",
        ]
        correcoes = parsear_erros_acentuacao(erros)
        assert correcoes == [("itens[2].fundamento", "orgao", "órgão")]


class TestAplicarCorrecoesAcentuacao:
    def test_corrige_todas_as_variantes_de_caixa_com_fronteira_de_palavra(self):
        dados = {"itens": [{}, {}, {"parecer": "sem referencia; ver Referencia e REFERENCIA"}]}
        correcoes = [("itens[3].parecer", "referencia", "referência")]
        resultado, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado["itens"][2]["parecer"] == "sem referência; ver Referência e REFERÊNCIA"
        assert descricoes == ["itens[3].parecer: referencia → referência"]

    def test_forma_canonica_capitalizada_e_usada_literalmente(self):
        dados = {"raiz_teste": None, "titulo": "Sede em brasilia e BRASILIA"}
        correcoes = [("raiz.titulo", "brasilia", "Brasília")]
        resultado, _ = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado["titulo"] == "Sede em Brasília e Brasília"

    def test_nao_vaza_para_vizinhos(self):
        dados = {"itens": [{"parecer": "ver referencias e coreferencia mantidos intactos"}]}
        correcoes = [("itens[1].parecer", "referencia", "referência")]
        resultado, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado["itens"][0]["parecer"] == "ver referencias e coreferencia mantidos intactos"
        assert descricoes == []

    def test_campo_de_nunca_e_alterado(self):
        dados = {"itens": [{"de": "referencia literal nao pode mudar"}]}
        correcoes = [("itens[1].de", "referencia", "referência")]
        resultado, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado["itens"][0]["de"] == "referencia literal nao pode mudar"
        assert descricoes == []

    def test_enderecca_rotulos_raiz_projeto_metadados_secao_e_itens(self):
        dados = {
            "titulo": "referencia",
            "projeto": {"objeto": "referencia"},
            "metadados": [{"label": "referencia"}],
            "secao_etp": {"parecer_documento": "referencia"},
            "itens": [{"fundamento": "referencia"}],
        }
        correcoes = [
            ("raiz.titulo", "referencia", "referência"),
            ("projeto.objeto", "referencia", "referência"),
            ("metadados[1].label", "referencia", "referência"),
            ("secao_etp.parecer_documento", "referencia", "referência"),
            ("itens[1].fundamento", "referencia", "referência"),
        ]
        resultado, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado["titulo"] == "referência"
        assert resultado["projeto"]["objeto"] == "referência"
        assert resultado["metadados"][0]["label"] == "referência"
        assert resultado["secao_etp"]["parecer_documento"] == "referência"
        assert resultado["itens"][0]["fundamento"] == "referência"
        assert len(descricoes) == 5

    def test_rotulo_desconhecido_e_ignorado_sem_excecao(self):
        dados = {"itens": [{"parecer": "referencia"}]}
        correcoes = [("desconhecido.campo", "referencia", "referência")]
        resultado, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado == dados
        assert descricoes == []

    def test_indice_fora_do_intervalo_e_ignorado(self):
        dados = {"itens": [{"parecer": "referencia"}]}
        correcoes = [("itens[9].parecer", "referencia", "referência")]
        resultado, descricoes = aplicar_correcoes_acentuacao(dados, correcoes)
        assert resultado == dados
        assert descricoes == []

    def test_nao_muta_o_dicionario_original(self):
        dados = {"itens": [{"parecer": "referencia"}]}
        original = copy.deepcopy(dados)
        aplicar_correcoes_acentuacao(dados, [("itens[1].parecer", "referencia", "referência")])
        assert dados == original


class TestColetarErrosValidacao:
    def test_devolve_erros_do_validador_real(self, tmp_path):
        json_path = tmp_path / "dados_consolidados.json"
        json_path.write_text(json.dumps({"titulo": "x"}), encoding="utf-8")
        erros = coletar_erros_validacao(tmp_path, json_path)
        assert isinstance(erros, list)
        assert any("campo ausente" in erro for erro in erros)

    def test_retorna_lista_vazia_quando_json_e_invalido(self, tmp_path):
        json_path = tmp_path / "dados_consolidados.json"
        json_path.write_text("{ nao e json valido", encoding="utf-8")
        erros = coletar_erros_validacao(tmp_path, json_path)
        assert erros == []

    def test_retorna_lista_vazia_quando_arquivo_nao_existe(self, tmp_path):
        json_path = tmp_path / "nao_existe.json"
        erros = coletar_erros_validacao(tmp_path, json_path)
        assert erros == []


class TestAutocorrigirJson:
    def test_json_que_so_falha_por_acentuacao_e_corrigido_e_revalida_com_sucesso(self, tmp_path):
        dados = _dados_validos()
        dados["itens"][0]["parecer"] = (
            "Parecer determinístico de teste sem inconsistências, mas com referencia sem acento."
        )
        json_path = tmp_path / "dados_consolidados.json"
        json_path.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

        assert validate(str(json_path), str(tmp_path)) != []

        descricoes = autocorrigir_json(tmp_path, json_path)
        assert descricoes
        assert any("referencia" in descricao for descricao in descricoes)

        assert validate(str(json_path), str(tmp_path)) == []
        corrigido = json.loads(json_path.read_text(encoding="utf-8"))
        assert "referência" in corrigido["itens"][0]["parecer"]
        assert "referencia" not in corrigido["itens"][0]["parecer"].replace("referência", "")

    def test_falha_por_outro_motivo_continua_invalida_apos_autocorrecao(self, tmp_path):
        dados = _dados_validos(modelo_ia="ia")
        dados["itens"][0]["parecer"] = (
            "Parecer determinístico de teste sem inconsistências, mas com referencia sem acento."
        )
        json_path = tmp_path / "dados_consolidados.json"
        json_path.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

        descricoes = autocorrigir_json(tmp_path, json_path)
        assert descricoes

        erros_restantes = validate(str(json_path), str(tmp_path))
        assert erros_restantes
        assert any("modelo_ia" in erro for erro in erros_restantes)

        corrigido = json.loads(json_path.read_text(encoding="utf-8"))
        assert "referência" in corrigido["itens"][0]["parecer"]

    def test_sem_erros_de_acentuacao_nao_toca_no_arquivo(self, tmp_path):
        dados = _dados_validos()
        json_path = tmp_path / "dados_consolidados.json"
        conteudo_original = json.dumps(dados, ensure_ascii=False)
        json_path.write_text(conteudo_original, encoding="utf-8")

        descricoes = autocorrigir_json(tmp_path, json_path)
        assert descricoes == []
        assert json_path.read_text(encoding="utf-8") == conteudo_original


ETP_TEXTO = (
    "Este Estudo Técnico Preliminar descreve a contratação de serviços "
    "continuados de manutenção predial para atendimento das unidades do "
    "órgão, considerando o interesse público e a economicidade da solução "
    "escolhida."
)

TR_TEXTO = (
    "Este Termo de Referência define os critérios de julgamento adotados "
    "para a contratação de serviços continuados de manutenção predial, "
    "especificando as obrigações da contratada e a forma de pagamento "
    "devida."
)


def _preparar_home(tmp_path: Path, nome: str = "home") -> Path:
    home_dir = tmp_path / nome
    sysdoc_dir = home_dir / ".sysdoc"
    sysdoc_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "dvi": {
            "economico": "openrouter/deepseek-chat",
            "forte": "anthropic/claude-opus-4",
            "timeout_s": 30,
            "max_retries": 0,
        },
        "api_keys": {
            "openrouter": "sk-test-openrouter-0000000000",
            "anthropic": "sk-ant-test-0000000000",
        },
    }
    (sysdoc_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return home_dir


def _criar_projeto(tmp_path: Path, nome: str) -> Path:
    projeto = tmp_path / nome
    docs = projeto / "documentos"
    docs.mkdir(parents=True)
    (docs / "ETP.txt").write_text(ETP_TEXTO, encoding="utf-8")
    (docs / "TR.txt").write_text(TR_TEXTO, encoding="utf-8")
    (projeto / "referencias").mkdir()

    sysdoc_dir = projeto / ".sysdoc"
    sysdoc_dir.mkdir()
    config_yaml = {
        "projeto": nome,
        "tipo": "geral",
        "orgao": "Órgão Público de Teste",
        "processo": "00001.000001/2026-01",
        "valor_estimado": "R$ 100.000,00",
        "objeto": "Contratação de serviços continuados de manutenção predial para o órgão",
    }
    (sysdoc_dir / "config.yaml").write_text(
        yaml.safe_dump(config_yaml, allow_unicode=True), encoding="utf-8"
    )
    return projeto


def _escrever_checklist(tmp_path: Path, nome: str = "checklist_teste.yaml") -> Path:
    dados = {
        "versao": "1.0",
        "descricao": "Checklist sintético de teste do pipeline (260826-o2d).",
        "itens": [
            {
                "id": "DVI-GER-001",
                "aplicabilidade": "geral",
                "peca": "ETP",
                "tipo": "presenca",
                "pergunta": "O ETP descreve o objeto da contratação de forma clara?",
                "base_legal_texto": "Regra interna de conformidade documental do órgão.",
                "referencia": "Padrão redacional interno de ETP do órgão",
                "severidade_default": "média",
                "modelo_alvo": "economico",
                "ativo": True,
                "parametros": {},
            },
        ],
    }
    destino = tmp_path / nome
    destino.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return destino


def _trecho_literal(contexto: str, palavras: int = 10) -> str:
    tokens = contexto.strip().split()
    return " ".join(tokens[:palavras])


class AgenteComTermoSemAcento:
    """Agente determinístico cujo parecer contém deliberadamente um termo sem
    acentuação (`referencia`), reproduzindo a falha real de acentuação nascida
    do próprio motor, sem chamada de rede."""

    def __init__(self):
        self.chamadas: list[str] = []
        self.chamadas_sintese: list[str] = []

    def executar_item(self, item, contexto):
        self.chamadas.append(item.id)
        trecho = _trecho_literal(contexto)
        return ResultadoItem(
            checklist_id=item.id,
            origem_verificacao="llm",
            documento=item.documento_saida,
            seção="1",
            de=trecho,
            para=trecho,
            parecer=(
                f"Parecer determinístico de teste para o item {item.id}, sem "
                "inconsistências, mas com referencia sem acento inserida de propósito."
            ),
            fundamento=(
                "Fundamentação de teste baseada na leitura do trecho apresentado "
                "no parecer, sem citação de normativo específico."
            ),
            classificação="conforme",
            severidade="média",
            risco_jurídico="informativo",
            uso=UsoModelo(
                provedor="teste",
                modelo="agente-falso",
                tokens_entrada=10,
                tokens_saida=10,
                custo_estimado=0.0,
                duracao_s=0.01,
            ),
        )

    def executar_lote(self, itens, contexto):
        return [self.executar_item(item, contexto) for item in itens]

    def chamar(self, alvo: str, prompt: str, *, schema: dict | None = None):
        from sysdoc_dvi.provedores import RespostaModelo

        self.chamadas_sintese.append(alvo)
        propriedades = (schema or {}).get("properties", {})
        campo = "parecer_executivo" if "parecer_executivo" in propriedades else "parecer_documento"
        minimo = 460 if campo == "parecer_executivo" else 130
        texto = " ".join(["análise"] * minimo)
        return RespostaModelo(
            conteudo={campo: texto},
            bruto="{}",
            uso=UsoModelo(
                provedor="teste",
                modelo="agente-falso",
                tokens_entrada=10,
                tokens_saida=minimo,
                custo_estimado=0.0,
                duracao_s=0.01,
            ),
        )


class TestPipelineAutocorrigeNoPasso8:
    def test_run_com_termo_sem_acento_autocorrige_revalida_e_gera_html(self, tmp_path, monkeypatch, capsys):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto_dir = _criar_projeto(tmp_path, "ProjetoAutocorrecao")
        checklist_path = _escrever_checklist(tmp_path)
        monkeypatch.chdir(tmp_path)

        agente = AgenteComTermoSemAcento()
        rc = pipeline.executar_run(
            "ProjetoAutocorrecao", tipo="geral", checklist=str(checklist_path), agente=agente
        )

        assert rc == 0
        saida = capsys.readouterr().out
        assert "Autocorreção determinística" in saida

        dados_path = projeto_dir / "dados_consolidados.json"
        dados = json.loads(dados_path.read_text(encoding="utf-8"))
        assert "referência" in dados["itens"][0]["parecer"]

        rc_validate = sysdoc.validate("ProjetoAutocorrecao", str(dados_path))
        assert rc_validate == 0

        htmls = list((projeto_dir / "output").glob("*.html"))
        assert htmls, "HTML não foi gerado apesar da autocorreção"

        relatorios = sorted((projeto_dir / "output").glob("*_relatorio_*.json"))
        assert relatorios
        relatorio = json.loads(relatorios[-1].read_text(encoding="utf-8"))
        assert any("autocorreção de acentuação" in aviso for aviso in relatorio["avisos"])
