import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO E TEMPLATES
# ==========================================
st.set_page_config(
    page_title="Gerador de Planilhas Bling",
    page_icon="📦",
    layout="wide"
)

# Colunas oficiais do Bling (59 colunas base)
COLUNAS_BLING = [
    "ID", "Código", "Descrição", "Unidade", "NCM", "Origem", "Preço", "Valor IPI fixo", 
    "Observações", "Situação", "Estoque", "Preço de custo", "Cód. no fornecedor", "Fornecedor", 
    "Localização", "Estoque máximo", "Estoque mínimo", "Peso líquido (Kg)", "Peso bruto (Kg)", 
    "GTIN/EAN", "GTIN/EAN da Embalagem", "Largura do produto", "Altura do Produto", 
    "Profundidade do produto", "Data Validade", "Descrição do Produto no Fornecedor", 
    "Descrição Complementar", "Itens p/ caixa", "Produto Variação", "Tipo Produção", 
    "Classe de enquadramento do IPI", "Código na Lista de Serviços", "Tipo do item", 
    "Grupo de Tags/Tags", "Tributos", "Código Pai", "Código Integração", "Grupo de produtos", 
    "Marca", "CEST", "Volumes", "Descrição Curta", "Cross-Docking", "URL Imagens Externas", 
    "Link Externo", "Meses Garantia no Fornecedor", "Clonar dados do pai", "Condição do Produto", 
    "Frete Grátis", "Número FCI", "Vídeo", "Departamento", "Unidade de Medida", "Preço de Compra", 
    "Valor base ICMS ST para retenção", "Valor ICMS ST para retenção", 
    "Valor ICMS próprio do substituto", "Categoria do produto", "Informações Adicionais"
]

def gerar_descricao_curta(titulo_completo, marca="Chevrolet"):
    """Gera a Descrição Curta exatamente no padrão oficial do Bling/Mercado Livre."""
    # Garante que marca tenha um fallback coerente
    marca_formatada = f"Original {marca}." if marca else "Original."

    return f"""<p><strong>ATENÇÃO</strong></p>
        <p>&nbsp;</p>
        <p><strong>Compre somente se for o mesmo código da peça</strong></p>
        <p>&nbsp;</p>
        <p>Utilize o campo de perguntas para esclarecer suas dúvidas.</p>
        <p>&nbsp;</p>
        <p>{titulo_completo}</p>
        <p>{marca_formatada}</p>
        <p>&nbsp;</p>
        <p>Verifique se o código do produto é igual ao da peça que está em seu veículo. Não compre somente pela compatibilidade de ano.</p>"""

def parse_description_text(text):
    """Extrai chave: valor caso seja usado texto estruturado na descrição."""
    data = {}
    if not isinstance(text, str):
        return data
    lines = text.split('\n')
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            data[key] = val
    return data

def processar_dados_item(item):
    """Normaliza e mapeia os dados do Trello/Bancada garantindo a sintaxe do Título."""
    codigo = str(item.get("codigo", "") or item.get("sku", "")).strip()
    nome_peca = str(item.get("titulo", "") or item.get("card_name", "")).strip()
    modelo = str(item.get("modelo", "")).strip()
    caracteristicas_ano = str(
        item.get("caracteristicas", "") or item.get("compatibilidade", "")
    ).strip()
    marca = str(item.get("marca", "")).strip()

    # Monta o título na sintaxe exata: TITULO PEÇA + MODELO CARRO + CARACTERISTICAS/COMPATIBILIDADE + CODIGO PEÇA
    partes_titulo = [
        p for p in [nome_peca, modelo, caracteristicas_ano, codigo] if p
    ]
    titulo_completo = " ".join(partes_titulo)

    peso = str(item.get("peso", "1.00")).replace(",", ".").strip()
    largura = str(item.get("largura", "20")).replace(",", ".").strip()
    altura = str(item.get("altura", "20")).replace(",", ".").strip()
    profundidade = str(item.get("profundidade", "20")).replace(",", ".").strip()
    quantidade = str(item.get("quantidade", "1")).strip()
    categoria = str(item.get("categoria", "")).strip()
    observacoes = str(item.get("observacoes", "")).strip()

    # Tag mensal automática (Ex: ROGER:AGOSTO 2026)
    meses = [
        "JANEIRO",
        "FEVEREIRO",
        "MARÇO",
        "ABRIL",
        "MAIO",
        "JUNHO",
        "JULHO",
        "AGOSTO",
        "SETEMBRO",
        "OUTUBRO",
        "NOVEMBRO",
        "DEZEMBRO",
    ]
    now = datetime.now()
    tag_mes = f"ROGER:{meses[now.month - 1]} {now.year}"
    tags = f"CADASTRO:1 - CONFERÊNCIA|{tag_mes}"

    # Dicionário do Produto Base Bling (59 colunas)
    prod_base = {col: "" for col in COLUNAS_BLING}
    prod_base["Código"] = codigo
    prod_base["Descrição"] = titulo_completo
    prod_base["Unidade"] = "UN"
    prod_base["NCM"] = "8708.99.90"
    prod_base["Origem"] = "0"
    prod_base["Preço"] = "1,00"
    prod_base["Valor IPI fixo"] = "0,00"
    prod_base["Estoque"] = quantidade
    prod_base["Peso bruto (Kg)"] = peso
    prod_base["Largura do produto"] = largura
    prod_base["Altura do Produto"] = altura
    prod_base["Profundidade do produto"] = profundidade
    prod_base["Produto Variação"] = "Produto"
    prod_base["Tipo Produção"] = "Própria"
    prod_base["Tipo do item"] = "Mercadoria para Revenda"
    prod_base["Grupo de Tags/Tags"] = tags
    prod_base["Marca"] = marca
    prod_base["CEST"] = "01.075.00"
    prod_base["Descrição Curta"] = gerar_descricao_curta(
        titulo_completo, marca
    )
    prod_base["Condição do Produto"] = "NOVO"
    prod_base["Frete Grátis"] = "NÃO"
    prod_base["Categoria do produto"] = categoria
    prod_base["Observações"] = observacoes

    # Dicionário dos Campos Customizados Bling (8 colunas)
    custom_fields = {
        "marca": marca,
        "numeroDePeca": codigo,
        "tipoDeVeiculo": "Carro/Caminhonete",
        "condicaoDoItem": "Novo",
        "sku": codigo,
        "modelo": modelo,
        "origem": "NACIONAL",
        "fonteDoProduto": "BRASIL",
    }

    return prod_base, custom_fields

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.title("📦 Automação de Cadastro — Bling ERP")
st.subheader("Transforme os dados do Trello em planilhas prontas para importação")

st.sidebar.header("⚙️ Configurações de Origem")
opcao_origem = st.sidebar.radio("Selecione a fonte dos dados:", ["Upload CSV do Trello", "Simulação / Teste Rápido"])

itens_para_processar = []

if opcao_origem == "Upload CSV do Trello":
    uploaded_file = st.file_uploader("Arraste ou selecione o arquivo CSV exportado do Trello", type=["csv"])
    if uploaded_file is not None:
        df_trello = pd.read_csv(uploaded_file)
        st.success(f"Arquivo carregado com sucesso! Encontrados {len(df_trello)} cards.")
        
        # Filtrar apenas a lista desejada (opcional)
        listas = df_trello['List Name'].unique() if 'List Name' in df_trello.columns else []
        lista_sel = st.selectbox("Selecione a Lista/Coluna a exportar:", listas) if len(listas) > 0 else None
        
        df_filtrado = df_trello[df_trello['List Name'] == lista_sel] if lista_sel else df_trello
        
        for idx, row in df_filtrado.iterrows():
            desc_parsed = parse_description_text(row.get('Card Description', ''))
            desc_parsed['card_name'] = row.get('Card Name', '')
            itens_para_processar.append(desc_parsed)

elif opcao_origem == "Simulação / Teste Rápido":
    st.info("Modo de Teste: Processando 1 item de demonstração com os dados do template.")
    item_teste = {
        "codigo": "S01664",
        "titulo": "Painel Instrumentos S10 LTZ Automática 2021 2023",
        "categoria": "Acessórios para Veículos>>Aces. de Carros e Caminhonetes>>Interior>>Instrumental>>Relógios>>Velocímetros e Conta-giros",
        "peso": "0.95",
        "largura": "36",
        "altura": "18",
        "profundidade": "22",
        "quantidade": "1",
        "marca": "CHEVROLET",
        "modelo": "S10",
        "observacoes": "Peça testada e higienizada"
    }
    itens_para_processar.append(item_teste)

# ==========================================
# PROCESSAMENTO E GERAÇÃO DOS ARQUIVOS
# ==========================================
if itens_para_processar and st.button("🚀 Gerar Planilhas para o Bling"):
    lista_prod_base = []
    lista_custom = []

    for item in itens_para_processar:
        p_base, p_custom = processar_dados_item(item)
        lista_prod_base.append(p_base)
        lista_custom.append(p_custom)

    df_bling_base = pd.DataFrame(lista_prod_base)[COLUNAS_BLING]
    df_bling_custom = pd.DataFrame(lista_custom)

    st.success("✨ Processamento concluído com sucesso!")

    # Exibição de Prévia
    st.subheader("👀 Prévia — Planilha Base de Produtos (59 colunas)")
    st.dataframe(df_bling_base.head())

    st.subheader("👀 Prévia — Campos Customizados (8 colunas)")
    st.dataframe(df_bling_custom.head())

    # Conversão para CSV para download
    buffer_base = io.BytesIO()
    df_bling_base.to_csv(buffer_base, index=False, sep=";", encoding="utf-8-sig")
    buffer_base.seek(0)

    buffer_custom = io.BytesIO()
    df_bling_custom.to_csv(buffer_custom, index=False, sep=";", encoding="utf-8-sig")
    buffer_custom.seek(0)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Baixar produtos_bling.csv",
            data=buffer_base,
            file_name="produtos_bling.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="📥 Baixar campos_customizados_bling.csv",
            data=buffer_custom,
            file_name="campos_customizados_bling.csv",
            mime="text/csv"
        )
