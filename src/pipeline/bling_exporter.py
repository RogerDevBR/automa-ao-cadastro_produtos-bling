# ============================================================
# pipeline/bling_exporter.py — Produto → linhas CSV do Bling
# ============================================================
# Toda coluna tem UMA entrada no _DEPARA. Sem exceções.
# Sem fallback silencioso. Sem inferência.
#
# Tipos de fonte em _DEPARA:
#   "campo"   → getattr(produto, chave)
#   "config"  → bling_defaults[chave]
#   "num2"    → produto.chave formatado como número 2 casas decimais
#   "num3"    → produto.chave formatado como número 3 casas decimais
#   "tags"    → build_tags(tag_config)
#   "desc"    → build_short_description(produto.titulo)
#   ""        → IGNORAR (coluna vazia)
# ============================================================

import pandas as pd
from src.config import COLUNAS_BLING, COLUNAS_CUSTOMIZADAS
from src.domain.produto import Produto
from src.pipeline.description import build_short_description
from src.pipeline.tags import build_tags


# ----------------------------------------------------------
# DE-PARA COMPLETO: Coluna Bling → (tipo_fonte, chave)
#
# Toda coluna das 59 tem entrada aqui.
# A ordem reflete a ordem oficial do modelo Bling.
# ----------------------------------------------------------
_DEPARA: dict = {
    # Col 1
    "ID":                                 ("",       ""),
    # Col 2 ← codigo interno (SKU Bling)
    "Código":                             ("campo",  "codigo"),
    # Col 3
    "Descrição":                          ("campo",  "titulo"),
    # Col 4
    "Unidade":                            ("config", "unidade"),
    # Col 5
    "NCM":                                ("config", "ncm"),
    # Col 6
    "Origem":                             ("config", "origem_tributaria"),
    # Col 7
    "Preço":                              ("config", "preco_venda"),
    # Col 8 — documentação diz IGNORAR
    "Valor IPI fixo":                     ("",       ""),
    # Col 9
    "Observações":                        ("campo",  "observacoes"),
    # Col 10
    "Situação":                           ("",       ""),
    # Col 11
    "Estoque":                            ("num2",   "quantidade"),
    # Col 12
    "Preço de custo":                     ("",       ""),
    # Col 13
    "Cód. no fornecedor":                 ("",       ""),
    # Col 14
    "Fornecedor":                         ("",       ""),
    # Col 15
    "Localização":                        ("",       ""),
    # Col 16
    "Estoque máximo":                     ("",       ""),
    # Col 17
    "Estoque mínimo":                     ("",       ""),
    # Col 18 — Peso LÍQUIDO ignorado (não é fornecido)
    "Peso líquido (Kg)":                  ("",       ""),
    # Col 19 — Peso BRUTO vem do campo peso
    "Peso bruto (Kg)":                    ("num3",   "peso"),
    # Col 20
    "GTIN/EAN":                           ("",       ""),
    # Col 21
    "GTIN/EAN da Embalagem":              ("",       ""),
    # Col 22
    "Largura do produto":                 ("num2",   "largura"),
    # Col 23
    "Altura do Produto":                  ("num2",   "altura"),
    # Col 24
    "Profundidade do produto":            ("num2",   "profundidade"),
    # Col 25
    "Data Validade":                      ("",       ""),
    # Col 26
    "Descrição do Produto no Fornecedor": ("",       ""),
    # Col 27
    "Descrição Complementar":             ("",       ""),
    # Col 28
    "Itens p/ caixa":                     ("",       ""),
    # Col 29
    "Produto Variação":                   ("config", "produto_variacao"),
    # Col 30
    "Tipo Produção":                      ("config", "tipo_producao"),
    # Col 31
    "Classe de enquadramento do IPI":     ("",       ""),
    # Col 32
    "Código na Lista de Serviços":        ("",       ""),
    # Col 33
    "Tipo do item":                       ("config", "tipo_item"),
    # Col 34
    "Grupo de Tags/Tags":                 ("tags",   ""),
    # Col 35
    "Tributos":                           ("",       ""),
    # Col 36
    "Código Pai":                         ("",       ""),
    # Col 37
    "Código Integração":                  ("",       ""),
    # Col 38
    "Grupo de produtos":                  ("",       ""),
    # Col 39
    "Marca":                              ("campo",  "marca"),
    # Col 40
    "CEST":                               ("config", "cest"),
    # Col 41
    "Volumes":                            ("",       ""),
    # Col 42
    "Descrição Curta":                    ("desc",   ""),
    # Col 43
    "Cross-Docking":                      ("",       ""),
    # Col 44
    "URL Imagens Externas":               ("",       ""),
    # Col 45
    "Link Externo":                       ("",       ""),
    # Col 46
    "Meses Garantia no Fornecedor":       ("",       ""),
    # Col 47
    "Clonar dados do pai":                ("",       ""),
    # Col 48
    "Condição do Produto":                ("config", "condicao_produto"),
    # Col 49
    "Frete Grátis":                       ("config", "frete_gratis"),
    # Col 50
    "Número FCI":                         ("",       ""),
    # Col 51
    "Vídeo":                              ("",       ""),
    # Col 52
    "Departamento":                       ("",       ""),
    # Col 53
    "Unidade de Medida":                  ("config", "unidade_medida"),
    # Col 54
    "Preço de Compra":                    ("",       ""),
    # Col 55
    "Valor base ICMS ST para retenção":   ("",       ""),
    # Col 56
    "Valor ICMS ST para retenção":        ("",       ""),
    # Col 57
    "Valor ICMS próprio do substituto":   ("",       ""),
    # Col 58
    "Categoria do produto":               ("campo",  "categoria"),
    # Col 59
    "Informações Adicionais":             ("",       ""),
}

# ----------------------------------------------------------
# DE-PARA CAMPOS CUSTOMIZADOS
#
# numeroDePeca ← produto.numero_peca  (NUNCA = produto.codigo)
# sku          ← produto.codigo       (regra de negócio explícita)
# ----------------------------------------------------------
_DEPARA_CUSTOM: dict = {
    "marca":          ("campo",    "marca"),
    "numeroDePeca":   ("campo",    "numero_peca"),   # NUNCA usa codigo como fallback
    "tipoDeVeiculo":  ("custom_d", "tipo_veiculo"),
    "condicaoDoItem": ("custom_d", "condicao_item"),
    "sku":            ("campo",    "codigo"),         # sku custom = codigo (de-para explícito)
    "modelo":         ("campo",    "modelo"),
    "origem":         ("custom_d", "origem"),
    "fonteDoProduto": ("custom_d", "fonte_produto"),
}


# ----------------------------------------------------------
# Normalização numérica (apenas formato, nunca significado)
# ----------------------------------------------------------
def _num(val: str, decimais: int) -> str:
    """
    Converte string numérica para formato Bling (vírgula decimal).
    Permite apenas normalização de FORMATO.
    Retorna "" se o valor estiver vazio ou não for numérico.
    """
    v = (val or "").strip()
    if not v:
        return ""
    try:
        n = float(v.replace(",", "."))
        return f"{n:.{decimais}f}".replace(".", ",")
    except ValueError:
        return ""   # valor não-numérico → vazio (não inventa)


# ----------------------------------------------------------
# Exporter principal
# ----------------------------------------------------------
class BlingExporter:
    """
    Converte Produto (modelo interno) em linhas dos CSVs do Bling.

    - to_row(produto)        → dict com 59 colunas
    - to_custom_row(produto) → dict com 8 campos customizados
    - export_dataframes(lista) → (df_base, df_custom)
    """

    def __init__(self, bling_defaults: dict, custom_defaults: dict, tag_config: dict):
        self._bling  = bling_defaults
        self._custom = custom_defaults
        # Tags são iguais para todos os produtos — pré-computa uma vez
        self._tags_str = build_tags(tag_config)

    # ----------------------------------------------------------
    def to_row(self, produto: Produto) -> dict:
        """Retorna dict com as 59 colunas Bling preenchidas."""
        row: dict = {}

        for col in COLUNAS_BLING:
            tipo, chave = _DEPARA.get(col, ("", ""))

            if tipo == "campo":
                row[col] = getattr(produto, chave, "")

            elif tipo == "config":
                row[col] = self._bling.get(chave, "")

            elif tipo == "num2":
                row[col] = _num(getattr(produto, chave, ""), 2)

            elif tipo == "num3":
                row[col] = _num(getattr(produto, chave, ""), 3)

            elif tipo == "tags":
                row[col] = self._tags_str

            elif tipo == "desc":
                row[col] = build_short_description(produto.titulo)

            else:  # "" → IGNORAR
                row[col] = ""

        return row

    # ----------------------------------------------------------
    def to_custom_row(self, produto: Produto) -> dict:
        """Retorna dict com os 8 campos customizados Bling."""
        row: dict = {}

        for col in COLUNAS_CUSTOMIZADAS:
            tipo, chave = _DEPARA_CUSTOM.get(col, ("", ""))

            if tipo == "campo":
                row[col] = getattr(produto, chave, "")

            elif tipo == "custom_d":
                row[col] = self._custom.get(chave, "")

            else:
                row[col] = ""

        return row

    # ----------------------------------------------------------
    def export_dataframes(self, produtos: list) -> tuple:
        """
        Converte lista de Produto em dois DataFrames prontos para CSV.
        Retorna (df_base, df_custom).
        """
        rows_base   = [self.to_row(p)        for p in produtos]
        rows_custom = [self.to_custom_row(p) for p in produtos]

        df_base   = pd.DataFrame(rows_base,   columns=COLUNAS_BLING)
        df_custom = pd.DataFrame(rows_custom, columns=COLUNAS_CUSTOMIZADAS)

        return df_base, df_custom
