# Gerador de Planilhas Bling ERP

Converte o CSV exportado do Trello em planilhas de importação do Bling ERP.

## Pipeline determinístico

```
CSV do Trello → TrelloAdapter → Produto → Validator → BlingExporter → produtos_bling.csv
```

**Regra fundamental:** O Trello diz. O programa copia. O Bling recebe.  
Nenhuma inferência é feita. Campos ausentes ficam vazios.

## Estrutura

```
app.py              ← Streamlit UI
src/
  config.py         ← Valores fixos + configuração de tags
  domain/produto.py ← Modelo interno neutro
  adapters/trello_adapter.py  ← Lê apenas campos explícitos do Trello
  pipeline/
    validator.py    ← Valida campos obrigatórios e duplicatas
    bling_exporter.py ← Mapeamento determinístico → CSV Bling
    description.py  ← Gera Descrição Curta do template fixo
    tags.py         ← Monta string de tags do Bling
tests/
  test_pipeline.py  ← 42 testes automatizados
```

## Atualizar tag mensal

Editar `src/config.py`:
```python
"valor": "SETEMBRO 2026",   # ← mudar todo mês
```

## Executar localmente

```bash
pip install streamlit pandas
streamlit run app.py
```

## Testes

```bash
python -m pytest tests/ -v
```
