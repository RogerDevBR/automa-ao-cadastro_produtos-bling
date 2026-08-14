# ============================================================
# domain/produto.py — Modelo interno neutro de produto
# ============================================================
# Esta classe representa um produto de forma INDEPENDENTE
# de qualquer ferramenta de origem (Trello) ou destino (Bling).
#
# REGRA: cada campo é preenchido APENAS com dados explicitamente
# fornecidos pela fonte. Campos ausentes ficam como string vazia "".
#
# Não coloque lógica de negócio aqui — este é apenas o contrato.
# ============================================================

from dataclasses import dataclass


@dataclass
class Produto:
    # ── Rastreabilidade ──────────────────────────────────────────
    source_id:     str = ""   # ID do card na origem (Card ID do Trello)
    source_name:   str = ""   # Nome bruto do card (para mensagens de erro)

    # ── Dados do produto ─────────────────────────────────────────
    codigo:        str = ""   # Código interno / SKU para o Bling (Coluna "Código")
    titulo:        str = ""   # Título / Descrição do produto
    categoria:     str = ""   # Categoria completa (caminho Bling)
    peso:          str = ""   # Peso bruto em Kg (string, separador vírgula)
    largura:       str = ""   # Largura em cm
    altura:        str = ""   # Altura em cm
    profundidade:  str = ""   # Profundidade em cm
    quantidade:    str = ""   # Quantidade em estoque
    observacoes:   str = ""   # Observações livres

    # ── Campos customizados ──────────────────────────────────────
    marca:         str = ""   # Marca do fabricante
    numero_peca:   str = ""   # Número de peça original (OEM) — NUNCA = codigo
    modelo:        str = ""   # Modelo do veículo compatível
    tipo_veiculo:  str = ""   # Tipo de veículo
    condicao_item: str = ""   # Condição do item
    sku:           str = ""   # SKU customizado Bling (= codigo, por regra de negócio)
    origem:        str = ""   # Origem do produto (campo custom)
    fonte_produto: str = ""   # Fonte do produto (campo custom)
