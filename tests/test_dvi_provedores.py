"""
Testes da camada de provedores multi-modelo e do agente de referência
(sysdoc_dvi.config, sysdoc_dvi.provedores, sysdoc_dvi.agente).

Nenhum teste faz rede real: o fixture `_bloquear_rede`, aplicado a todos os
testes, levanta `AssertionError` se `requests.post` for chamado sem um
substituto explícito injetado pelo próprio teste.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi.agente import TEMPLATE_POR_TIPO, AgenteLLM  # noqa: E402
from sysdoc_dvi.config import (  # noqa: E402
    ConfigDvi,
    ErroConfiguracaoModelos,
    carregar_config_dvi,
    chave_do_provedor,
)
from sysdoc_dvi.provedores import (  # noqa: E402
    PROVEDORES,
    ErroProvedor,
    chamar_modelo,
    limpar_registro_chamadas,
)
from sysdoc_dvi.tipos import ItemChecklist  # noqa: E402

_VARS_AMBIENTE = ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def _bloquear_rede(monkeypatch):
    def _falha(*args, **kwargs):
        raise AssertionError("chamada de rede real não permitida em testes")

    monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", _falha)
    limpar_registro_chamadas()
    yield
    limpar_registro_chamadas()


@pytest.fixture(autouse=True)
def _sem_env_de_chaves(monkeypatch):
    for var in _VARS_AMBIENTE:
        monkeypatch.delenv(var, raising=False)


def _configurar_home(tmp_path, monkeypatch, dvi=None, api_keys=None):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".sysdoc"
    config_dir.mkdir(parents=True, exist_ok=True)
    dados = {}
    if dvi is not None:
        dados["dvi"] = dvi
    if api_keys is not None:
        dados["api_keys"] = api_keys
    (config_dir / "config.json").write_text(json.dumps(dados), encoding="utf-8")
    return tmp_path


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload or {}

    def json(self):
        return self._payload


class _PostSpy:
    def __init__(self, respostas):
        self.chamadas = []
        self._respostas = list(respostas)

    def __call__(self, url, headers=None, json=None, timeout=None, **kwargs):
        self.chamadas.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return self._respostas.pop(0)


def _payload_openai_like(conteudo_json, tokens_entrada=10, tokens_saida=5):
    return {
        "choices": [{"message": {"content": json.dumps(conteudo_json, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": tokens_entrada, "completion_tokens": tokens_saida},
    }


def _payload_anthropic(conteudo_json, tokens_entrada=8, tokens_saida=4, cache_leitura=0, cache_escrita=0):
    return {
        "content": [{"type": "text", "text": json.dumps(conteudo_json, ensure_ascii=False)}],
        "usage": {
            "input_tokens": tokens_entrada,
            "output_tokens": tokens_saida,
            "cache_read_input_tokens": cache_leitura,
            "cache_creation_input_tokens": cache_escrita,
        },
    }


def _payload_gemini(conteudo_json, tokens_entrada=12, tokens_saida=6):
    return {
        "candidates": [{"content": {"parts": [{"text": json.dumps(conteudo_json, ensure_ascii=False)}]}}],
        "usageMetadata": {"promptTokenCount": tokens_entrada, "candidatesTokenCount": tokens_saida},
    }


CONTEUDO_VALIDO = {
    "seção": "1",
    "de": "texto original",
    "para": "",
    "parecer": "conforme",
    "fundamento": "art. 18",
    "classificação": "conforme",
    "severidade": "baixa",
    "risco_jurídico": "informativo",
}


class TestConfig:
    def test_sem_arquivo_levanta_erro_com_remedio(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        with pytest.raises(ErroConfiguracaoModelos) as exc_info:
            carregar_config_dvi()
        mensagem = str(exc_info.value)
        assert "economico" in mensagem
        assert "config.json" in mensagem

    def test_sem_economico_levanta_erro(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"forte": "anthropic/claude-opus-4"},
            api_keys={"anthropic": "sk-ant-x"},
        )
        with pytest.raises(ErroConfiguracaoModelos) as exc_info:
            carregar_config_dvi()
        assert "economico" in str(exc_info.value)

    def test_sem_forte_levanta_erro(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"economico": "openrouter/deepseek-chat"},
            api_keys={"openrouter": "sk-or-x"},
        )
        with pytest.raises(ErroConfiguracaoModelos) as exc_info:
            carregar_config_dvi()
        assert "forte" in str(exc_info.value)

    def test_alvo_fora_do_formato_levanta_erro(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"economico": "deepseek-chat", "forte": "anthropic/claude-opus-4"},
            api_keys={"anthropic": "sk-ant-x"},
        )
        with pytest.raises(ErroConfiguracaoModelos):
            carregar_config_dvi()

    def test_provedor_nao_suportado_levanta_erro(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"economico": "foo/bar", "forte": "anthropic/claude-opus-4"},
            api_keys={"anthropic": "sk-ant-x"},
        )
        with pytest.raises(ErroConfiguracaoModelos) as exc_info:
            carregar_config_dvi()
        assert "não suportado" in str(exc_info.value)

    def test_chave_ausente_cita_variavel_de_ambiente(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"economico": "openrouter/deepseek-chat", "forte": "anthropic/claude-opus-4"},
            api_keys={},
        )
        with pytest.raises(ErroConfiguracaoModelos) as exc_info:
            carregar_config_dvi()
        assert "OPENROUTER_API_KEY" in str(exc_info.value)

    def test_flags_sobrepoe_arquivo(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"economico": "openrouter/deepseek-chat", "forte": "anthropic/claude-opus-4"},
            api_keys={"openrouter": "sk-or-x", "anthropic": "sk-ant-x", "openai": "sk-openai-x"},
        )
        config = carregar_config_dvi(economico="openai/gpt-5")
        assert config.economico == "openai/gpt-5"
        assert config.forte == "anthropic/claude-opus-4"

    def test_config_sem_expor_chave(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"economico": "openrouter/deepseek-chat", "forte": "anthropic/claude-opus-4"},
            api_keys={"openrouter": "sk-or-super-secreta", "anthropic": "sk-ant-x"},
        )
        config = carregar_config_dvi()
        assert "sk-or-super-secreta" not in repr(config)
        assert "chave" not in {f for f in vars(config)}
        assert isinstance(config, ConfigDvi)

    def test_chave_do_provedor_usa_variavel_de_ambiente(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
        assert chave_do_provedor("anthropic") == "sk-ant-env"


class TestAdaptadores:
    def test_openrouter_envia_temperatura_zero_e_json_schema(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"openrouter": "sk-or-x"})
        spy = _PostSpy([_FakeResponse(payload=_payload_openai_like(CONTEUDO_VALIDO))])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        resposta = chamar_modelo(
            "openrouter/deepseek-chat", "pergunta", schema={"type": "object"}, timeout_s=30
        )

        assert resposta.conteudo == CONTEUDO_VALIDO
        chamada = spy.chamadas[0]
        assert chamada["url"] == "https://openrouter.ai/api/v1/chat/completions"
        assert chamada["json"]["temperature"] == 0
        assert chamada["json"]["response_format"]["type"] == "json_schema"
        assert chamada["timeout"] == 30

    def test_openai_usa_endpoint_e_json_schema(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"openai": "sk-openai-x"})
        spy = _PostSpy([_FakeResponse(payload=_payload_openai_like(CONTEUDO_VALIDO))])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        chamar_modelo("openai/gpt-5", "pergunta", schema={"type": "object"})

        chamada = spy.chamadas[0]
        assert chamada["url"] == "https://api.openai.com/v1/chat/completions"
        assert chamada["json"]["response_format"]["type"] == "json_schema"
        assert chamada["json"]["temperature"] == 0

    def test_anthropic_usa_endpoint_e_cabecalho_de_versao_sem_response_format(
        self, tmp_path, monkeypatch
    ):
        _configurar_home(tmp_path, monkeypatch, api_keys={"anthropic": "sk-ant-x"})
        spy = _PostSpy([_FakeResponse(payload=_payload_anthropic(CONTEUDO_VALIDO))])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        chamar_modelo("anthropic/claude-opus-4", "pergunta")

        chamada = spy.chamadas[0]
        assert chamada["url"] == "https://api.anthropic.com/v1/messages"
        assert chamada["headers"]["anthropic-version"]
        assert "response_format" not in chamada["json"]
        assert chamada["json"]["temperature"] == 0

    def test_gemini_usa_generate_content_com_response_schema(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"gemini": "sk-gemini-x"})
        spy = _PostSpy([_FakeResponse(payload=_payload_gemini(CONTEUDO_VALIDO))])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        chamar_modelo("gemini/gemini-2-5-pro", "pergunta", schema={"type": "object"})

        chamada = spy.chamadas[0]
        assert "generateContent" in chamada["url"]
        assert chamada["json"]["generationConfig"]["responseMimeType"] == "application/json"
        assert chamada["json"]["generationConfig"]["responseSchema"] == {"type": "object"}
        assert chamada["json"]["generationConfig"]["temperature"] == 0

    def test_provedor_desconhecido_levanta_erro(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch)
        with pytest.raises(ErroProvedor):
            chamar_modelo("foo/bar", "pergunta")

    def test_dicionario_provedores_lista_os_quatro(self):
        assert sorted(PROVEDORES) == ["anthropic", "gemini", "openai", "openrouter"]
        assert PROVEDORES["anthropic"].suporta_cache is True
        assert PROVEDORES["openai"].suporta_cache is False


class TestRetry:
    def test_json_invalido_dispara_um_retry_e_depois_sucede(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"openrouter": "sk-or-x"})
        spy = _PostSpy(
            [
                _FakeResponse(payload={"choices": [{"message": {"content": "não é json"}}], "usage": {}}),
                _FakeResponse(payload=_payload_openai_like(CONTEUDO_VALIDO)),
            ]
        )
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        resposta = chamar_modelo("openrouter/deepseek-chat", "pergunta", max_retries=1)

        assert resposta.conteudo == CONTEUDO_VALIDO
        assert len(spy.chamadas) == 2
        assert "não é json" not in json.dumps(spy.chamadas[0]["json"])

    def test_json_invalido_duas_vezes_levanta_erro_provedor(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"openrouter": "sk-or-x"})
        spy = _PostSpy(
            [
                _FakeResponse(payload={"choices": [{"message": {"content": "invalido 1"}}], "usage": {}}),
                _FakeResponse(payload={"choices": [{"message": {"content": "invalido 2"}}], "usage": {}}),
            ]
        )
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        with pytest.raises(ErroProvedor):
            chamar_modelo("openrouter/deepseek-chat", "pergunta", max_retries=1)
        assert len(spy.chamadas) == 2


class TestSegredo:
    def test_erro_http_401_nao_expoe_chave(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"openai": "sk-openai-secreta-401"})
        spy = _PostSpy([_FakeResponse(status_code=401, payload={"error": "unauthorized"})])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        with pytest.raises(ErroProvedor) as exc_info:
            chamar_modelo("openai/gpt-5", "pergunta")
        assert "sk-openai-secreta-401" not in str(exc_info.value)


class TestUso:
    def test_tokens_custo_e_duracao_sao_preenchidos(self, tmp_path, monkeypatch):
        _configurar_home(
            tmp_path,
            monkeypatch,
            dvi={"precos": {"openrouter/deepseek-chat": {"entrada": 1.0, "saida": 2.0}}},
            api_keys={"openrouter": "sk-or-x"},
        )
        spy = _PostSpy(
            [_FakeResponse(payload=_payload_openai_like(CONTEUDO_VALIDO, tokens_entrada=1000, tokens_saida=500))]
        )
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        resposta = chamar_modelo("openrouter/deepseek-chat", "pergunta")

        assert resposta.uso.tokens_entrada == 1000
        assert resposta.uso.tokens_saida == 500
        assert resposta.uso.custo_estimado == pytest.approx(1000 / 1_000_000 * 1.0 + 500 / 1_000_000 * 2.0)
        assert resposta.uso.duracao_s >= 0

    def test_alvo_sem_preco_registrado_custo_zero(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"openrouter": "sk-or-x"})
        spy = _PostSpy([_FakeResponse(payload=_payload_openai_like(CONTEUDO_VALIDO))])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        resposta = chamar_modelo("openrouter/deepseek-chat", "pergunta")

        assert resposta.uso.custo_estimado == 0.0


class TestCache:
    def test_anthropic_marca_prefixo_com_cache_control(self, tmp_path, monkeypatch):
        _configurar_home(tmp_path, monkeypatch, api_keys={"anthropic": "sk-ant-x"})
        spy = _PostSpy(
            [
                _FakeResponse(
                    payload=_payload_anthropic(
                        CONTEUDO_VALIDO, cache_leitura=100, cache_escrita=50
                    )
                )
            ]
        )
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        resposta = chamar_modelo(
            "anthropic/claude-opus-4",
            "pergunta",
            prefixo_cacheavel="instrução fixa + base legal pública",
        )

        chamada = spy.chamadas[0]
        blocos_system = chamada["json"]["system"]
        assert blocos_system[0]["cache_control"] == {"type": "ephemeral"}
        assert blocos_system[0]["text"] == "instrução fixa + base legal pública"
        assert resposta.tokens_cache_leitura == 100
        assert resposta.tokens_cache_escrita == 50

    @pytest.mark.parametrize("alvo", ["openai/gpt-5", "gemini/gemini-2-5-pro", "openrouter/deepseek-chat"])
    def test_provedor_sem_suporte_a_cache_nao_levanta_e_ignora_marcacao(
        self, tmp_path, monkeypatch, alvo
    ):
        provedor = alvo.split("/")[0]
        _configurar_home(tmp_path, monkeypatch, api_keys={provedor: f"sk-{provedor}-x"})
        if provedor == "gemini":
            payload = _payload_gemini(CONTEUDO_VALIDO)
        else:
            payload = _payload_openai_like(CONTEUDO_VALIDO)
        spy = _PostSpy([_FakeResponse(payload=payload)])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        resposta = chamar_modelo(alvo, "pergunta", prefixo_cacheavel="instrução fixa + base legal")

        chamada = spy.chamadas[0]
        assert "cache_control" not in json.dumps(chamada["json"])
        assert resposta.tokens_cache_leitura == 0
        assert resposta.tokens_cache_escrita == 0


ITEM_BASE = dict(
    id="DVI-GER-001",
    aplicabilidade="ambos",
    peca="ETP",
    documento_saida="ETP",
    pergunta="A necessidade da contratação está descrita?",
    base_legal_texto="Lei 14.133/2021, art. 18",
    referencia="Lei 14.133/2021, art. 18, §1º, I",
    severidade_default="média",
    ativo=True,
)


def _item(tipo, modelo_alvo="economico"):
    dados = dict(ITEM_BASE, tipo=tipo, modelo_alvo=modelo_alvo)
    return ItemChecklist(**dados)


def _config():
    return ConfigDvi(
        economico="openrouter/deepseek-chat",
        forte="anthropic/claude-opus-4",
        limiar_grounding=0.85,
        tolerancia_absoluta="0.01",
        limiar_curadoria_dias=180,
        timeout_s=120,
        max_retries=1,
    )


class TestAgente:
    def test_template_por_tipo_mapeia_presenca_julgamento_calculo(self):
        assert TEMPLATE_POR_TIPO["presenca"] == "item_presenca"
        assert TEMPLATE_POR_TIPO["julgamento"] == "item_julgamento"
        assert TEMPLATE_POR_TIPO["calculo"] == "extracao_precos"

    def test_executar_item_usa_template_certo_por_tipo(self, monkeypatch):
        chamadas_prompt = []

        def duplo_montar_prompt(nome, **kwargs):
            chamadas_prompt.append(nome)
            return f"prompt-{nome}"

        def fake_chamar_modelo(alvo, prompt, **kwargs):
            from sysdoc_dvi.provedores import RespostaModelo
            from sysdoc_dvi.tipos import UsoModelo

            return RespostaModelo(
                conteudo=dict(CONTEUDO_VALIDO),
                bruto="{}",
                uso=UsoModelo(
                    provedor="openrouter", modelo="deepseek-chat",
                    tokens_entrada=1, tokens_saida=1, custo_estimado=0.0, duracao_s=0.0,
                ),
            )

        monkeypatch.setattr("sysdoc_dvi.agente.chamar_modelo", fake_chamar_modelo)
        agente = AgenteLLM(_config(), montar_prompt=duplo_montar_prompt)

        for tipo, esperado in TEMPLATE_POR_TIPO.items():
            agente.executar_item(_item(tipo), "contexto")

        assert chamadas_prompt == list(TEMPLATE_POR_TIPO.values())

    def test_tipo_fora_do_mapa_vira_pendente_sem_excecao(self):
        agente = AgenteLLM(_config())
        resultado = agente.executar_item(_item("vigencia"), "contexto")
        assert resultado.classificação == "pendente"
        assert resultado.falha_estruturada is not None
        assert "vigencia" in resultado.falha_estruturada

    def test_modelo_alvo_economico_seleciona_alvo_configurado(self, monkeypatch):
        alvos_chamados = []

        def fake_chamar_modelo(alvo, prompt, **kwargs):
            from sysdoc_dvi.provedores import RespostaModelo
            from sysdoc_dvi.tipos import UsoModelo

            alvos_chamados.append(alvo)
            return RespostaModelo(
                conteudo=dict(CONTEUDO_VALIDO),
                bruto="{}",
                uso=UsoModelo(
                    provedor="x", modelo="y", tokens_entrada=1, tokens_saida=1,
                    custo_estimado=0.0, duracao_s=0.0,
                ),
            )

        monkeypatch.setattr("sysdoc_dvi.agente.chamar_modelo", fake_chamar_modelo)
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")

        agente.executar_item(_item("presenca", modelo_alvo="economico"), "contexto")
        agente.executar_item(_item("presenca", modelo_alvo="forte"), "contexto")

        assert alvos_chamados == ["openrouter/deepseek-chat", "anthropic/claude-opus-4"]

    def test_falha_provedor_apos_retry_vira_pendente_com_falha_estruturada(self, monkeypatch):
        def fake_chamar_modelo(alvo, prompt, **kwargs):
            raise ErroProvedor("resposta inválida do provedor 'openrouter': erro de parsing")

        monkeypatch.setattr("sysdoc_dvi.agente.chamar_modelo", fake_chamar_modelo)
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")

        resultado = agente.executar_item(_item("presenca"), "contexto")

        assert resultado.classificação == "pendente"
        assert resultado.falha_estruturada == "resposta inválida do provedor 'openrouter': erro de parsing"

    def test_prefixo_cacheavel_nao_inclui_contexto_da_peca(self, monkeypatch):
        prefixos_recebidos = []

        def fake_chamar_modelo(alvo, prompt, prefixo_cacheavel=None, **kwargs):
            from sysdoc_dvi.provedores import RespostaModelo
            from sysdoc_dvi.tipos import UsoModelo

            prefixos_recebidos.append(prefixo_cacheavel)
            return RespostaModelo(
                conteudo=dict(CONTEUDO_VALIDO),
                bruto="{}",
                uso=UsoModelo(
                    provedor="x", modelo="y", tokens_entrada=1, tokens_saida=1,
                    custo_estimado=0.0, duracao_s=0.0,
                ),
            )

        monkeypatch.setattr("sysdoc_dvi.agente.chamar_modelo", fake_chamar_modelo)
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")
        contexto_sigiloso = "TRECHO CONFIDENCIAL DA PEÇA ANALISADA"

        agente.executar_item(_item("presenca"), contexto_sigiloso)

        assert prefixos_recebidos[0] is not None
        assert "Lei 14.133/2021, art. 18" in prefixos_recebidos[0]
        assert contexto_sigiloso not in prefixos_recebidos[0]

    def test_executar_lote_retorna_um_resultado_por_item(self, monkeypatch):
        def fake_chamar_modelo(alvo, prompt, **kwargs):
            from sysdoc_dvi.provedores import RespostaModelo
            from sysdoc_dvi.tipos import UsoModelo

            return RespostaModelo(
                conteudo=dict(CONTEUDO_VALIDO),
                bruto="{}",
                uso=UsoModelo(
                    provedor="x", modelo="y", tokens_entrada=1, tokens_saida=1,
                    custo_estimado=0.0, duracao_s=0.0,
                ),
            )

        monkeypatch.setattr("sysdoc_dvi.agente.chamar_modelo", fake_chamar_modelo)
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")
        itens = [_item("presenca"), _item("julgamento"), _item("vigencia")]

        resultados = agente.executar_lote(itens, "contexto")

        assert len(resultados) == 3
        assert resultados[2].falha_estruturada is not None


LINHAS_TABELA = [
    {
        "descricao": "Combustível automotivo comum",
        "unidade": "litro",
        "quantidade": "5",
        "cotacoes": [
            {"fonte": "Fornecedor A", "valor_unitario": "50.00"},
            {"fonte": "Fornecedor B", "valor_unitario": "52.00"},
            {"fonte": "Fornecedor C", "valor_unitario": "48.00"},
        ],
        "metodo_declarado": "media",
        "unitario_declarado": "60.00",
        "total_declarado": "250.00",
    }
]


class TestAgenteCalculo:
    def _fake_chamar_modelo(self, conteudo):
        from sysdoc_dvi.provedores import RespostaModelo
        from sysdoc_dvi.tipos import UsoModelo

        def _fake(alvo, prompt, **kwargs):
            return RespostaModelo(
                conteudo=conteudo,
                bruto=json.dumps(conteudo, ensure_ascii=False),
                uso=UsoModelo(
                    provedor="openrouter", modelo="deepseek-chat",
                    tokens_entrada=1, tokens_saida=1, custo_estimado=0.0, duracao_s=0.0,
                ),
            )

        return _fake

    def test_calculo_serializa_lista_extraida_no_campo_para(self, monkeypatch):
        monkeypatch.setattr(
            "sysdoc_dvi.agente.chamar_modelo", self._fake_chamar_modelo(list(LINHAS_TABELA))
        )
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")

        resultado = agente.executar_item(_item("calculo"), "contexto")

        assert resultado.classificação == "pendente"
        assert json.loads(resultado.para) == LINHAS_TABELA
        assert resultado.falha_estruturada is None

    def test_calculo_aceita_objeto_com_chave_linhas(self, monkeypatch):
        monkeypatch.setattr(
            "sysdoc_dvi.agente.chamar_modelo",
            self._fake_chamar_modelo({"linhas": list(LINHAS_TABELA)}),
        )
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")

        resultado = agente.executar_item(_item("calculo"), "contexto")

        assert json.loads(resultado.para) == LINHAS_TABELA

    def test_calculo_com_conteudo_nao_lista_vira_pendente_com_falha(self, monkeypatch):
        monkeypatch.setattr(
            "sysdoc_dvi.agente.chamar_modelo", self._fake_chamar_modelo(dict(CONTEUDO_VALIDO))
        )
        agente = AgenteLLM(_config(), montar_prompt=lambda nome, **kw: "prompt")

        resultado = agente.executar_item(_item("calculo"), "contexto")

        assert resultado.classificação == "pendente"
        assert resultado.falha_estruturada is not None
        assert "lista" in resultado.falha_estruturada

    def test_calculo_ponta_a_ponta_com_resposta_http_em_lista(self, tmp_path, monkeypatch):
        from sysdoc_dvi import despacho

        _configurar_home(
            tmp_path, monkeypatch, api_keys={"openrouter": "sk-test-openrouter-000"}
        )
        spy = _PostSpy([_FakeResponse(payload=_payload_openai_like(LINHAS_TABELA))])
        monkeypatch.setattr("sysdoc_dvi.provedores.requests.post", spy)

        agente = AgenteLLM(
            _config(),
            montar_prompt=lambda nome, **kw: "prompt",
            schemas_por_tipo=despacho.SCHEMAS_POR_TIPO,
        )
        resultado = despacho.executar_item(
            _item("calculo"), {"ETP": "tabela de preços da pesquisa"}, agente, tabela_vigencia={}
        )

        assert resultado.origem_verificacao == "deterministico"
        assert resultado.classificação == "risco"
        assert resultado.falha_estruturada is None
        assert "60.00" in resultado.parecer
