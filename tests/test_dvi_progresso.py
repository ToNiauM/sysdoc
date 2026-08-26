"""
Testes de progresso por item no passo 5 do pipeline DVI (P4 - 260826-o2d).

Reaproveita o padrão de projeto sintético e `AgenteFalso` de
`tests/test_dvi_run.py`. Nenhum teste chama modelo real.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sysdoc_dvi import pipeline  # noqa: E402
from sysdoc_dvi.checklist import hash_checklist  # noqa: E402
from sysdoc_dvi.checkpoint import registrar_item  # noqa: E402
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


def _escrever_checklist(tmp_path: Path, nome: str = "checklist_teste.yaml", n_itens: int = 3) -> Path:
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
        "descricao": "Checklist sintético de teste do pipeline (260826-o2d).",
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


class TestProgressoPorItem:
    def test_imprime_uma_linha_por_item_concluido_com_denominador_do_run_atual(
        self, tmp_path, monkeypatch, capsys
    ):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        _criar_projeto(tmp_path, "ProjetoProgresso")
        checklist_path = _escrever_checklist(tmp_path, n_itens=3)
        monkeypatch.chdir(tmp_path)

        agente = AgenteFalso()
        rc = pipeline.executar_run(
            "ProjetoProgresso", tipo="geral", checklist=str(checklist_path), agente=agente
        )
        assert rc == 0

        saida = capsys.readouterr().out
        linhas_progresso = [
            linha for linha in saida.splitlines() if linha.strip().startswith("[") and "]" in linha
        ]
        assert linhas_progresso == [
            "   [1/3] DVI-GER-001: conforme",
            "   [2/3] DVI-GER-002: conforme",
            "   [3/3] DVI-GER-003: conforme",
        ]

    def test_retomada_usa_denominador_dos_itens_pendentes_do_run_atual(
        self, tmp_path, monkeypatch, capsys
    ):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto_dir = _criar_projeto(tmp_path, "ProjetoRetomadaProgresso")
        checklist_path = _escrever_checklist(tmp_path, n_itens=5)
        monkeypatch.chdir(tmp_path)

        agente_1 = AgenteFalso()
        rc1 = pipeline.executar_run(
            "ProjetoRetomadaProgresso", tipo="geral", checklist=str(checklist_path), agente=agente_1
        )
        assert rc1 == 0

        checklist_hash = hash_checklist(checklist_path)
        resultado_base = ResultadoItem(
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
        registrar_item(projeto_dir, checklist_hash, resultado_base)
        registrar_item(
            projeto_dir,
            checklist_hash,
            ResultadoItem(
                checklist_id="DVI-GER-002",
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
            ),
        )

        capsys.readouterr()
        agente_2 = AgenteFalso()
        rc2 = pipeline.executar_run(
            "ProjetoRetomadaProgresso", tipo="geral", checklist=str(checklist_path), agente=agente_2
        )
        assert rc2 == 0

        saida = capsys.readouterr().out
        linhas_progresso = [
            linha for linha in saida.splitlines() if linha.strip().startswith("[") and "]" in linha
        ]
        assert linhas_progresso == [
            "   [1/3] DVI-GER-003: conforme",
            "   [2/3] DVI-GER-004: conforme",
            "   [3/3] DVI-GER-005: conforme",
        ]

    def test_checkpoint_continua_gravado_por_item(self, tmp_path, monkeypatch):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto_dir = _criar_projeto(tmp_path, "ProjetoCheckpointProgresso")
        checklist_path = _escrever_checklist(tmp_path, n_itens=2)
        monkeypatch.chdir(tmp_path)

        agente = AgenteFalso()
        rc = pipeline.executar_run(
            "ProjetoCheckpointProgresso", tipo="geral", checklist=str(checklist_path), agente=agente
        )
        assert rc == 0
        assert not (projeto_dir / ".sysdoc" / "cache" / "dvi_checkpoint.json").is_file()

    def test_sem_itens_pendentes_nenhuma_linha_de_progresso_e_impressa(
        self, tmp_path, monkeypatch, capsys
    ):
        home_dir = _preparar_home(tmp_path)
        monkeypatch.setenv("HOME", str(home_dir))
        projeto_dir = _criar_projeto(tmp_path, "ProjetoSemPendentes")
        checklist_path = _escrever_checklist(tmp_path, n_itens=1)
        monkeypatch.chdir(tmp_path)

        checklist_hash = hash_checklist(checklist_path)
        registrar_item(
            projeto_dir,
            checklist_hash,
            ResultadoItem(
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
            ),
        )

        capsys.readouterr()
        agente = AgenteFalso()
        rc = pipeline.executar_run(
            "ProjetoSemPendentes", tipo="geral", checklist=str(checklist_path), agente=agente
        )
        assert rc == 0
        assert agente.chamadas == []

        saida = capsys.readouterr().out
        linhas_progresso = [
            linha for linha in saida.splitlines() if linha.strip().startswith("[") and "]" in linha
        ]
        assert linhas_progresso == []
