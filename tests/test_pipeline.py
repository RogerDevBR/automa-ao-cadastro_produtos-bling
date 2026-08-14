# ============================================================
# tests/test_pipeline.py — 20 testes obrigatórios + regressão
# ============================================================
# Execute com: python -m pytest tests/ -v
#           ou: python -m unittest tests/test_pipeline.py -v
#
# Cada teste verifica ORIGEM → CAMPO INTERNO → COLUNA FINAL.
# Não basta verificar que um valor "apareceu em algum lugar".
# A coluna exata é sempre verificada.
# ============================================================

import io
import os
import sys
import unittest
import pandas as pd

# Garante que o pacote src/ seja encontrado independente de onde o teste roda
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.produto import Produto
from src.adapters.trello_adapter import TrelloAdapter
from src.pipeline.validator import validate, validate_batch, Severity
from src.pipeline.bling_exporter import BlingExporter
from src.pipeline.description import build_short_description
from src.pipeline.tags import build_tags
from src.config import (
    BLING_DEFAULTS, CUSTOM_DEFAULTS, TAG_CONFIG,
    COLUNAS_BLING, COLUNAS_CUSTOMIZADAS,
)


# ----------------------------------------------------------
# Utilitários de teste
# ----------------------------------------------------------
def _make_row(**kwargs) -> pd.Series:
    """Cria uma linha simulando o CSV exportado do Trello."""
    defaults = {
        "Card ID":          "TEST_ID",
        "Card Name":        "CARD SEM SKU",
        "Card Description": "",
        "List Name":        "Concluído 🎉",
        "Código(OEM):":     "",
        "Título:":          "",
        "Categoria:":       "",
        "Peso:":            "",
        "Largura:":         "",
        "Altura:":          "",
        "Profundidade:":    "",
        "Quantidade:":      "",
        "Marca:":           "",
        "Modelo:":          "",
        "Observações:":     "",
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def _make_adapter(row: pd.Series) -> TrelloAdapter:
    df = pd.DataFrame([row.to_dict()])
    return TrelloAdapter(df)


def _make_exporter() -> BlingExporter:
    return BlingExporter(BLING_DEFAULTS, CUSTOM_DEFAULTS, TAG_CONFIG)


# ===========================================================
# GRUPO 1 — TrelloAdapter: extração determinística
# ===========================================================

class TestTrelloAdapter(unittest.TestCase):

    # ── Teste 1: Produto completo ────────────────────────────
    def test_01_produto_completo(self):
        """Todos os campos explícitos devem ser mapeados corretamente."""
        row = _make_row(
            **{
                "Card Name":     "CUSTOM SKU:ABC123",
                "Código(OEM):":  "OEM456",
                "Título:":       "Retrovisor Hilux",
                "Categoria:":    "Retrovisores",
                "Peso:":         "2,5",
                "Largura:":      "30",
                "Altura:":       "20",
                "Profundidade:": "15",
                "Quantidade:":   "2",
                "Marca:":        "TOYOTA",
                "Modelo:":       "HILUX",
                "Observações:":  "Original Toyota",
            }
        )
        p = _make_adapter(row).parse_row(row)

        self.assertEqual(p.codigo,       "ABC123",          "codigo")
        self.assertEqual(p.numero_peca,  "OEM456",          "numero_peca")
        self.assertEqual(p.titulo,       "Retrovisor Hilux","titulo")
        self.assertEqual(p.categoria,    "Retrovisores",    "categoria")
        self.assertEqual(p.peso,         "2,5",             "peso")
        self.assertEqual(p.largura,      "30",              "largura")
        self.assertEqual(p.altura,       "20",              "altura")
        self.assertEqual(p.profundidade, "15",              "profundidade")
        self.assertEqual(p.quantidade,   "2",               "quantidade")
        self.assertEqual(p.marca,        "TOYOTA",          "marca")
        self.assertEqual(p.modelo,       "HILUX",           "modelo")
        self.assertEqual(p.observacoes,  "Original Toyota", "observacoes")

    # ── Teste 2: Sem categoria ───────────────────────────────
    def test_02_sem_categoria(self):
        """Categoria vazia → campo categoria = ''."""
        row = _make_row(**{"Card Name": "CUSTOM SKU:X001", "Categoria:": ""})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.categoria, "")

    # ── Teste 3: Sem marca — NÃO inferir do título ──────────
    def test_03_sem_marca_nao_inferir(self):
        """Marca vazia → campo marca = ''. NÃO procurar no título."""
        row = _make_row(
            **{"Card Name": "CUSTOM SKU:X001",
               "Título:":   "Retrovisor Toyota Hilux 2020",
               "Marca:":    ""}
        )
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.marca, "",
            "FALHA: marca não deve ser inferida do título")

    # ── Teste 4: Sem modelo — NÃO inferir do título ─────────
    def test_04_sem_modelo_nao_inferir(self):
        """Modelo vazio → campo modelo = ''. NÃO procurar no título."""
        row = _make_row(
            **{"Card Name": "CUSTOM SKU:X001",
               "Título:":   "Retrovisor Hilux 2022",
               "Modelo:":   ""}
        )
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.modelo, "",
            "FALHA: modelo não deve ser inferido do título")

    # ── Teste 5: Sem número de peça — NÃO usar SKU ──────────
    def test_05_sem_numero_peca_nao_usar_sku(self):
        """numero_peca vazio → ''. NÃO copiar codigo para numero_peca."""
        row = _make_row(
            **{"Card Name":    "CUSTOM SKU:S001",
               "Código(OEM):": ""}
        )
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.numero_peca, "",
            "FALHA: numero_peca não deve receber o valor de codigo")
        self.assertEqual(p.codigo, "S001")

    # ── Teste 6: Sem peso ────────────────────────────────────
    def test_06_sem_peso(self):
        """Peso vazio → campo peso = ''."""
        row = _make_row(**{"Card Name": "CUSTOM SKU:X001", "Peso:": ""})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.peso, "")

    # ── Teste 7: Sem dimensões ───────────────────────────────
    def test_07_sem_dimensoes(self):
        """Dimensões vazias → campos largura/altura/profundidade = ''."""
        row = _make_row(**{"Card Name": "CUSTOM SKU:X001"})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.largura,      "", "largura")
        self.assertEqual(p.altura,       "", "altura")
        self.assertEqual(p.profundidade, "", "profundidade")

    # ── Teste 8: Sem quantidade ──────────────────────────────
    def test_08_sem_quantidade(self):
        """Quantidade vazia → campo quantidade = ''."""
        row = _make_row(**{"Card Name": "CUSTOM SKU:X001", "Quantidade:": ""})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.quantidade, "")

    # ── Teste 9: Código com zeros à esquerda ────────────────
    def test_09_codigo_zeros_esquerda(self):
        """Zeros à esquerda devem ser preservados (código é string)."""
        row = _make_row(**{"Card Name": "CUSTOM SKU:001234"})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.codigo, "001234",
            "FALHA: zeros à esquerda foram removidos")

    # ── Teste 10: Código com ponto ───────────────────────────
    def test_10_codigo_com_ponto(self):
        """Ponto no código deve ser preservado."""
        row = _make_row(**{"Card Name": "CUSTOM SKU:8100.C113"})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.codigo, "8100.C113",
            "FALHA: ponto no código foi alterado")

    # ── Teste 11: Título longo ───────────────────────────────
    def test_11_titulo_longo(self):
        """Título longo deve ser preservado exatamente como informado."""
        titulo = ("Painel de Instrumentos Digitais Completo para Chevrolet S10 "
                  "LTZ Automática 4x4 2021 2022 2023 com Todas as Funcionalidades")
        row = _make_row(**{"Card Name": "CUSTOM SKU:X001", "Título:": titulo})
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.titulo, titulo)

    # ── Teste 12: Observação com números — NÃO extrair medidas
    def test_12_observacao_nao_extrai_medidas(self):
        """Peso e dimensões dentro de observação NÃO devem ser extraídos."""
        row = _make_row(
            **{"Card Name":     "CUSTOM SKU:X001",
               "Observações:":  "Peso aprox 850g. Medidas: 37x12x18cm.",
               "Peso:":         "",
               "Largura:":      ""}
        )
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.peso,    "",
            "FALHA: peso foi extraído de texto livre")
        self.assertEqual(p.largura, "",
            "FALHA: largura foi extraída de texto livre")
        # Observação deve ser preservada como texto
        self.assertIn("850g", p.observacoes)

    # ── Teste 13: Produto com medidas em campos explícitos ───
    def test_13_medidas_em_campos_explicitos(self):
        """Dimensões dos campos explícitos devem ser mapeadas corretamente."""
        row = _make_row(
            **{"Card Name":     "CUSTOM SKU:X001",
               "Peso:":         "4,2",
               "Largura:":      "50",
               "Altura:":       "30",
               "Profundidade:": "20"}
        )
        p = _make_adapter(row).parse_row(row)
        self.assertEqual(p.peso,         "4,2")
        self.assertEqual(p.largura,      "50")
        self.assertEqual(p.altura,       "30")
        self.assertEqual(p.profundidade, "20")

    # ── Teste 20: Múltiplos produtos no mesmo arquivo ────────
    def test_20_multiplos_produtos(self):
        """Lista com múltiplos produtos deve mapear cada um corretamente."""
        rows = [
            _make_row(**{"Card Name": "CUSTOM SKU:P001", "Título:": "Peça Um",   "Quantidade:": "1"}).to_dict(),
            _make_row(**{"Card Name": "CUSTOM SKU:P002", "Título:": "Peça Dois",  "Quantidade:": "2"}).to_dict(),
            _make_row(**{"Card Name": "CUSTOM SKU:P003", "Título:": "Peça Três",  "Quantidade:": "3"}).to_dict(),
        ]
        df = pd.DataFrame(rows)
        adapter = TrelloAdapter(df)
        produtos = adapter.parse_dataframe(df)

        self.assertEqual(len(produtos), 3)
        self.assertEqual(produtos[0].codigo,    "P001")
        self.assertEqual(produtos[1].codigo,    "P002")
        self.assertEqual(produtos[2].codigo,    "P003")
        self.assertEqual(produtos[0].titulo,    "Peça Um")
        self.assertEqual(produtos[1].quantidade, "2")
        self.assertEqual(produtos[2].quantidade, "3")


# ===========================================================
# GRUPO 2 — BlingExporter: colunas corretas
# ===========================================================

class TestBlingExporter(unittest.TestCase):

    def setUp(self):
        self.exp = _make_exporter()

    # ── Teste 16: Todas as colunas nas posições corretas ─────
    def test_16_colunas_corretas(self):
        """Cada campo deve ir para a COLUNA EXATA no Bling."""
        p = Produto(
            codigo       = "ABC123",
            titulo       = "Retrovisor Hilux",
            categoria    = "Retrovisores",
            peso         = "2,5",
            largura      = "30",
            altura       = "20",
            profundidade = "15",
            quantidade   = "2",
            marca        = "TOYOTA",
            observacoes  = "Original",
        )
        row = self.exp.to_row(p)

        # Campos de produto
        self.assertEqual(row["Código"],              "ABC123",            "Código")
        self.assertEqual(row["Descrição"],           "Retrovisor Hilux",  "Descrição")
        self.assertEqual(row["Marca"],               "TOYOTA",            "Marca")
        self.assertEqual(row["Categoria do produto"],"Retrovisores",      "Categoria")
        self.assertEqual(row["Observações"],         "Original",          "Observações")

        # Campos fixos de config
        self.assertEqual(row["Unidade"],             "UN",                     "Unidade")
        self.assertEqual(row["NCM"],                 "8708.99.90",             "NCM")
        self.assertEqual(row["CEST"],                "01.075.00",              "CEST")
        self.assertEqual(row["Condição do Produto"], "NOVO",                   "Condição")
        self.assertEqual(row["Tipo Produção"],       "Própria",                "Tipo Produção")
        self.assertEqual(row["Tipo do item"],        "Mercadoria para Revenda","Tipo item")
        self.assertEqual(row["Frete Grátis"],        "NÃO",                    "Frete")
        self.assertEqual(row["Produto Variação"],    "Produto",                "Variação")
        self.assertEqual(row["Unidade de Medida"],   "Centímetro",             "Unidade Medida")
        self.assertEqual(row["Origem"],              "0",                      "Origem tributária")

        # Campos numéricos formatados
        self.assertEqual(row["Peso bruto (Kg)"],        "2,500", "Peso bruto 3 dec")
        self.assertEqual(row["Largura do produto"],     "30,00", "Largura 2 dec")
        self.assertEqual(row["Altura do Produto"],      "20,00", "Altura 2 dec")
        self.assertEqual(row["Profundidade do produto"],"15,00", "Profundidade 2 dec")
        self.assertEqual(row["Estoque"],                "2,00",  "Estoque 2 dec")

        # Peso LÍQUIDO deve ser VAZIO (IGNORAR)
        self.assertEqual(row["Peso líquido (Kg)"],   "", "Peso líquido deve ser vazio")

        # Campos IGNORAR devem estar vazios
        self.assertEqual(row["ID"],           "", "ID deve ser vazio")
        self.assertEqual(row["Situação"],     "", "Situação deve ser vazio")
        self.assertEqual(row["Preço de custo"],"", "Preço custo deve ser vazio")
        self.assertEqual(row["Volumes"],      "", "Volumes deve ser vazio")
        self.assertEqual(row["Departamento"], "", "Departamento deve ser vazio")
        self.assertEqual(row["Valor IPI fixo"],"","Valor IPI deve ser vazio")

    # ── Teste 3 (exporter): sem marca → Marca = '' ──────────
    def test_16b_sem_marca_coluna_vazia(self):
        """Produto sem marca: coluna Marca no Bling deve ser ''."""
        p = Produto(codigo="X001", titulo="Peça", marca="")
        row = self.exp.to_row(p)
        self.assertEqual(row["Marca"], "",
            "FALHA: Marca foi preenchida mesmo estando vazia na origem")

    # ── Teste: sem título → Descrição = '' ─────────────────
    def test_16c_sem_titulo_descricao_vazia(self):
        """Produto sem título: Descrição no Bling deve ser ''."""
        p = Produto(codigo="X001", titulo="")
        row = self.exp.to_row(p)
        self.assertEqual(row["Descrição"], "")

    # ── Teste: sem quantidade → Estoque = '' ───────────────
    def test_16d_sem_quantidade_estoque_vazio(self):
        """Produto sem quantidade: Estoque deve ser ''."""
        p = Produto(codigo="X001", quantidade="")
        row = self.exp.to_row(p)
        self.assertEqual(row["Estoque"], "")

    # ── Teste: sem peso → Peso bruto = '' ──────────────────
    def test_16e_sem_peso_coluna_vazia(self):
        """Produto sem peso: Peso bruto deve ser ''."""
        p = Produto(codigo="X001", peso="")
        row = self.exp.to_row(p)
        self.assertEqual(row["Peso bruto (Kg)"], "")

    # ── Teste: sem dimensões → colunas vazias ──────────────
    def test_16f_sem_dimensoes_colunas_vazias(self):
        """Produto sem dimensões: Largura/Altura/Profundidade = ''."""
        p = Produto(codigo="X001")
        row = self.exp.to_row(p)
        self.assertEqual(row["Largura do produto"],      "")
        self.assertEqual(row["Altura do Produto"],       "")
        self.assertEqual(row["Profundidade do produto"], "")

    # ── Teste: todas as 59 colunas presentes ───────────────
    def test_16g_todas_59_colunas_presentes(self):
        """O resultado deve ter exatamente as 59 colunas Bling."""
        p = Produto(codigo="X001")
        row = self.exp.to_row(p)
        self.assertEqual(set(row.keys()), set(COLUNAS_BLING))
        self.assertEqual(len(row), 59)

    # ── Teste 17: Campos customizados ───────────────────────
    def test_17_campos_customizados(self):
        """Campos customizados mapeados corretamente."""
        p = Produto(
            codigo      = "S01670",
            numero_peca = "12348765",
            marca       = "CHEVROLET",
            modelo      = "S10",
        )
        custom = self.exp.to_custom_row(p)

        # sku custom = codigo (regra de negócio explícita)
        self.assertEqual(custom["sku"],          "S01670",            "sku custom")
        # numeroDePeca ← numero_peca (NUNCA = codigo)
        self.assertEqual(custom["numeroDePeca"], "12348765",          "numeroDePeca")
        self.assertEqual(custom["marca"],        "CHEVROLET",         "marca custom")
        self.assertEqual(custom["modelo"],       "S10",               "modelo custom")
        # Fixos de CUSTOM_DEFAULTS
        self.assertEqual(custom["tipoDeVeiculo"], "Carro/Caminhonete","tipoDeVeiculo")
        self.assertEqual(custom["condicaoDoItem"],"Novo",             "condicaoDoItem")
        self.assertEqual(custom["origem"],        "NACIONAL",         "origem custom")
        self.assertEqual(custom["fonteDoProduto"],"BRASIL",           "fonteDoProduto")

    # ── Teste 17b: sem numero_peca → numeroDePeca = '' ──────
    def test_17b_sem_numero_peca(self):
        """numeroDePeca deve ser '' quando numero_peca não existe."""
        p = Produto(codigo="S001", numero_peca="")
        custom = self.exp.to_custom_row(p)
        self.assertEqual(custom["numeroDePeca"], "",
            "FALHA: numeroDePeca recebeu o valor de codigo")

    # ── Teste 17c: sem modelo → modelo custom = '' ──────────
    def test_17c_sem_modelo_custom(self):
        """modelo custom deve ser '' quando modelo não existe."""
        p = Produto(codigo="S001", modelo="")
        custom = self.exp.to_custom_row(p)
        self.assertEqual(custom["modelo"], "")

    # ── Teste 17d: todos os 8 campos customizados presentes ─
    def test_17d_todos_8_campos_customizados(self):
        """O resultado deve ter exatamente 8 campos customizados."""
        p = Produto(codigo="X001")
        custom = self.exp.to_custom_row(p)
        self.assertEqual(set(custom.keys()), set(COLUNAS_CUSTOMIZADAS))
        self.assertEqual(len(custom), 8)

    # ── Teste 18: Tags ───────────────────────────────────────
    def test_18_tags_formato_correto(self):
        """Tags devem seguir formato 'GRUPO:TAG|GRUPO:TAG'."""
        p = Produto(codigo="X001")
        row = self.exp.to_row(p)
        tags = row["Grupo de Tags/Tags"]

        self.assertIn("CADASTRO:1 - CONFERÊNCIA", tags, "Tag fixa ausente")
        self.assertIn("ROGER:AGOSTO 2026",         tags, "Tag mensal ausente")
        self.assertIn("|",                          tags, "Separador | ausente")
        # Garante formato exato
        self.assertEqual(tags, "CADASTRO:1 - CONFERÊNCIA|ROGER:AGOSTO 2026")

    # ── Teste 19: Descrição curta ────────────────────────────
    def test_19_descricao_curta(self):
        """Descrição curta usa título, sem marca/modelo/SKU extras."""
        p = Produto(codigo="X001", titulo="Retrovisor Hilux", marca="TOYOTA")
        row = self.exp.to_row(p)
        desc = row["Descrição Curta"]

        self.assertIn("ATENÇÃO",          desc, "ATENÇÃO ausente")
        self.assertIn("Retrovisor Hilux", desc, "Título ausente na descrição curta")
        self.assertNotIn("\n",            desc, "Não pode ter quebra de linha")
        self.assertNotIn("\r",            desc, "Não pode ter \\r")
        # Marca NÃO deve aparecer de forma customizada — só o título
        # (o template pode conter "TOYOTA" na empresa mas não pelo campo marca)

    def test_19b_descricao_curta_titulo_vazio(self):
        """Título vazio → descrição curta = ''."""
        p = Produto(codigo="X001", titulo="")
        row = self.exp.to_row(p)
        self.assertEqual(row["Descrição Curta"], "")


# ===========================================================
# GRUPO 3 — build_short_description e build_tags isolados
# ===========================================================

class TestFuncoesAuxiliares(unittest.TestCase):

    def test_build_tags_padrao(self):
        result = build_tags(TAG_CONFIG)
        self.assertEqual(result, "CADASTRO:1 - CONFERÊNCIA|ROGER:AGOSTO 2026")

    def test_build_tags_sem_mensal(self):
        cfg = {
            "tags_fixas": [{"grupo": "CADASTRO", "tag": "1 - CONFERÊNCIA"}],
            "tag_mensal": {"habilitada": False, "grupo": "X", "valor": "Y"},
        }
        result = build_tags(cfg)
        self.assertEqual(result, "CADASTRO:1 - CONFERÊNCIA")

    def test_build_short_description_titulo_presente(self):
        desc = build_short_description("Painel L200 Triton")
        self.assertIn("Painel L200 Triton", desc)
        self.assertIn("ATENÇÃO", desc)
        self.assertIn("Alpha Brasil", desc)
        self.assertNotIn("\n", desc)

    def test_build_short_description_titulo_vazio(self):
        self.assertEqual(build_short_description(""), "")
        self.assertEqual(build_short_description(None), "")


# ===========================================================
# GRUPO 4 — Validator
# ===========================================================

class TestValidator(unittest.TestCase):

    # ── Teste 14: Produto duplicado ──────────────────────────
    def test_14_produto_duplicado(self):
        """Dois produtos com mesmo código → alerta de duplicata."""
        p1 = Produto(codigo="DUP001", titulo="Peça A")
        p2 = Produto(codigo="DUP001", titulo="Peça B")
        alerts = validate_batch([p1, p2])
        dup_alerts = [a for a in alerts if "vezes" in a.problema]
        self.assertGreater(len(dup_alerts), 0,
            "FALHA: duplicata não foi detectada")

    def test_codigo_vazio_gera_error(self):
        """Código vazio → alerta ERROR."""
        p = Produto(codigo="", titulo="Peça Sem Código")
        alerts = validate(p)
        erros = [a for a in alerts if a.severity.value == "ERROR"]
        self.assertTrue(any(a.campo == "codigo" for a in erros))

    def test_produto_valido_sem_alertas_error(self):
        """Produto com código → sem alertas ERROR."""
        p = Produto(codigo="X001", titulo="Peça", categoria="Cat",
                    marca="TOYOTA", numero_peca="OEM001")
        alerts = validate(p)
        erros = [a for a in alerts if a.severity.value == "ERROR"]
        self.assertEqual(len(erros), 0)

    def test_campos_ausentes_geram_warnings(self):
        """Campos importantes ausentes geram WARNING."""
        p = Produto(codigo="X001")  # sem título, marca, categoria, numero_peca
        alerts = validate(p)
        warnings = {a.campo for a in alerts if a.severity.value == "WARNING"}
        self.assertIn("titulo",       warnings)
        self.assertIn("categoria",    warnings)
        self.assertIn("marca",        warnings)
        self.assertIn("numero_peca",  warnings)


# ===========================================================
# GRUPO 5 — Round-trip CSV (Teste 15)
# ===========================================================

class TestCSVRoundTrip(unittest.TestCase):

    def test_15_roundtrip_csv(self):
        """
        Salva DataFrame em CSV e lê novamente.
        Os valores devem ser idênticos — a coluna lida é a fonte de verdade.
        """
        p = Produto(
            codigo       = "RT001",
            titulo       = "Retrovisor Teste",
            peso         = "2,5",
            largura      = "30",
            altura       = "20",
            profundidade = "15",
            quantidade   = "3",
            marca        = "TOYOTA",
            categoria    = "Retrovisores",
            observacoes  = "Observação com; ponto-e-vírgula",
        )
        exp = _make_exporter()
        df = pd.DataFrame([exp.to_row(p)], columns=COLUNAS_BLING)

        # Salva em buffer
        buf = io.BytesIO()
        df.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
        buf.seek(0)

        # Lê de volta
        df2 = pd.read_csv(buf, sep=";", dtype=str, encoding="utf-8-sig").fillna("")

        self.assertEqual(df2.iloc[0]["Código"],              "RT001",          "Código round-trip")
        self.assertEqual(df2.iloc[0]["Descrição"],           "Retrovisor Teste","Descrição round-trip")
        self.assertEqual(df2.iloc[0]["Marca"],               "TOYOTA",         "Marca round-trip")
        self.assertEqual(df2.iloc[0]["Peso bruto (Kg)"],     "2,500",          "Peso round-trip")
        self.assertEqual(df2.iloc[0]["Largura do produto"],  "30,00",          "Largura round-trip")
        self.assertEqual(df2.iloc[0]["Estoque"],             "3,00",           "Estoque round-trip")
        self.assertEqual(df2.iloc[0]["Categoria do produto"],"Retrovisores",   "Categoria round-trip")
        self.assertEqual(df2.iloc[0]["ID"],                  "",               "ID deve ser vazio")
        self.assertEqual(df2.iloc[0]["Peso líquido (Kg)"],   "",               "Peso líquido vazio")
        # Confirma número de colunas
        self.assertEqual(len(df2.columns), 59, "Deve ter 59 colunas exatas")


# ===========================================================
# GRUPO 6 — Testes de regressão com cards reais
# ===========================================================

class TestRegressaoCardsReais(unittest.TestCase):
    """
    Testa cards S01670 e S01671 (com todos os campos explícitos)
    contra resultados esperados conhecidos.
    """

    def _make_s01670(self):
        row = _make_row(**{
            "Card Name":     "CUSTOM SKU:S01670",
            "Código(OEM):":  "12348765",
            "Título:":       "Peça Teste A S10",
            "Categoria:":    "Acessórios para Veículos>>Instrumentos",
            "Peso:":         "1",
            "Largura:":      "36",
            "Altura:":       "18",
            "Profundidade:": "22",
            "Quantidade:":   "1",
            "Marca:":        "CHEVROLET",
            "Modelo:":       "S10",
            "Observações:":  "",
        })
        return row

    def _make_s01671(self):
        row = _make_row(**{
            "Card Name":     "CUSTOM SKU:S01671",
            "Código(OEM):":  "87651234",
            "Título:":       "Peça Teste B AMAROK",
            "Peso:":         "1",
            "Largura:":      "12",
            "Altura:":       "22",
            "Profundidade:": "44",
            "Quantidade:":   "3",
            "Marca:":        "VOLKSWAGEN",
            "Modelo:":       "AMAROK",
        })
        return row

    def test_S01670_adapter(self):
        """S01670: todos os campos do adapter verificados."""
        row = self._make_s01670()
        p = _make_adapter(row).parse_row(row)

        self.assertEqual(p.codigo,       "S01670")
        self.assertEqual(p.numero_peca,  "12348765")
        self.assertEqual(p.titulo,       "Peça Teste A S10")
        self.assertEqual(p.marca,        "CHEVROLET")
        self.assertEqual(p.modelo,       "S10")
        self.assertEqual(p.peso,         "1")
        self.assertEqual(p.largura,      "36")
        self.assertEqual(p.altura,       "18")
        self.assertEqual(p.profundidade, "22")
        self.assertEqual(p.quantidade,   "1")

    def test_S01670_bling(self):
        """S01670: output Bling verificado coluna por coluna."""
        row = self._make_s01670()
        p = _make_adapter(row).parse_row(row)
        bling_row = _make_exporter().to_row(p)

        self.assertEqual(bling_row["Código"],              "S01670")
        self.assertEqual(bling_row["Descrição"],           "Peça Teste A S10")
        self.assertEqual(bling_row["Marca"],               "CHEVROLET")
        self.assertEqual(bling_row["Estoque"],             "1,00")
        self.assertEqual(bling_row["Peso bruto (Kg)"],     "1,000")
        self.assertEqual(bling_row["Largura do produto"],  "36,00")
        self.assertEqual(bling_row["Altura do Produto"],   "18,00")
        self.assertEqual(bling_row["Profundidade do produto"], "22,00")
        self.assertEqual(bling_row["Categoria do produto"],
                         "Acessórios para Veículos>>Instrumentos")
        self.assertEqual(bling_row["Peso líquido (Kg)"],   "")   # IGNORAR
        self.assertEqual(bling_row["ID"],                  "")   # IGNORAR

    def test_S01670_custom(self):
        """S01670: campos customizados verificados."""
        row = self._make_s01670()
        p = _make_adapter(row).parse_row(row)
        custom = _make_exporter().to_custom_row(p)

        self.assertEqual(custom["sku"],           "S01670")
        self.assertEqual(custom["numeroDePeca"],  "12348765")
        self.assertEqual(custom["marca"],         "CHEVROLET")
        self.assertEqual(custom["modelo"],        "S10")
        self.assertEqual(custom["tipoDeVeiculo"], "Carro/Caminhonete")
        self.assertEqual(custom["condicaoDoItem"],"Novo")
        self.assertEqual(custom["origem"],        "NACIONAL")
        self.assertEqual(custom["fonteDoProduto"],"BRASIL")

    def test_S01671_completo(self):
        """S01671: adapter + Bling + custom verificados."""
        row = self._make_s01671()
        p = _make_adapter(row).parse_row(row)

        self.assertEqual(p.codigo,      "S01671")
        self.assertEqual(p.numero_peca, "87651234")
        self.assertEqual(p.marca,       "VOLKSWAGEN")
        self.assertEqual(p.modelo,      "AMAROK")
        self.assertEqual(p.quantidade,  "3")

        bling_row = _make_exporter().to_row(p)
        self.assertEqual(bling_row["Código"],          "S01671")
        self.assertEqual(bling_row["Marca"],           "VOLKSWAGEN")
        self.assertEqual(bling_row["Estoque"],         "3,00")
        self.assertEqual(bling_row["Largura do produto"], "12,00")

        custom = _make_exporter().to_custom_row(p)
        self.assertEqual(custom["sku"],          "S01671")
        self.assertEqual(custom["numeroDePeca"], "87651234")
        self.assertEqual(custom["marca"],        "VOLKSWAGEN")
        self.assertEqual(custom["modelo"],       "AMAROK")

    def test_csv_real_406_cards_sem_excecao(self):
        """
        Os 406 cards do CSV real devem ser processados sem lançar exceção.
        Não verifica os valores (a maioria terá campos vazios por design).
        """
        csv_path = r"c:/Users/roger/Downloads/produtos/jIjgRBC3 - processo-cadastro-pecas.csv"
        if not os.path.exists(csv_path):
            self.skipTest("CSV do Trello não encontrado — pulando teste real")

        df = pd.read_csv(csv_path, dtype=str).fillna("")
        adapter = TrelloAdapter(df)
        produtos = adapter.parse_dataframe(df)

        self.assertEqual(len(produtos), len(df),
            "Número de produtos deve ser igual ao número de linhas")
        for p in produtos:
            self.assertIsInstance(p, Produto)
            # campo sku sempre espelha codigo
            self.assertEqual(p.sku, p.codigo,
                f"sku deve espelhar codigo para '{p.source_name}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
