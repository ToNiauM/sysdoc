"""
Prova de que `sysdoc` e `sysdoc_dvi` são chamáveis como biblioteca pela
camada web, sem `subprocess` da CLI e sem reimplementar pipeline (D-03,
Plano 07-01).

Três frentes, adicionadas incrementalmente pelas Tasks 1-3 deste plano:

- `sysdoc.criar_documento()` devolve os caminhos gerados sem exigir leitura
  de stdout; `sysdoc.create()` continua imprimindo exatamente as mesmas
  linhas de antes (Task 1).
- `sysdoc.localizar_html_analise()` / `sysdoc.localizar_docx_despacho()`
  encontram os artefatos de download sem parsear stdout de `deploy` (Task 2).
- `sysdoc_dvi.pipeline.executar_run(..., progresso=...)` emite eventos
  estruturados a cada etapa, sem alterar a saída de terminal existente
  (Task 3).

Nenhum teste aqui chama modelo real.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import sysdoc  # noqa: E402
from sysdoc_dvi import pipeline  # noqa: E402
from sysdoc_dvi.progresso import EventoProgresso  # noqa: E402
from sysdoc_dvi.tipos import ResultadoItem, UsoModelo  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers compartilhados (Task 1 / Task 2) — mesmo padrão de
# tests/test_dvi_create_variante.py, sem importar o módulo de teste alheio.
# ---------------------------------------------------------------------------

def _base_dvi_json(**overrides) -> dict:
    payload = {
        "modelo_ia": "gpt-5",
        "data_análise": "2026-08-27",
        "projeto": {
            "órgão": "Secretaria de Teste",
            "processo": "90796110000007.000039/2025-14",
            "valor_estimado": "R$ 100.000,00",
            "objeto": "Aquisição de materiais de teste",
        },
        "secao_etp": {
            "classificação_documento": "aprovado_com_ressalvas",
            "parecer_documento": "Parecer da seção ETP consolidado.",
            "numero": "1343011",
        },
        "secao_tr": {
            "classificação_documento": "aprovado",
            "parecer_documento": "Parecer da seção TR consolidado.",
            "numero": "1343014",
        },
        "itens": [
            {
                "id": "ETP-001",
                "documento": "ETP",
                "seção": "4.20",
                "de": "texto original",
                "para": "outro texto",
                "parecer": "Parecer de ajuste necessário sobre o item analisado.",
                "fundamento": "Lei 14.133/2021 art. 18",
                "classificação": "ajuste_necessário",
                "severidade": "média",
                "risco_jurídico": "relevante",
            },
        ],
    }
    payload.update(overrides)
    return payload


def _escrever_dvi_json(project_dir: Path, **overrides) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    json_file = project_dir / "dados_consolidados.json"
    json_file.write_text(
        json.dumps(_base_dvi_json(**overrides), ensure_ascii=False),
        encoding="utf-8",
    )
    return json_file


def _projeto_dvi(tmp_path: Path, nome: str, tipo: str = "geral") -> tuple[Path, "sysdoc.ProjectPaths"]:
    """Roda `sysdoc.init_command(nome)`, marca `tipo` no `.sysdoc/config.yaml`
    e escreve um `dados_consolidados.json` válido. Precisa de `monkeypatch.
    chdir(tmp_path)` já ativo no chamador."""
    sysdoc.init_command(nome)
    project_dir = tmp_path / nome
    paths = sysdoc.project_paths(project_dir)
    config = sysdoc.load_config(paths)
    config["tipo"] = tipo
    sysdoc.write_config(paths, config)
    _escrever_dvi_json(project_dir)
    return project_dir, paths


# ---------------------------------------------------------------------------
# Task 1 — criar_documento() / create()
# ---------------------------------------------------------------------------

class TestCriarDocumento:
    def test_criar_documento_devolve_caminho_sem_ler_stdout(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _projeto_dvi(tmp_path, "ProjetoBiblioteca")

        resultado = sysdoc.criar_documento("ProjetoBiblioteca", "dvi")

        assert isinstance(resultado, sysdoc.ResultadoCreate)
        assert resultado.saida.is_file()
        assert resultado.saida.suffix == ".docx"
        assert resultado.origem_template is not None
        assert resultado.substituicoes_pendentes == 0

    def test_create_ainda_imprime_as_mesmas_linhas_e_retorna_zero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        _projeto_dvi(tmp_path, "ProjetoBibliotecaCli")

        rc = sysdoc.create("ProjetoBibliotecaCli", "dvi")

        saida = capsys.readouterr().out
        assert rc == 0
        assert "DOCX gerado: " in saida
        assert "Template DVI: " in saida


# ---------------------------------------------------------------------------
# Task 2 — localizar_html_analise() / localizar_docx_despacho()
# ---------------------------------------------------------------------------

class TestLocalizarHtmlAnalise:
    def test_devolve_o_html_mais_recente(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoHtml")
        project_dir = tmp_path / "ProjetoHtml"
        paths = sysdoc.project_paths(project_dir)
        paths.output.mkdir(parents=True, exist_ok=True)

        antigo = paths.output / "analise_gpt-5_2026-01-01.html"
        recente = paths.output / "analise_gpt-5_2026-01-02.html"
        antigo.write_text("<html>antigo</html>", encoding="utf-8")
        os.utime(antigo, (time.time() - 100, time.time() - 100))
        recente.write_text("<html>recente</html>", encoding="utf-8")

        encontrado = sysdoc.localizar_html_analise(paths)

        assert encontrado == recente

    def test_devolve_none_sem_nenhum_html(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoSemHtml")
        paths = sysdoc.project_paths(tmp_path / "ProjetoSemHtml")

        assert sysdoc.localizar_html_analise(paths) is None

    def test_localizar_docx_despacho_ignora_docx_de_nome_nao_padrao(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sysdoc.init_command("ProjetoDocx")
        project_dir = tmp_path / "ProjetoDocx"
        paths = sysdoc.project_paths(project_dir)

        (project_dir / "modelo_tr.docx").write_text("x", encoding="utf-8")
        assert sysdoc.localizar_docx_despacho(paths) is None

        despacho = project_dir / "01_projetodocx_dvi_2026-08-27.docx"
        despacho.write_text("x", encoding="utf-8")
        assert sysdoc.localizar_docx_despacho(paths) == despacho


# ---------------------------------------------------------------------------
# Task 3 — progresso estruturado no pipeline DVI
# ---------------------------------------------------------------------------

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


def _criar_projeto_pipeline(tmp_path: Path, nome: str) -> Path:
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


def _escrever_checklist_pipeline(tmp_path: Path, nome: str = "checklist_teste.yaml", n_itens: int = 3) -> Path:
    modelo_item = {
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
    }
    dados = {
        "versao": "1.0",
        "descricao": "Checklist sintético de teste do pipeline (07-01).",
        "itens": [
            {**modelo_item, "id": f"DVI-GER-{indice:03d}"} for indice in range(1, n_itens + 1)
        ],
    }
    destino = tmp_path / nome
    destino.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return destino


def _trecho_literal(contexto: str, palavras: int = 10) -> str:
    tokens = contexto.strip().split()
    return " ".join(tokens[:palavras])


class AgenteFalso:
    def __init__(self):
        self.chamadas: list[str] = []

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
                "inconsistências identificadas na peça analisada."
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


class TestProgressoEstruturado:
    def test_eventos_de_todas_as_etapas_com_total_de_itens_correto(self, tmp_path, monkeypatch):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        _criar_projeto_pipeline(tmp_path, "ProjetoEventos")
        checklist_path = _escrever_checklist_pipeline(tmp_path, n_itens=3)
        monkeypatch.chdir(tmp_path)

        eventos: list[EventoProgresso] = []
        agente = AgenteFalso()
        rc = pipeline.executar_run(
            "ProjetoEventos",
            tipo="geral",
            checklist=str(checklist_path),
            agente=agente,
            progresso=eventos.append,
        )

        assert rc == 0
        assert all(isinstance(evento, EventoProgresso) for evento in eventos)

        eventos_itens = [evento for evento in eventos if evento.etapa == "itens" and evento.total == 3]
        assert eventos_itens, "esperado ao menos um evento de etapa 'itens' com total=3"

        etapas_recebidas = {evento.etapa for evento in eventos}
        for etapa_esperada in (
            "config",
            "checklist",
            "itens",
            "sintese",
            "montagem",
            "validacao",
            "render",
        ):
            assert etapa_esperada in etapas_recebidas

    def test_callback_que_falha_nao_derruba_a_execucao(self, tmp_path, monkeypatch, capsys):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        _criar_projeto_pipeline(tmp_path, "ProjetoCallbackFalho")
        checklist_path = _escrever_checklist_pipeline(tmp_path, n_itens=2)
        monkeypatch.chdir(tmp_path)

        def _callback_com_defeito(evento: EventoProgresso) -> None:
            raise RuntimeError("callback de teste sempre falha")

        agente = AgenteFalso()
        rc = pipeline.executar_run(
            "ProjetoCallbackFalho",
            tipo="geral",
            checklist=str(checklist_path),
            agente=agente,
            progresso=_callback_com_defeito,
        )

        assert rc == 0
        saida = capsys.readouterr().out
        assert "AVISO: callback de progresso falhou:" in saida
