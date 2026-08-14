# ============================================================
# adapters/trello_adapter.py — CSV do Trello → Produto
# ============================================================
# REGRAS ABSOLUTAS (sem exceções):
#   1. Lê apenas colunas explícitas do CSV exportado do Trello.
#   2. Na Card Description, lê SOMENTE pares chave:valor com
#      chaves reconhecidas do template. Ignora texto livre.
#   3. No Card Name, aceita APENAS o padrão "CUSTOM SKU:XXXX"
#      como fonte de 'codigo'. Nenhum outro padrão é aceito.
#   4. NÃO usa regex de texto livre (sem 37x12x18, sem 850g).
#   5. NÃO usa listas hardcoded de marcas/modelos.
#   6. NÃO infere, NÃO assume, NÃO copia campo para outro.
#   7. Campos ausentes ficam como string vazia "".
# ============================================================

import re
import pandas as pd
from src.domain.produto import Produto


# ----------------------------------------------------------
# DE-PARA: nome normalizado de coluna CSV → campo em Produto
#
# Apenas estas colunas são reconhecidas.
# Qualquer outra coluna do Trello é ignorada silenciosamente.
# ----------------------------------------------------------
_COLUNA_PARA_CAMPO: dict = {
    "código(oem):":      "numero_peca",
    "codigo(oem):":      "numero_peca",
    "número de peça:":   "numero_peca",
    "numero de peca:":   "numero_peca",
    "título:":           "titulo",
    "titulo:":           "titulo",
    "categoria:":        "categoria",
    "peso:":             "peso",
    "peso(kg):":         "peso",
    "largura:":          "largura",
    "largura(cm):":      "largura",
    "altura:":           "altura",
    "altura(cm):":       "altura",
    "profundidade:":     "profundidade",
    "profundidade(cm):": "profundidade",
    "quantidade:":       "quantidade",
    "quantidade(un):":   "quantidade",
    "marca:":            "marca",
    "modelo:":           "modelo",
    "observações:":      "observacoes",
    "observacoes:":      "observacoes",
}

# Chaves aceitas na Card Description para o campo 'codigo'
_CODIGO_KEYS: frozenset = frozenset({"código:", "codigo:", "sku:"})

# Único padrão aceito no Card Name para 'codigo'.
# Exemplo: "CUSTOM SKU:S01670"  ou  "SKU:S01670"
_CUSTOM_SKU_RE = re.compile(r'(?:CUSTOM\s+)?SKU\s*:\s*([^\s,|]+)', re.IGNORECASE)


# ----------------------------------------------------------
# Utilitário interno
# ----------------------------------------------------------
def _limpar(val) -> str:
    """Converte qualquer valor para string limpa. Nulos viram ''."""
    if val is None:
        return ""
    if isinstance(val, float) and pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null", ""):
        return ""
    return s


def _extrair_codigo_da_desc(desc: str) -> str:
    """
    Procura SOMENTE as chaves Código:, Codigo:, SKU: na Card Description.
    Ignora todo o restante (texto livre, dimensões, pesos, etc.).
    Retorna string vazia se não encontrar.
    """
    for line in desc.split("\n"):
        linha = line.replace("`", "").strip()
        if ":" not in linha:
            continue
        chave_raw, _, valor_raw = linha.partition(":")
        chave = chave_raw.strip().lower() + ":"
        valor = valor_raw.strip()
        if chave in _CODIGO_KEYS and valor:
            return valor
    return ""


# ----------------------------------------------------------
# Adapter principal
# ----------------------------------------------------------
class TrelloAdapter:
    """
    Transforma linhas do CSV exportado do Trello em instâncias de Produto.

    Princípio: "O Trello diz. O programa copia. O Bling recebe."

    Uso:
        df = pd.read_csv(arquivo, dtype=str).fillna("")
        adapter = TrelloAdapter(df)
        produtos = adapter.parse_dataframe(df)
    """

    def __init__(self, df: pd.DataFrame):
        # Mapeia nome normalizado → nome original de cada coluna do DataFrame
        self._indice_colunas: dict = {
            col.strip().lower(): col
            for col in df.columns
        }

    # ----------------------------------------------------------
    def parse_row(self, row: pd.Series) -> Produto:
        """Converte uma linha do Trello em um Produto. Sem inferência."""
        p = Produto()
        p.source_id   = _limpar(row.get("Card ID",   ""))
        p.source_name = _limpar(row.get("Card Name", ""))

        # ── Passo 1: colunas explícitas do CSV ──────────────────
        # Prioridade máxima: se a coluna existe no CSV e tem valor, usa direto.
        for col_norm, col_original in self._indice_colunas.items():
            campo = _COLUNA_PARA_CAMPO.get(col_norm)
            if not campo:
                continue
            valor = _limpar(row.get(col_original, ""))
            if valor and not getattr(p, campo):
                setattr(p, campo, valor)

        # ── Passo 2: Card Description — apenas campo 'codigo' ───
        # Os demais campos vêm exclusivamente das colunas explícitas (Passo 1).
        # Na Card Description, procuramos APENAS Código:/SKU: para o campo codigo.
        if not p.codigo:
            desc = _limpar(row.get("Card Description", ""))
            if desc:
                p.codigo = _extrair_codigo_da_desc(desc)

        # ── Passo 3: Card Name — padrão CUSTOM SKU:XXXX ─────────
        # Aceita SOMENTE este padrão explícito. Nenhum outro.
        if not p.codigo and p.source_name:
            m = _CUSTOM_SKU_RE.search(p.source_name)
            if m:
                p.codigo = m.group(1).strip()

        # ── Passo 4: campo 'sku' espelha 'codigo' ───────────────
        # Regra de negócio documentada no de-para:
        # o campo customizado 'sku' no Bling = Código interno.
        p.sku = p.codigo

        return p

    # ----------------------------------------------------------
    def parse_dataframe(self, df: pd.DataFrame) -> list:
        """Converte todas as linhas em uma lista de Produto."""
        return [self.parse_row(row) for _, row in df.iterrows()]
