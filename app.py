from datetime import datetime
import io
import re
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURAÇÃO E TEMPLATES
# ==========================================
st.set_page_config(
    page_title="Gerador de Planilhas Bling", page_icon="📦", layout="wide"
)

# 59 Colunas Oficiais do Modelo Base do Bling
COLUNAS_BLING = [
    "ID",
    "Código",
    "Descrição",
    "Unidade",
    "NCM",
    "Origem",
    "Preço",
    "Valor IPI fixo",
    "Observações",
    "Situação",
    "Estoque",
    "Preço de custo",
    "Cód. no fornecedor",
    "Fornecedor",
    "Localização",
    "Estoque máximo",
    "Estoque mínimo",
    "Peso líquido (Kg)",
    "Peso bruto (Kg)",
    "GTIN/EAN",
    "GTIN/EAN da Embalagem",
    "Largura do produto",
    "Altura do Produto",
    "Profundidade do produto",
    "Data Validade",
    "Descrição do Produto no Fornecedor",
    "Descrição Complementar",
    "Itens p/ caixa",
    "Produto Variação",
    "Tipo Produção",
    "Classe de enquadramento do IPI",
    "Código na Lista de Serviços",
    "Tipo do item",
    "Grupo de Tags/Tags",
    "Tributos",
    "Código Pai",
    "Código Integração",
    "Grupo de produtos",
    "Marca",
    "CEST",
    "Volumes",
    "Descrição Curta",
    "Cross-Docking",
    "URL Imagens Externas",
    "Link Externo",
    "Meses Garantia no Fornecedor",
    "Clonar dados do pai",
    "Condição do Produto",
    "Frete Grátis",
    "Número FCI",
    "Vídeo",
    "Departamento",
    "Unidade de Medida",
    "Preço de Compra",
    "Valor base ICMS ST para retenção",
    "Valor ICMS ST para retenção",
    "Valor ICMS próprio do substituto",
    "Categoria do produto",
    "Informações Adicionais",
]


def gerar_descricao_curta_html(titulo_completo, marca="Chevrolet"):
  """Gera o HTML da Descrição Curta em LINHA ÚNICA sem '\\n' para evitar corromper o CSV."""
  marca_str = f"Original {marca}." if marca else "Original."
  html = (
      "<p><strong>ATENÇÃO</strong></p><p>&nbsp;</p><p><strong>Compre somente se"
      " for o mesmo código da"
      " peça</strong></p><p>&nbsp;</p><p>Utilize o campo de perguntas para"
      f" esclarecer suas dúvidas.</p><p>&nbsp;</p><p>{titulo_completo}</p><p>{marca_str}</p><p>&nbsp;</p><p>Verifique"
      " se o código do produto é igual ao da peça que está em seu veículo. Não"
      " compre somente pela compatibilidade de ano.</p>"
  )
  return html


def parse_trello_card(card_desc, card_name):
  """Extrai chave:valor ou padrões livres de dimensões/pesos do card do Trello."""
  data = {}
  desc_text = str(card_desc) if pd.notna(card_desc) else ""

  # 1. Leitura de chave: valor na descrição
  for line in desc_text.split("\n"):
    if ":" in line:
      parts = line.split(":", 1)
      k = parts[0].strip().lower()
      v = parts[1].strip()
      data[k] = v

  # 2. Resgate de SKU / Código da Peça
  # Prioridade: 'codigo' ou 'sku' na descrição -> senão usa a 1ª palavra do Card Name
  sku = data.get("codigo") or data.get("sku") or ""
  if not sku and card_name:
    words = str(card_name).strip().split()
    if words:
      sku = words[0].strip()
  data["sku_final"] = sku

  # 3. Resgate Regex de Dimensões (ex: 37x12x18)
  if "largura" not in data:
    match_dim = re.search(r"(\d+)\s*[xX]\s*(\d+)\s*[xX]\s*(\d+)", desc_text)
    if match_dim:
      data["largura"] = match_dim.group(1)
      data["altura"] = match_dim.group(2)
      data["profundidade"] = match_dim.group(3)

  # 4. Resgate Regex de Peso (ex: 850g ou 1.5kg)
  if "peso" not in data:
    match_g = re.search(r"(\d+)\s*g\b", desc_text, re.IGNORECASE)
    if match_g:
      data["peso"] = f"{float(match_g.group(1)) / 1000:.3f}"
    else:
      match_kg = re.search(
          r"(\d+(?:[.,]\d+)?)\s*kg\b", desc_text, re.IGNORECASE
      )
      if match_kg:
        data["peso"] = match_kg.group(1).replace(",", ".")

  return data


def processar_produto(item_data, card_name_bruto=""):
  sku = str(item_data.get("sku_final", "")).strip()
  nome_peca = str(
      item_data.get("titulo", "") or item_data.get("peca", "") or card_name_bruto
  ).strip()
  modelo = str(item_data.get("modelo", "")).strip()
  caracteristicas = str(
      item_data.get("caracteristicas", "")
      or item_data.get("compatibilidade", "")
  ).strip()
  marca = str(item_data.get("marca", "")).strip()

  # Sintaxe oficial do Título: NOME PEÇA + MODELO + CARACTERISTICAS + SKU
  partes = [p for p in [nome_peca, modelo, caracteristicas, sku] if p]
  titulo_completo = " ".join(partes) if partes else card_name_bruto

  peso = str(item_data.get("peso", "1.000")).replace(",", ".").strip()
  largura = str(item_data.get("largura", "20")).replace(",", ".").strip()
  altura = str(item_data.get("altura", "20")).replace(",", ".").strip()
  profundidade = (
      str(item_data.get("profundidade", "20")).replace(",", ".").strip()
  )
  quantidade = str(item_data.get("quantidade", "1")).strip()
  categoria = str(item_data.get("categoria", "")).strip()
  observacoes = str(item_data.get("observacoes", "")).strip()

  # Tags mensais
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

  # 1. Montagem do Produto Base Bling (59 colunas)
  p_base = {col: "" for col in COLUNAS_BLING}
  p_base["Código"] = sku  # COLUNA 2 = SKU DO PRODUTO
  p_base["Descrição"] = titulo_completo
  p_base["Unidade"] = "UN"
  p_base["NCM"] = "8708.99.90"
  p_base["Origem"] = "0"
  p_base["Preço"] = "1,00"
  p_base["Valor IPI fixo"] = "0,00"
  p_base["Estoque"] = quantidade
  p_base["Peso bruto (Kg)"] = peso
  p_base["Largura do produto"] = largura
  p_base["Altura do Produto"] = altura
  p_base["Profundidade do produto"] = profundidade
  p_base["Produto Variação"] = "Produto"
  p_base["Tipo Produção"] = "Própria"
  p_base["Tipo do item"] = "Mercadoria para Revenda"
  p_base["Grupo de Tags/Tags"] = tags
  p_base["Marca"] = marca
  p_base["CEST"] = "01.075.00"
  p_base["Descrição Curta"] = gerar_descricao_curta_html(
      titulo_completo, marca
  )
  p_base["Condição do Produto"] = "NOVO"
  p_base["Frete Grátis"] = "NÃO"
  p_base["Categoria do produto"] = categoria
  p_base["Observações"] = observacoes

  # 2. Montagem dos Campos Customizados Bling (8 colunas)
  p_custom = {
      "marca": marca,
      "numeroDePeca": sku,  # Número da Peça / Código Físico
      "tipoDeVeiculo": "Carro/Caminhonete",
      "condicaoDoItem": "Novo",
      "sku": sku,
      "modelo": modelo,
      "origem": "NACIONAL",
      "fonteDoProduto": "BRASIL",
  }

  return p_base, p_custom


# ==========================================
# STREAMLIT UI
# ==========================================
st.title("📦 Automação de Cadastro — Bling ERP")
st.subheader("Transformação e Normalização dos dados do Trello para o Bling")

uploaded_file = st.file_uploader(
    "Carregue o CSV exportado do Trello", type=["csv"]
)

if uploaded_file is not None:
  df_trello = pd.read_csv(uploaded_file)
  st.success(f"CSV do Trello carregado com sucesso! ({len(df_trello)} cards)")

  listas = (
      df_trello["List Name"].unique() if "List Name" in df_trello.columns else []
  )
  lista_sel = (
      st.selectbox("Selecione a Lista para exportar:", listas)
      if len(listas) > 0
      else None
  )

  df_filtrado = (
      df_trello[df_trello["List Name"] == lista_sel]
      if lista_sel
      else df_trello
  )

  if st.button("🚀 Processar e Gerar Planilhas"):
    lista_base, lista_custom = [], []

    for _, row in df_filtrado.iterrows():
      c_name = str(row.get("Card Name", "")).strip()
      c_desc = row.get("Card Description", "")

      parsed = parse_trello_card(c_desc, c_name)
      base, custom = processar_produto(parsed, c_name)

      lista_base.append(base)
      lista_custom.append(custom)

    df_out_base = pd.DataFrame(lista_base)[COLUNAS_BLING]
    df_out_custom = pd.DataFrame(lista_custom)

    st.subheader("Prévia dos Produtos Base (59 colunas)")
    st.dataframe(df_out_base.head())

    # Exportação em memória mantendo separador ';' e UTF-8 com BOM
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
