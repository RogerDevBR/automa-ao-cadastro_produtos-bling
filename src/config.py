# ============================================================
# config.py — Configuração central do pipeline Trello → Bling
# ============================================================
# TODOS os valores fixos e configurações estão definidos AQUI.
# Não espalhe constantes em outras funções.
# ============================================================

# ----------------------------------------------------------
# Valores fixos do Bling (não vêm do Trello)
# ----------------------------------------------------------
BLING_DEFAULTS: dict = {
    "unidade":           "UN",
    "preco_venda":       "1,00",
    "ncm":               "8708.99.90",
    "cest":              "01.075.00",
    "origem_tributaria": "0",
    "condicao_produto":  "NOVO",
    "tipo_producao":     "Própria",
    "tipo_item":         "Mercadoria para Revenda",
    "frete_gratis":      "NÃO",
    "produto_variacao":  "Produto",
    "unidade_medida":    "Centímetro",
}

# ----------------------------------------------------------
# Valores fixos dos Campos Customizados
# ----------------------------------------------------------
CUSTOM_DEFAULTS: dict = {
    "tipo_veiculo":  "Carro/Caminhonete",
    "condicao_item": "Novo",
    "origem":        "NACIONAL",
    "fonte_produto": "BRASIL",
}

# ----------------------------------------------------------
# Configuração de Tags
# ↑ Atualizar "valor" em tag_mensal todo mês
# ----------------------------------------------------------
TAG_CONFIG: dict = {
    "tags_fixas": [
        {"grupo": "CADASTRO", "tag": "1 - CONFERÊNCIA"},
    ],
    "tag_mensal": {
        "habilitada": True,
        "grupo": "ROGER",
        "valor": "AGOSTO 2026",   # ← atualizar manualmente todo mês
    },
}

# ----------------------------------------------------------
# Template da Descrição Curta
# Único campo dinâmico: {TITULO}
# Não altere o restante sem revisão comercial.
# ----------------------------------------------------------
DESCRICAO_CURTA_TEMPLATE: str = (
    "<p><strong>ATENÇÃO</strong></p>"
    "<p>&nbsp;</p>"
    "<p>Utilize o campo de perguntas para esclarecer suas dúvidas.</p>"
    "<p>&nbsp;</p>"
    "<p>{TITULO}</p>"
    "<p>&nbsp;</p>"
    "<p>Verifique se o código do produto é igual ao da peça que está em seu veículo. "
    "Não compre somente pela compatibilidade de ano.</p>"
    "<p>&nbsp;</p>"
    "<p>A Alpha Brasil Multimarcas oferece uma ampla variedade de peças para pick-ups.</p>"
)

# ----------------------------------------------------------
# 59 Colunas oficiais do modelo base Bling (ordem obrigatória)
# ----------------------------------------------------------
COLUNAS_BLING: list = [
    "ID", "Código", "Descrição", "Unidade", "NCM", "Origem", "Preço",
    "Valor IPI fixo", "Observações", "Situação", "Estoque", "Preço de custo",
    "Cód. no fornecedor", "Fornecedor", "Localização", "Estoque máximo",
    "Estoque mínimo", "Peso líquido (Kg)", "Peso bruto (Kg)", "GTIN/EAN",
    "GTIN/EAN da Embalagem", "Largura do produto", "Altura do Produto",
    "Profundidade do produto", "Data Validade",
    "Descrição do Produto no Fornecedor", "Descrição Complementar",
    "Itens p/ caixa", "Produto Variação", "Tipo Produção",
    "Classe de enquadramento do IPI", "Código na Lista de Serviços",
    "Tipo do item", "Grupo de Tags/Tags", "Tributos", "Código Pai",
    "Código Integração", "Grupo de produtos", "Marca", "CEST", "Volumes",
    "Descrição Curta", "Cross-Docking", "URL Imagens Externas",
    "Link Externo", "Meses Garantia no Fornecedor", "Clonar dados do pai",
    "Condição do Produto", "Frete Grátis", "Número FCI", "Vídeo",
    "Departamento", "Unidade de Medida", "Preço de Compra",
    "Valor base ICMS ST para retenção", "Valor ICMS ST para retenção",
    "Valor ICMS próprio do substituto", "Categoria do produto",
    "Informações Adicionais",
]

# ----------------------------------------------------------
# 8 Campos Customizados do Bling
# ----------------------------------------------------------
COLUNAS_CUSTOMIZADAS: list = [
    "marca", "numeroDePeca", "tipoDeVeiculo", "condicaoDoItem",
    "sku", "modelo", "origem", "fonteDoProduto",
]
