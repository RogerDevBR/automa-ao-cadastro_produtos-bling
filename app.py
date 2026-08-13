from datetime import datetime
import io
import re
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E TEMPLATES
# ==========================================
st.set_page_config(
    page_title="Gerador de Planilhas Bling ERP",
    page_icon="📦",
    layout="wide"
)

# 59 Colunas Oficiais do Modelo Base do Bling
COLUNAS_BLING = [
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
    "Informações Adicionais"
]

# 8 Colunas Oficiais dos Campos Customizados do Bling
COLUNAS_CUSTOMIZADAS = [
    "marca", "numeroDePeca", "tipoDeVeiculo", "condicaoDoItem",
    "sku", "modelo", "origem", "fonteDoProduto"
]


def clean_str(val):
    """Limpa e normaliza strings, removendo nulos, aspas e sufixos numéricos indesejados."""
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", "null"]:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1].strip()
    return s


def gerar_descricao_curta_html(titulo_completo, marca=""):
    """
    Gera o HTML da Descrição Curta estritamente em LINHA ÚNICA sem \\n ou \\r.
    Se marca não foi informada no Trello, omite a marca.
    """
    marca_str = f"<p>Original {marca}.</p>" if marca else "<p>Original.</p>"
    html = (
        f"<p><strong>ATENÇÃO</strong></p>"
        f"<p>&nbsp;</p>"
        f"<p><strong>Compre somente se for o mesmo código da peça</strong></p>"
        f"<p>&nbsp;</p>"
        f"<p>Utilize o campo de perguntas para esclarecer suas dúvidas.</p>"
        f"<p>&nbsp;</p>"
        f"<p>{titulo_completo}</p>"
        f"{marca_str}"
        f"<p>&nbsp;</p>"
        f"<p>Verifique se o código do produto é igual ao da peça que está em seu veículo. Não compre somente pela compatibilidade de ano.</p>"
    )
    return html.replace("\n", "").replace("\r", "").strip()


def extract_brand_model_from_text(text):
    """Infere Marca e Modelo a partir do texto caso estejam citados explicitamente no título/descrição."""
    brands = [
        "CHEVROLET", "VOLKSWAGEN", "VW", "MITSUBISHI", "TOYOTA", "FORD", "FIAT",
        "RENAULT", "NISSAN", "HYUNDAI", "HONDA", "JEEP", "RAM", "AUDI", "BMW", "MERCEDES"
    ]
    models = [
        "AMAROK", "S10", "TRAILBLAZER", "TRITON", "L200 TRITON", "L200", "SW4", "HILUX",
        "RANGER", "COROLLA", "TORO", "COMPASS", "RENEGADE", "DUSTER", "SAVEIRO", "MONTANA"
    ]
    
    text_upper = text.upper()
    found_brand = ""
    found_model = ""
    
    for b in brands:
        if re.search(r'\b' + re.escape(b) + r'\b', text_upper):
            found_brand = "VOLKSWAGEN" if b == "VW" else b
            break
            
    for m in models:
        if re.search(r'\b' + re.escape(m) + r'\b', text_upper):
            found_model = m
            break
            
    return found_brand, found_model


def parse_trello_row(row):
    """
    Extrai EXATAMENTE o que existe no Trello sem inventar fallbacks.
    Se um dado não foi fornecido, permanece vazio ("").
    """
    data = {}
    c_name = clean_str(row.get("Card Name", ""))
    c_desc = clean_str(row.get("Card Description", ""))
    
    # 1. Colunas explícitas no CSV exportado do Trello
    col_mapping = {
        'codigo_oem': ['código(oem):', 'codigo(oem):', 'código oem:', 'codigo oem:'],
        'codigo': ['código:', 'codigo:', 'sku:'],
        'titulo': ['título:', 'titulo:'],
        'categoria': ['categoria:'],
        'peso': ['peso:', 'peso(kg):'],
        'largura': ['largura:', 'largura(cm):'],
        'altura': ['altura:', 'altura(cm):'],
        'profundidade': ['profundidade:', 'profundidade(cm):'],
        'quantidade': ['quantidade:', 'quantidade(un):'],
        'marca': ['marca:'],
        'modelo': ['modelo:'],
        'observacoes': ['observações:', 'observacoes:']
    }
    
    for key, aliases in col_mapping.items():
        for col_name in row.index:
            col_clean = str(col_name).strip().lower()
            if any(col_clean == alias for alias in aliases):
                val = clean_str(row[col_name])
                if val:
                    data[key] = val
                    break

    # 2. Parse da Card Description (linhas chave: valor)
    if c_desc:
        for line in c_desc.split("\n"):
            line_clean = line.replace("`", "").strip()
            if ":" in line_clean:
                parts = line_clean.split(":", 1)
                k = parts[0].strip().lower()
                v = clean_str(parts[1])
                if v:
                    if any(x in k for x in ["código(oem)", "codigo(oem)", "código oem"]) and "codigo_oem" not in data:
                        data["codigo_oem"] = v
                    elif any(x in k for x in ["código", "codigo"]) and "codigo" not in data:
                        data["codigo"] = v
                    elif "sku" in k and "sku" not in data:
                        data["sku"] = v
                    elif ("título" in k or "titulo" in k) and "titulo" not in data:
                        data["titulo"] = v
                    elif "marca" in k and "marca" not in data:
                        data["marca"] = v
                    elif "modelo" in k and "modelo" not in data:
                        data["modelo"] = v
                    elif "categoria" in k and "categoria" not in data:
                        data["categoria"] = v
                    elif "peso" in k and "peso" not in data:
                        data["peso"] = v
                    elif "largura" in k and "largura" not in data:
                        data["largura"] = v
                    elif "altura" in k and "altura" not in data:
                        data["altura"] = v
                    elif "profundidade" in k and "profundidade" not in data:
                        data["profundidade"] = v
                    elif "quantidade" in k and "quantidade" not in data:
                        data["quantidade"] = v
                    elif ("observações" in k or "observacoes" in k) and "observacoes" not in data:
                        data["observacoes"] = v

    # 3. Resgate de SKU e Código OEM
    sku = data.get("sku") or data.get("codigo") or ""
    oem = data.get("codigo_oem") or ""

    match_custom_sku = re.search(r'(?:CUSTOM\s*)?SKU\s*:\s*([A-Za-z0-9_-]+)', c_name, re.IGNORECASE)
    if match_custom_sku:
        sku = match_custom_sku.group(1).strip()

    if not sku:
        match_s_code = re.search(r'\b(S\d{4,6})\b', c_name, re.IGNORECASE)
        if match_s_code:
            sku = match_s_code.group(1).upper()

    if not oem and c_name:
        words = c_name.split()
        if words:
            first_word = words[0].strip()
            if re.match(r'^[A-Za-z0-9]{6,}$', first_word) and not first_word.upper().startswith("S016"):
                oem = first_word

    if not sku:
        sku = oem if oem else (c_name.split()[0] if c_name.split() else "")

    if not oem:
        oem = sku

    data["sku_final"] = sku
    data["oem_final"] = oem

    # 4. Extração Regex de Dimensões SOMENTE se constar na descrição (ex: 37x12x18)
    if not data.get("largura"):
        match_dim = re.search(r'(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)', c_desc)
        if match_dim:
            data["largura"] = match_dim.group(1).replace(",", ".")
            data["altura"] = match_dim.group(2).replace(",", ".")
            data["profundidade"] = match_dim.group(3).replace(",", ".")
        else:
            data["largura"] = ""
            data["altura"] = ""
            data["profundidade"] = ""

    # 5. Extração Regex de Peso SOMENTE se constar na descrição (ex: 850g ou 1kg)
    if not data.get("peso"):
        match_g = re.search(r'(\d+(?:[.,]\d+)?)\s*g\b', c_desc, re.IGNORECASE)
        if match_g:
            val_g = float(match_g.group(1).replace(",", "."))
            data["peso"] = f"{val_g / 1000:.3f}"
        else:
            match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*kg\b', c_desc, re.IGNORECASE)
            if match_kg:
                data["peso"] = match_kg.group(1).replace(",", ".")
            else:
                data["peso"] = ""

    # 6. Extração Regex de Quantidade SOMENTE se constar na descrição (ex: 1 un)
    if not data.get("quantidade"):
        match_q = re.search(r'(\d+)\s*(?:un|u|unid|unidade|peças|pecas)\b', c_desc, re.IGNORECASE)
        if match_q:
            data["quantidade"] = match_q.group(1)
        else:
            data["quantidade"] = ""

    # 7. Inferência de Marca e Modelo se citado no texto
    inf_brand, inf_model = extract_brand_model_from_text(c_name + " " + c_desc)
    if not data.get("marca"):
        data["marca"] = inf_brand
    if not data.get("modelo"):
        data["modelo"] = inf_model

    return data, c_name


def processar_produto(item_data, card_name_bruto=""):
    sku = str(item_data.get("sku_final", "")).strip()
    numero_peca = str(item_data.get("oem_final", sku)).strip()
    nome_peca = str(item_data.get("titulo", "")).strip()
    
    if not nome_peca:
        clean_name = re.sub(r'^(?:CUSTOM\s*)?SKU\s*:\s*[A-Za-z0-9_-]*', '', card_name_bruto, flags=re.IGNORECASE).strip()
        nome_peca = clean_name if clean_name else card_name_bruto

    modelo = str(item_data.get("modelo", "")).strip()
    caracteristicas = str(item_data.get("caracteristicas", "") or item_data.get("compatibilidade", "")).strip()
    marca = str(item_data.get("marca", "")).strip()

    # Regra oficial de Título: TITULO PEÇA + MODELO CARRO + CARACTERÍSTICAS/COMPATIBILIDADE + SKU/CÓDIGO
    partes = []
    if nome_peca:
        partes.append(nome_peca)
    if modelo and modelo.lower() not in nome_peca.lower():
        partes.append(modelo)
    if caracteristicas:
        partes.append(caracteristicas)
    if sku and sku.lower() not in nome_peca.lower():
        partes.append(sku)
    
    titulo_completo = " ".join(partes) if partes else card_name_bruto

    peso = str(item_data.get("peso", "")).replace(",", ".").strip()
    largura = str(item_data.get("largura", "")).replace(",", ".").strip()
    altura = str(item_data.get("altura", "")).replace(",", ".").strip()
    profundidade = str(item_data.get("profundidade", "")).replace(",", ".").strip()
    quantidade = str(item_data.get("quantidade", "")).strip()
    categoria = str(item_data.get("categoria", "")).strip()
    observacoes = str(item_data.get("observacoes", "")).strip()

    # Tag mensal dinâmica
    meses = [
        "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
        "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
    ]
    now = datetime.now()
    tag_mes = f"ROGER:{meses[now.month - 1]} {now.year}"
    tags = f"CADASTRO:1 - CONFERÊNCIA|{tag_mes}"

    def fmt_num(v, decimals=2):
        if not v or pd.isna(v) or str(v).strip() == "":
            return ""
        try:
            val = float(str(v).replace(",", "."))
            return f"{val:.{decimals}f}".replace(".", ",")
        except:
            return ""

    # 1. Montagem do Produto Base Bling (59 colunas)
    p_base = {col: "" for col in COLUNAS_BLING}
    p_base["Código"] = sku
    p_base["Descrição"] = titulo_completo
    p_base["Unidade"] = "UN"
    p_base["NCM"] = "8708.99.90"
    p_base["Origem"] = "0"
    p_base["Preço"] = "1,00"
    p_base["Valor IPI fixo"] = "0,00"
    p_base["Estoque"] = fmt_num(quantidade, 2)
    p_base["Peso bruto (Kg)"] = fmt_num(peso, 3)
    p_base["Largura do produto"] = fmt_num(largura, 2)
    p_base["Altura do Produto"] = fmt_num(altura, 2)
    p_base["Profundidade do produto"] = fmt_num(profundidade, 2)
    p_base["Produto Variação"] = "Produto"
    p_base["Tipo Produção"] = "Própria"
    p_base["Tipo do item"] = "Mercadoria para Revenda"
    p_base["Grupo de Tags/Tags"] = tags
    p_base["Marca"] = marca
    p_base["CEST"] = "01.075.00"
    p_base["Descrição Curta"] = gerar_descricao_curta_html(titulo_completo, marca)
    p_base["Condição do Produto"] = "NOVO"
    p_base["Frete Grátis"] = "NÃO"
    p_base["Unidade de Medida"] = "Centímetro"
    p_base["Categoria do produto"] = categoria
    p_base["Observações"] = observacoes

    # 2. Montagem dos Campos Customizados Bling (8 colunas)
    p_custom = {
        "marca": marca,
        "numeroDePeca": numero_peca,
        "tipoDeVeiculo": "Carro/Caminhonete",
        "condicaoDoItem": "Novo",
        "sku": sku,
        "modelo": modelo,
        "origem": "NACIONAL",
        "fonteDoProduto": "BRASIL"
    }

    return p_base, p_custom


# ==========================================
# INTERFACE STREAMLIT UI
# ==========================================
st.title("📦 Automação de Cadastro — Bling ERP")
st.subheader("Conversão e Normalização dos dados do Trello para o Bling ERP")

uploaded_file = st.file_uploader(
    "Carregue o CSV exportado do Trello", type=["csv"]
)

if uploaded_file is not None:
    df_trello = pd.read_csv(uploaded_file)
    st.success(f"CSV do Trello carregado com sucesso! ({len(df_trello)} cards identificados)")

    listas = df_trello["List Name"].unique().tolist() if "List Name" in df_trello.columns else []
    opcoes_lista = ["Todas as Listas"] + listas
    lista_sel = st.selectbox("Selecione a Lista para exportar:", opcoes_lista)

    if lista_sel and lista_sel != "Todas as Listas":
        df_filtrado = df_trello[df_trello["List Name"] == lista_sel]
    else:
        df_filtrado = df_trello

    if st.button("🚀 Processar e Gerar Planilhas"):
        lista_base, lista_custom = [], []

        for _, row in df_filtrado.iterrows():
            parsed, c_name = parse_trello_row(row)
            base, custom = processar_produto(parsed, c_name)
            lista_base.append(base)
            lista_custom.append(custom)

        df_out_base = pd.DataFrame(lista_base)[COLUNAS_BLING]
        df_out_custom = pd.DataFrame(lista_custom)[COLUNAS_CUSTOMIZADAS]

        st.subheader("Prévia dos Produtos Base (59 colunas)")
        st.dataframe(df_out_base.head())

        st.subheader("Prévia dos Campos Customizados (8 colunas)")
        st.dataframe(df_out_custom.head())

        # Exportação em memória com separador ';' e UTF-8 com BOM (padrão Bling)
        buf_base = io.BytesIO()
        df_out_base.to_csv(buf_base, index=False, sep=";", encoding="utf-8-sig")
        buf_base.seek(0)

        buf_custom = io.BytesIO()
        df_out_custom.to_csv(buf_custom, index=False, sep=";", encoding="utf-8-sig")
        buf_custom.seek(0)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Baixar produtos_bling.csv",
                data=buf_base,
                file_name="produtos_bling.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                "📥 Baixar campos_customizados_bling.csv",
                data=buf_custom,
                file_name="campos_customizados_bling.csv",
                mime="text/csv",
            )
