"""
Teste ponta a ponta do orquestrador DVI (sysdoc_dvi.pipeline / sysdoc_dvi.cli).

Monta um projeto sintético completo em `tmp_path` (documentos de ETP/TR com
texto literal, `.sysdoc/config.yaml` com `tipo: geral` e um
`~/.sysdoc/config.json` de teste com `HOME` monkeypatchado) e substitui o
agente de análise/síntese por `AgenteFalso`, determinístico e sem rede.
Nenhum teste importa `requests` nem faz chamada HTTP real.
"""

from __future__ import annotations

import json
import stat
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import sysdoc  # noqa: E402
from sysdoc_dvi import cli, pipeline  # noqa: E402
from sysdoc_dvi.checklist import hash_checklist  # noqa: E402
from sysdoc_dvi.checkpoint import registrar_item  # noqa: E402
from sysdoc_dvi.provedores import RespostaModelo  # noqa: E402
from sysdoc_dvi.tipos import ResultadoItem, UsoModelo  # noqa: E402

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


def _criar_projeto(tmp_path: Path, nome: str, com_etp: bool = True, com_tr: bool = True) -> Path:
    projeto = tmp_path / nome
    docs = projeto / "documentos"
    docs.mkdir(parents=True)
    if com_etp:
        (docs / "ETP.txt").write_text(ETP_TEXTO, encoding="utf-8")
    if com_tr:
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
        "descricao": "Checklist sintético de teste do pipeline (05-14).",
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
            {
                "id": "DVI-GER-002",
                "aplicabilidade": "geral",
                "peca": "TR",
                "tipo": "julgamento",
                "pergunta": "O critério de julgamento adotado no TR é adequado ao objeto?",
                "base_legal_texto": "Regra interna de conformidade documental do órgão.",
                "referencia": "Padrão redacional interno de TR do órgão",
                "severidade_default": "alta",
                "modelo_alvo": "forte",
                "ativo": True,
                "parametros": {},
            },
            {
                "id": "DVI-GER-003",
                "aplicabilidade": "geral",
                "peca": "TR",
                "tipo": "presenca",
                "pergunta": "O TR descreve as obrigações da contratada?",
                "base_legal_texto": "Regra interna de conformidade documental do órgão.",
                "referencia": "Padrão redacional interno de TR do órgão",
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


class AgenteFalso:
    """Agente determinístico: cobre `AnalysisAgent` (execução de itens) e
    `AgenteSintese` (`.chamar`) sem nenhuma chamada de rede."""

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

    def chamar(self, alvo: str, prompt: str, *, schema: dict | None = None) -> RespostaModelo:
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
                tokens_entrada=100,
                tokens_saida=100,
                custo_estimado=0.0,
                duracao_s=0.01,
            ),
        )


class TestAbortSemConfig:
    def test_sem_config_aborta_antes_de_qualquer_arquivo(self, tmp_path, monkeypatch):
        home_dir = tmp_path / "home_vazio"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))
        projeto = _criar_projeto(tmp_path, "ProjetoSemConfig")
        checklist_path = _escrever_checklist(tmp_path)
        monkeypatch.chdir(tmp_path)

        rc = pipeline.executar_run(
            "ProjetoSemConfig", tipo="geral", checklist=str(checklist_path)
        )

        assert rc == 1
        assert not (projeto / ".sysdoc" / "cache" / "manifest.json").is_file()
        assert not (projeto / "dados_consolidados.json").is_file()


class TestAbortSemPeca:
    def test_peca_obrigatoria_ausente_aborta_com_remedio(self, tmp_path, monkeypatch, capsys):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto = _criar_projeto(tmp_path, "ProjetoSemPeca", com_tr=False)
        checklist_path = _escrever_checklist(tmp_path)
        monkeypatch.chdir(tmp_path)

        rc = pipeline.executar_run(
            "ProjetoSemPeca", tipo="geral", checklist=str(checklist_path)
        )

        assert rc == 1
        assert not (projeto / "dados_consolidados.json").is_file()
        saida = capsys.readouterr().out
        assert "pecas:" in saida
        assert "TR" in saida


class TestRunCompleto:
    def test_run_completo_gera_json_html_e_relatorio(self, tmp_path, monkeypatch):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto_dir = _criar_projeto(tmp_path, "ProjetoCompleto")
        checklist_path = _escrever_checklist(tmp_path)
        monkeypatch.chdir(tmp_path)

        agente = AgenteFalso()
        rc = pipeline.executar_run(
            "ProjetoCompleto", tipo="geral", checklist=str(checklist_path), agente=agente
        )

        assert rc == 0
        dados_path = projeto_dir / "dados_consolidados.json"
        assert dados_path.is_file()

        rc_validate = sysdoc.validate("ProjetoCompleto", str(dados_path))
        assert rc_validate == 0

        htmls = list((projeto_dir / "output").glob("*.html"))
        assert htmls, "HTML não foi gerado em output/"

        relatorios = list((projeto_dir / "output").glob("*_relatorio_*.json"))
        assert relatorios, "Relatório não foi gravado em output/"

        assert len(agente.chamadas) == 3
        assert not (projeto_dir / ".sysdoc" / "cache" / "dvi_checkpoint.json").is_file()


class TestRetomada:
    def test_segunda_execucao_pula_itens_ja_resolvidos(self, tmp_path, monkeypatch):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto_dir = _criar_projeto(tmp_path, "ProjetoRetomada")
        checklist_path = _escrever_checklist(tmp_path)
        monkeypatch.chdir(tmp_path)

        agente_1 = AgenteFalso()
        rc1 = pipeline.executar_run(
            "ProjetoRetomada", tipo="geral", checklist=str(checklist_path), agente=agente_1
        )
        assert rc1 == 0
        assert len(agente_1.chamadas) == 3

        checklist_hash = hash_checklist(checklist_path)
        resultado_etp = ResultadoItem(
            checklist_id="DVI-GER-001",
            origem_verificacao="llm",
            documento="ETP",
            seção="1",
            de="Este Estudo Técnico Preliminar descreve a",
            para="Este Estudo Técnico Preliminar descreve a",
            parecer="Parecer previamente resolvido para fins de teste de retomada.",
            fundamento="Fundamentação previamente resolvida, sem citação de normativo.",
            classificação="conforme",
            severidade="média",
            risco_jurídico="informativo",
        )
        resultado_tr = replace(
            resultado_etp,
            checklist_id="DVI-GER-002",
            documento="TR",
            de="Este Termo de Referência define os",
            para="Este Termo de Referência define os",
        )
        registrar_item(projeto_dir, checklist_hash, resultado_etp)
        registrar_item(projeto_dir, checklist_hash, resultado_tr)

        agente_2 = AgenteFalso()
        rc2 = pipeline.executar_run(
            "ProjetoRetomada", tipo="geral", checklist=str(checklist_path), agente=agente_2
        )

        assert rc2 == 0
        assert agente_2.chamadas == ["DVI-GER-003"]
        assert len(agente_2.chamadas) < len(agente_1.chamadas)


class TestCli:
    def test_run_dispatch_chama_executar_run_com_argumentos(self, monkeypatch, tmp_path):
        capturado = {}

        def fake_executar_run(projeto, tipo=None, checklist=None, economico=None, forte=None, retomar=True, agente=None):
            capturado.update(
                projeto=projeto,
                tipo=tipo,
                checklist=checklist,
                economico=economico,
                forte=forte,
                retomar=retomar,
            )
            return 0

        monkeypatch.setattr(pipeline, "executar_run", fake_executar_run)

        rc = cli.main(
            [
                "run",
                str(tmp_path),
                "--tipo",
                "tic",
                "--economico",
                "openrouter/x",
                "--forte",
                "anthropic/y",
                "--no-resume",
            ]
        )

        assert rc == 0
        assert capturado["projeto"] == str(tmp_path)
        assert capturado["tipo"] == "tic"
        assert capturado["economico"] == "openrouter/x"
        assert capturado["forte"] == "anthropic/y"
        assert capturado["retomar"] is False

    def test_relatorio_sem_relatorio_informa_comando_e_sai_com_1(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        project_dir = tmp_path / "ProjetoSemRelatorio"
        project_dir.mkdir()

        rc = cli.main(["relatorio", str(project_dir)])

        assert rc == 1

    def test_relatorio_reimprime_ultimo_relatorio_sem_reexecutar(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "ProjetoComRelatorio"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True)
        relatorio_dados = {
            "itens_por_status": {"conforme": 1},
            "itens_por_tipo": {"ETP": 1},
            "itens_por_origem": {"llm": 1},
            "falhas_grounding": {"total": 0, "itens": []},
            "falhas_estruturadas": {"total": 0, "itens": []},
            "tokens_por_modelo": {},
            "custo_por_modelo": {},
            "custo_total": 0.0,
            "duracao_total_s": 1.23,
            "checklist_hash": "0" * 64,
            "schema_version": "1.1",
            "pecas_mapeadas": {},
            "avisos": [],
        }
        (output_dir / "01_projetocomrelatorio_relatorio_2026-08-26.json").write_text(
            json.dumps(relatorio_dados), encoding="utf-8"
        )

        chamou_executar_run = []
        monkeypatch.setattr(
            pipeline, "executar_run", lambda *a, **kw: chamou_executar_run.append(True) or 0
        )

        rc = cli.main(["relatorio", str(project_dir)])

        assert rc == 0
        assert chamou_executar_run == []

    def test_config_dispatch_grava_secao_dvi(self, tmp_path, monkeypatch):
        home_dir = tmp_path / "home_cli"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        rc = cli.main(["config", "--economico", "openrouter/x", "--forte", "anthropic/y"])

        assert rc == 0
        config_path = home_dir / ".sysdoc" / "config.json"
        assert config_path.is_file()
        dados = json.loads(config_path.read_text(encoding="utf-8"))
        assert dados["dvi"]["economico"] == "openrouter/x"
        assert dados["dvi"]["forte"] == "anthropic/y"


class TestConfigSegredo:
    def test_listar_nao_vaza_chave(self, tmp_path, monkeypatch, capsys):
        home_dir = tmp_path / "home_segredo"
        sysdoc_dir = home_dir / ".sysdoc"
        sysdoc_dir.mkdir(parents=True)
        chave_secreta = "sk-SEGREDOMUITOLONGO1234567890"
        config = {
            "dvi": {"economico": "openrouter/deepseek-chat", "forte": "anthropic/claude-opus-4"},
            "api_keys": {"openrouter": chave_secreta},
        }
        (sysdoc_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
        monkeypatch.setenv("HOME", str(home_dir))

        rc = cli.config(listar=True)

        assert rc == 0
        saida = capsys.readouterr().out
        assert chave_secreta not in saida
        assert chave_secreta[:8] not in saida
        assert "configurada" in saida
        assert "ausente" in saida

    def test_config_grava_permissoes_restritas(self, tmp_path, monkeypatch):
        home_dir = tmp_path / "home_perm"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        rc = cli.config(economico="openrouter/x", forte="anthropic/y")
        assert rc == 0

        config_path = home_dir / ".sysdoc" / "config.json"
        modo_arquivo = stat.S_IMODE(config_path.stat().st_mode)
        modo_dir = stat.S_IMODE(config_path.parent.stat().st_mode)
        assert modo_arquivo == 0o600
        assert modo_dir == 0o700
