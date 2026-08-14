# ============================================================
# app.py — Streamlit UI: Gerador Bling ERP (pipeline deterministico)
# ============================================================
import io
import sys
import os
import pandas as pd
import streamlit as st

# Garante que src/ seja encontrado
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import (
    BLING_DEFAULTS, CUSTOM_DEFAULTS, TAG_CONFIG,
    COLUNAS_BLING, COLUNAS_CUSTOMIZADAS,
)
from src.adapters.trello_adapter import TrelloAdapter
from src.pipeline.validator import validate_batch, Severity
from src.pipeline.bling_exporter import BlingExporter

# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gerador Bling ERP — Pipeline Determinístico",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Automação de Cadastro — Bling ERP")
st.caption(
    "Pipeline determinístico: **O Trello diz. O programa copia. O Bling recebe.** "
    "Nenhuma inferência é feita. Campos ausentes ficam vazios."
)

# ──────────────────────────────────────────────────────────────
# UPLOAD
# ──────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Carregue o CSV exportado do Trello",
    type=["csv"],
    help="Exportar do Trello: Compartilhar → Imprimir → CSV",
)

if uploaded_file is None:
    st.info("⬆️ Faça upload do CSV do Trello para começar.")
    st.stop()

# Lê com dtype=str para preservar zeros à esquerda e pontos em códigos
df_trello = pd.read_csv(uploaded_file, dtype=str).fillna("")
total_cards = len(df_trello)
st.success(f"✅ CSV carregado — **{total_cards} cards** identificados.")

# ──────────────────────────────────────────────────────────────
# SELEÇÃO DE LISTA
# ──────────────────────────────────────────────────────────────
listas_disponiveis = (
    df_trello["List Name"].unique().tolist()
    if "List Name" in df_trello.columns else []
)
opcoes = ["Todas as Listas"] + listas_disponiveis
lista_selecionada = st.selectbox("Filtrar por Lista:", opcoes)

if lista_selecionada and lista_selecionada != "Todas as Listas":
    df_filtrado = df_trello[df_trello["List Name"] == lista_selecionada].copy()
else:
    df_filtrado = df_trello.copy()

st.info(f"**{len(df_filtrado)} cards** selecionados para exportação.")

# ──────────────────────────────────────────────────────────────
# PROCESSAMENTO
# ──────────────────────────────────────────────────────────────
if not st.button("🚀 Processar e Gerar Planilhas", type="primary"):
    st.stop()

with st.spinner("Processando..."):
    adapter  = TrelloAdapter(df_filtrado)
    produtos = adapter.parse_dataframe(df_filtrado)
    exporter = BlingExporter(BLING_DEFAULTS, CUSTOM_DEFAULTS, TAG_CONFIG)
    df_base, df_custom = exporter.export_dataframes(produtos)
    alerts   = validate_batch(produtos)

# ──────────────────────────────────────────────────────────────
# PAINEL DE VALIDAÇÃO
# ──────────────────────────────────────────────────────────────
erros    = [a for a in alerts if a.severity == Severity.ERROR]
warnings = [a for a in alerts if a.severity == Severity.WARNING]

st.divider()
st.subheader("🔍 Relatório de Validação")

col_e, col_w = st.columns(2)
col_e.metric("❌ Erros (bloqueantes)", len(erros))
col_w.metric("⚠️ Avisos", len(warnings))

if erros:
    with st.expander(f"❌ {len(erros)} Erros — produtos SEM código (não serão importados)", expanded=True):
        df_erros = pd.DataFrame([
            {
                "Card":     a.source_name or a.source_id,
                "Campo":    a.campo,
                "Problema": a.problema,
                "Ação":     a.acao,
            }
            for a in erros
        ])
        st.dataframe(df_erros, use_container_width=True, hide_index=True)

if warnings:
    with st.expander(f"⚠️ {len(warnings)} Avisos — campos ausentes ou duplicatas"):
        df_warns = pd.DataFrame([
            {
                "Card":     a.source_name or a.source_id,
                "Campo":    a.campo,
                "Problema": a.problema,
                "Ação":     a.acao,
            }
            for a in warnings
        ])
        st.dataframe(df_warns, use_container_width=True, hide_index=True)

if not alerts:
    st.success("✅ Todos os produtos passaram na validação sem alertas!")

# ──────────────────────────────────────────────────────────────
# TABELA DE DE-PARA (resumo do mapeamento aplicado)
# ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("🗺️ De-Para Aplicado")
with st.expander("Ver mapeamento campo-a-campo (leitura)"):
    depara_table = [
        {"Origem (Trello)",  "Campo Interno",  "Bling",                     "Tipo"},
    ]
    depara_rows = [
        ("Código(OEM):",      "numero_peca",   "numeroDePeca (custom)",     "Campo"),
        ("Título:",           "titulo",        "Descrição",                 "Campo"),
        ("Categoria:",        "categoria",     "Categoria do produto",      "Campo"),
        ("Peso:",             "peso",          "Peso bruto (Kg)",           "Número 3 dec"),
        ("Largura:",          "largura",       "Largura do produto",        "Número 2 dec"),
        ("Altura:",           "altura",        "Altura do Produto",         "Número 2 dec"),
        ("Profundidade:",     "profundidade",  "Profundidade do produto",   "Número 2 dec"),
        ("Quantidade:",       "quantidade",    "Estoque",                   "Número 2 dec"),
        ("Marca:",            "marca",         "Marca + marca (custom)",    "Campo"),
        ("Modelo:",           "modelo",        "modelo (custom)",           "Campo"),
        ("Observações:",      "observacoes",   "Observações",               "Campo"),
        ("CUSTOM SKU:XXX",    "codigo",        "Código + sku (custom)",     "Padrão Card Name"),
        ("—",                 "—",             "Unidade",                   "Fixo: UN"),
        ("—",                 "—",             "NCM",                       "Fixo: 8708.99.90"),
        ("—",                 "—",             "CEST",                      "Fixo: 01.075.00"),
        ("—",                 "—",             "Condição do Produto",       "Fixo: NOVO"),
        ("—",                 "—",             "Tipo Produção",             "Fixo: Própria"),
        ("—",                 "—",             "Grupo de Tags/Tags",        "Gerado: config.py"),
        ("—",                 "—",             "Descrição Curta",           "Gerado: template"),
        ("—",                 "—",             "tipoDeVeiculo (custom)",    "Fixo: Carro/Caminhonete"),
        ("—",                 "—",             "condicaoDoItem (custom)",   "Fixo: Novo"),
        ("—",                 "—",             "origem (custom)",           "Fixo: NACIONAL"),
        ("—",                 "—",             "fonteDoProduto (custom)",   "Fixo: BRASIL"),
    ]
    df_depara = pd.DataFrame(depara_rows, columns=["Origem (Trello)", "Campo Interno", "Bling", "Tipo"])
    st.dataframe(df_depara, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────
# PRÉVIA DOS DADOS
# ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Prévia — produtos_bling.csv")

# Colunas-chave para visualização rápida
colunas_preview = [
    "Código", "Descrição", "Marca", "Estoque",
    "Peso bruto (Kg)", "Largura do produto", "Altura do Produto",
    "Profundidade do produto", "Categoria do produto", "Grupo de Tags/Tags",
]
colunas_existentes = [c for c in colunas_preview if c in df_base.columns]
st.dataframe(
    df_base[colunas_existentes].head(20),
    use_container_width=True,
    hide_index=True,
)
st.caption(f"Mostrando até 20 de {len(df_base)} produtos. "
           "O arquivo completo está disponível para download abaixo.")

st.subheader("🔧 Prévia — campos_customizados_bling.csv")
st.dataframe(df_custom.head(20), use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────
# ESTATÍSTICAS
# ──────────────────────────────────────────────────────────────
st.divider()
total         = len(produtos)
com_codigo    = sum(1 for p in produtos if p.codigo)
com_titulo    = sum(1 for p in produtos if p.titulo)
com_categoria = sum(1 for p in produtos if p.categoria)
com_marca     = sum(1 for p in produtos if p.marca)
com_peso      = sum(1 for p in produtos if p.peso)

st.subheader("📊 Estatísticas do Lote")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total",     total)
c2.metric("Com Código",    com_codigo,    delta=f"{com_codigo/total*100:.0f}%")
c3.metric("Com Título",    com_titulo,    delta=f"{com_titulo/total*100:.0f}%")
c4.metric("Com Categoria", com_categoria, delta=f"{com_categoria/total*100:.0f}%")
c5.metric("Com Marca",     com_marca,     delta=f"{com_marca/total*100:.0f}%")
c6.metric("Com Peso",      com_peso,      delta=f"{com_peso/total*100:.0f}%")

# ──────────────────────────────────────────────────────────────
# DOWNLOADS
# ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("📥 Downloads")

# Gera CSVs em memória com sep=';' e UTF-8 BOM (padrão Bling)
buf_base = io.BytesIO()
df_base.to_csv(buf_base, index=False, sep=";", encoding="utf-8-sig")
buf_base.seek(0)

buf_custom = io.BytesIO()
df_custom.to_csv(buf_custom, index=False, sep=";", encoding="utf-8-sig")
buf_custom.seek(0)

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        label    = "📥 Baixar produtos_bling.csv",
        data     = buf_base,
        file_name= "produtos_bling.csv",
        mime     = "text/csv",
        type     = "primary",
        help     = f"{len(df_base)} produtos | separador ; | UTF-8 BOM",
    )
    st.caption(f"{len(df_base)} produtos · 59 colunas · sep=; · UTF-8 BOM")

with col2:
    st.download_button(
        label    = "📥 Baixar campos_customizados_bling.csv",
        data     = buf_custom,
        file_name= "campos_customizados_bling.csv",
        mime     = "text/csv",
        help     = f"{len(df_custom)} produtos | 8 campos customizados",
    )
    st.caption(f"{len(df_custom)} produtos · 8 campos · sep=; · UTF-8 BOM")

if erros:
    st.warning(
        f"⚠️ **{len(erros)} produto(s) sem código** foram incluídos no CSV "
        "com a coluna Código vazia. Revise-os no Trello antes de importar no Bling."
    )
