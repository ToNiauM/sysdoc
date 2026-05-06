# ROADMAP — SysDoc

> **Para modelos de IA:** Leia `CLAUDE.md` antes de qualquer edição. A fonte única de verdade operacional é `skills/sysdoc/SKILL.md`.
> **Versão atual:** 1.0.0 | **Atualizado em:** 2026-05-06

Este documento organiza as melhorias planejadas para o SysDoc em milestones priorizados. 
Para sessões futuras de IA: **Utilize as checklists de tasks (`- [ ]`) abaixo para organizar seu plano de execução (`task.md`) e rastrear o progresso.**

---

## Como Usar Este Roadmap (Para Agentes de IA)

1. Leia o resumo de tasks no final deste documento ou escolha um Milestone específico.
2. Copie as tasks não marcadas (`- [ ]`) para o seu `task.md` temporário na sessão.
3. Use o **Contexto técnico** e a **Implementação Sugerida** de cada item para guiar seu código.
4. Rode os testes e verifique o **Critério de aceitação**.
5. Marque a task com `[x]` neste ROADMAP.md após concluí-la com sucesso.
6. Atualize o `CHANGELOG.md`.

---

## Milestone 1 — Robustez de Extração de PDF

### M1-A · Migrar PyPDF2 → pypdf
**Prioridade:** Alta | **Dificuldade:** Baixa

**Problema:** `PyPDF2` está deprecado desde 2022. O fork mantido é `pypdf`. O código atual usa `import PyPDF2` em `extract_pdf()` em `sysdoc.py`.

**Localização:** `sysdoc.py`, função `extract_pdf()` (~linha 121).

**Como implementar:**
1. Em `pyproject.toml`, troque `PyPDF2>=3.0.0` por `pypdf>=4.0.0`.
2. Em `sysdoc.py`, troque:
   ```python
   # Antes
   import PyPDF2
   reader = PyPDF2.PdfReader(str(path))
   
   # Depois
   import pypdf
   reader = pypdf.PdfReader(str(path))
   ```
3. A API do `pypdf` é compatível com `PyPDF2 3.x`, então nenhuma outra mudança é necessária.
4. Rode `pip install pypdf` e `pip uninstall PyPDF2`.

**Critério de aceitação:**
- `python -m pytest tests/ -v` passa.
- `sysdoc prepare [pasta-com-pdf]` extrai texto corretamente.

---

### M1-B · Detectar PDFs sem camada de texto e sugerir fallback
**Prioridade:** Média | **Dificuldade:** Média

**Problema:** PDFs escaneados (sem camada OCR) retornam texto vazio. O sistema atual não informa o usuário sobre isso.

**Localização:** `sysdoc.py`, função `extract_pdf()`.

**Como implementar:**
```python
def extract_pdf(path: Path) -> str:
    # ... código existente ...
    text = "\n".join(pages).strip()
    if len(text) < 100:
        print(f"⚠️  {path.name}: texto extraído muito curto ({len(text)} chars).")
        print("   Este PDF pode ser escaneado (sem camada de texto).")
        print("   Tente converter com: pdftotext -layout arquivo.pdf saida.txt")
    return text
```

**Critério de aceitação:** Ao rodar `prepare` com um PDF escaneado, o aviso é impresso sem travar o fluxo.

---

### M1-C · Extração de tabelas em DOCX
**Prioridade:** Baixa | **Dificuldade:** Média

**Problema:** `extract_docx()` em `sysdoc.py` só lê parágrafos (`w:p`). Tabelas (`w:tbl`) são ignoradas, perdendo dados importantes em modelos de referência.

**Localização:** `sysdoc.py`, função `extract_docx()` (~linha 134).

**Como implementar:**
```python
def extract_docx(path: Path) -> str:
    # Após extrair parágrafos, extrair também tabelas:
    for table in root.findall(".//w:tbl", ns):
        for row in table.findall(".//w:tr", ns):
            cells = []
            for cell in row.findall(".//w:tc", ns):
                parts = [n.text for n in cell.findall(".//w:t", ns) if n.text]
                cells.append("".join(parts))
            if cells:
                paragraphs.append(" | ".join(cells))
```

**Critério de aceitação:** DOCX com tabelas produz texto contendo as células separadas por ` | `.

---

## Milestone 2 — Qualidade da Análise LLM

### M2-A · Validação pós-LLM: retry automático com instrução de correção
**Prioridade:** Alta | **Dificuldade:** Média

**Problema:** Se o JSON retornado pela LLM falhar na validação, o usuário precisa rodar manualmente de novo. O `analyze()` deveria tentar uma segunda chamada com os erros como instrução extra.

**Localização:** `sysdoc.py`, função `analyze()` (~linha 553).

**Como implementar:**
```python
# Após gravar o JSON e chamar validate():
if validation != 0:
    errors = run_validate_and_capture(project)
    if errors and attempt < 2:
        extra = f"Corrija os seguintes erros de validação: {'; '.join(errors)}"
        data = call_llm_json(provider, api_key, model, prompt + "\n\n" + extra, schema)
        # tente novamente
```

Criar função auxiliar `run_validate_and_capture(project) -> list[str]` que retorna a lista de erros ao invés de apenas o código de retorno.

**Critério de aceitação:** Se a LLM gerar JSON inválido, uma segunda tentativa é feita automaticamente com os erros no prompt.

---

### M2-B · Suporte a `json_schema` no OpenRouter para modelos OpenAI
**Prioridade:** Média | **Dificuldade:** Baixa

**Problema:** `call_openrouter_json()` usa `json_object` para todos os modelos. Quando o modelo selecionado no OpenRouter é um modelo OpenAI (ex.: `openai/gpt-4o`), o OpenRouter aceita `json_schema` formal, gerando saídas mais confiáveis.

**Localização:** `sysdoc.py`, função `call_openrouter_json()`.

**Como implementar:**
```python
def call_openrouter_json(api_key, model, prompt, schema):
    # Detectar se é modelo OpenAI roteado pelo OpenRouter
    use_schema = model.startswith("openai/") or model.startswith("google/")
    return _call_openai_compatible_json(
        ...,
        use_json_schema=use_schema,
    )
```

**Critério de aceitação:** `sysdoc analyze` com `--model openai/gpt-4o` usa `json_schema`; com `--model mistralai/mistral-7b` usa `json_object`.

---

### M2-C · Campo `de` com suporte a `[OMISSÃO: descrição]`
**Prioridade:** Média | **Dificuldade:** Baixa

**Problema:** Quando um item documenta ausência de cláusula, o campo `de` não tem texto literal para rastrear. O validador aceita `[OMISSÃO]` mas a SKILL não documenta claramente como formatar.

**Localização:** `skills/sysdoc/SKILL.md` e `templates/validate_sysdoc.py`.

**Como implementar:**
1. Documentar em `SKILL.md` o formato exato: `[OMISSÃO: descrição do que está ausente]`
2. Em `validate_sysdoc.py`, melhorar a regex do marcador:
   ```python
   def is_omissao_marker(text: str) -> bool:
       return bool(re.match(r"\[OMISS[ÃA]O[:\s]", str(text or ""), re.IGNORECASE))
   ```

**Critério de aceitação:** `[OMISSÃO: ausência de cláusula de garantia]` passa na validação de rastreabilidade; `[OMISSAO]` (sem acento) também.

---

## Milestone 3 — Interface e Experiência do Usuário

### M3-A · Comando `sysdoc status` com output tabular
**Prioridade:** Média | **Dificuldade:** Baixa

**Problema:** O `status` atual emite texto simples. Com muitos projetos, fica difícil de ler.

**Localização:** `sysdoc.py`, função `status()` (~linha 355).

**Como implementar:**
```python
def status() -> int:
    # Header
    header = f"{'PROJETO':<30} {'ETP':>5} {'TR':>5} {'MODELOS':>8} {'JSON':>5} {'HTML':>5} {'PREP':>5}"
    print(header)
    print("-" * len(header))
    for directory in sorted(...):
        # formatar como linha de tabela
        print(f"{directory.name:<30} {'ok' if has_etp else '---':>5} ...")
```

**Critério de aceitação:** `sysdoc status` exibe uma tabela alinhada com colunas claramente rotuladas.

---

### M3-B · GUI: campo de instrução extra antes de Analisar
**Prioridade:** Média | **Dificuldade:** Baixa

**Problema:** A GUI não expõe o `--instruction` do `analyze`. O usuário precisa usar a CLI para passar instruções extras (ex.: "foco em garantia contratual").

**Localização:** `sysdoc_gui.py`, método `_build()` e `run_command()`.

**Como implementar:**
1. Adicionar `Entry` para instrução extra abaixo do campo de modelo:
   ```python
   self.instruction_var = StringVar()
   Label(model_bar, text="Instrução extra").pack(side=LEFT)
   Entry(model_bar, textvariable=self.instruction_var, width=40).pack(side=LEFT, padx=4)
   ```
2. Em `run_command()`, ao montar `args` para `analyze`:
   ```python
   instruction = self.instruction_var.get().strip()
   if instruction:
       args.extend(["--instruction", instruction])
   ```

**Critério de aceitação:** Digitando texto no campo e clicando "Analisar com LLM", o argumento `--instruction` é passado ao subprocess.

---

### M3-C · Comando `sysdoc compare [pasta]`
**Prioridade:** Baixa | **Dificuldade:** Alta

**Problema:** Quando múltiplos modelos analisam o mesmo projeto, não há forma de comparar os resultados via CLI.

**Localização:** Novo subcomando em `sysdoc.py`.

**Como implementar:**
```python
def compare(project: str) -> int:
    """Lista todos os JSONs versionados e compara número de itens, classificações e riscos."""
    paths = project_paths(project)
    jsons = sorted(paths.root.glob("dados_consolidados_*.json"))
    if not jsons:
        print("Nenhuma versão encontrada. Rode 'sysdoc publish' para versionar.")
        return 1
    for json_file in jsons:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        itens = data.get("itens", [])
        modelo = data.get("modelo_ia", "?")
        data_a = data.get("data_análise", "?")
        bloq = sum(1 for i in itens if i.get("risco_jurídico") == "bloqueante")
        print(f"{json_file.name}: modelo={modelo} data={data_a} itens={len(itens)} bloqueantes={bloq}")
    return 0
```

**Critério de aceitação:** `sysdoc compare Combustivel` lista todos os JSONs versionados com resumo de itens e riscos por modelo.

---

## Milestone 4 — Testes e Qualidade de Código

### M4-A · Cobertura de testes para sysdoc.py (funções de preparação)
**Prioridade:** Alta | **Dificuldade:** Média

**Problema:** `tests/test_validate.py` cobre o validador e utilidades. As funções de preparação (`prepare`, `render_context`, `detect_object`, `detect_values`) não têm testes.

**Localização:** Criar `tests/test_prepare.py`.

**Testes a implementar:**
```python
# tests/test_prepare.py
def test_detect_values_extracts_brl():
    texts = {"ETP": "O valor estimado é R$ 1.234.567,89"}
    assert "R$ 1.234.567,89" in detect_values(texts)

def test_detect_object_finds_contratacao():
    texts = {"TR": "A contratação tem por objeto a aquisição de veículos leves."}
    obj = detect_object(texts)
    assert "contratação" in obj.lower()

def test_render_context_includes_sections():
    # Montar fixture de manifest + texts mínimos
    context = render_context(paths_fixture, manifest_fixture, texts_fixture)
    assert "## Mapa De Seções" in context
    assert "## Extratos Orientadores" in context
```

**Critério de aceitação:** `pytest tests/test_prepare.py -v` passa com ≥ 5 testes.

---

### M4-B · Lint e formatação com Ruff
**Prioridade:** Baixa | **Dificuldade:** Baixa

**Problema:** O projeto não tem linter configurado, dificultando contribuições consistentes.

**Como implementar:**
1. Adicionar ao `pyproject.toml`:
   ```toml
   [tool.ruff]
   line-length = 100
   select = ["E", "F", "W", "I"]
   ignore = ["E501"]  # linhas longas no prompt LLM são aceitáveis
   ```
2. Adicionar ao `[project.optional-dependencies]`:
   ```toml
   dev = ["pytest>=7.0", "ruff>=0.4"]
   ```
3. Corrigir os avisos com `ruff check . --fix`.

**Critério de aceitação:** `ruff check .` retorna 0 warnings.

---

## Milestone 5 — Distribuição e Deploy

### M5-A · GitHub Actions CI
**Prioridade:** Média | **Dificuldade:** Baixa

**Problema:** Não há integração contínua. Pull requests podem quebrar testes sem aviso.

**Como implementar:** Criar `.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -v
```

**Critério de aceitação:** O workflow executa e passa no GitHub.

---

### M5-B · Publicação no PyPI
**Prioridade:** Baixa | **Dificuldade:** Baixa

**Problema:** O SysDoc só é instalável via `pip install -e .` a partir do clone local.

**Pré-requisito:** M5-A (CI) deve estar funcionando.

**Como implementar:**
1. Garantir que `pyproject.toml` está completo (✅ já feito na v1.0.0).
2. Criar `.github/workflows/publish.yml` que roda em `push de tag v*`:
   ```yaml
   - run: pip install build twine
   - run: python -m build
   - run: twine upload dist/*
   ```
3. Configurar `PYPI_TOKEN` nos secrets do repositório.

**Critério de aceitação:** `pip install sysdoc` funciona após publicação.

---

## 📝 Tasks Consolidadas (Master Checklist)

Agentes: Ao começar a trabalhar no projeto, copie estas tasks para o seu `task.md` e, ao finalizar, atualize este `ROADMAP.md` marcando a task como `[x]`.

### Milestone 1 — Robustez de Extração de PDF
- [x] **M1-A**: Migrar dependência `PyPDF2` para `pypdf` em `pyproject.toml` e refatorar imports em `sysdoc.py`.
- [x] **M1-B**: Modificar `extract_pdf` em `sysdoc.py` para detectar textos extraídos com menos de 100 caracteres e printar aviso de possível PDF escaneado.
- [x] **M1-C**: Estender `extract_docx` em `sysdoc.py` para extrair não só parágrafos (`w:p`), mas também tabelas (`w:tbl`).

### Milestone 2 — Qualidade da Análise LLM
- [x] **M2-A**: Na função `analyze` em `sysdoc.py`, se a validação pós-LLM falhar, fazer um retry automático repassando a lista de erros da validação na instrução do prompt.
- [x] **M2-B**: Na função `call_openrouter_json` em `sysdoc.py`, usar `response_format={"type": "json_schema"}` condicionalmente quando o modelo for da OpenAI (`openai/`) ou Google (`google/`).
- [ ] **M2-C**: Documentar o uso de `[OMISSÃO: justificativa]` no `SKILL.md` e suportar este padrão na regex do `validate_sysdoc.py`.

### Milestone 3 — Interface e Experiência do Usuário
- [x] **M3-A**: Refatorar a saída da função `status()` em `sysdoc.py` para renderizar uma tabela alinhada ao invés de texto simples.
- [x] **M3-B**: Na GUI (`sysdoc_gui.py`), adicionar um `Entry` para "Instrução extra" e repassar o valor usando a flag `--instruction` ao chamar `analyze`.
- [x] **M3-C**: Criar o comando `sysdoc compare [pasta]` em `sysdoc.py` para iterar sobre múltiplos JSONs versionados e gerar um relatório comparativo na tela.

### Milestone 4 — Testes e Qualidade de Código
- [ ] **M4-A**: Criar `tests/test_prepare.py` com testes para `detect_values`, `detect_object` e `render_context` em `sysdoc.py`.
- [x] **M4-B**: Adicionar configuração do linter `ruff` no `pyproject.toml` (dependências e regras) e rodar `ruff check . --fix`.

### Milestone 5 — Distribuição e Deploy
- [ ] **M5-A**: Criar o workflow do GitHub Actions em `.github/workflows/ci.yml` rodando o `pytest` a cada push/PR.
- [ ] **M5-B**: Criar o workflow do GitHub Actions em `.github/workflows/publish.yml` para publicar no PyPI em push de tags de versão.

---

## Regras Inegociáveis para Qualquer Contribuição

> [!IMPORTANT]
> Leia e siga antes de qualquer edição:

1. **`templates/analise_template.html` e `templates/render_analise.py` são imutáveis.** Nunca edite durante análise.
2. **`skills/sysdoc/SKILL.md` é a fonte única de verdade operacional.** Toda mudança de fluxo vai aqui.
3. **Rode `python -m pytest tests/ -v` antes e depois de qualquer mudança.**
4. **`modelo_ia` no JSON deve ser slug minúsculo real** (ex.: `claude-sonnet-4-6`, não `claude`).
5. **Não invente artigos, acórdãos, números SEI, datas ou valores.** Use `pendente`.
6. **Todo campo gerado em português brasileiro culto com acentuação correta.** O campo `de` preserva literalidade.
7. **Atualize `CHANGELOG.md`** com o que foi alterado, versão e data.

---

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.1.0 | 2026-05-06 | M1-A/B/C: pypdf, aviso PDF escaneado, extração de tabelas DOCX. M2-A/B: retry automático com erros de validação, json_schema no OpenRouter. M3-A/B/C: status tabular, GUI instrução extra, comando compare. M4-B: ruff. |
| 1.0.0 | 2026-05-06 | Primeira versão estável. CLI completo com connect/models/init/analyze/--dry-run. Retry LLM com backoff. GUI melhorada. 27 testes automatizados. |
| 0.x | 2026-04-27 | Versão inicial com CLI básico e fluxo IA-agnóstico. |
