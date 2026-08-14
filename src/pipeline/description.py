# ============================================================
# pipeline/description.py — Geração da Descrição Curta
# ============================================================
# Único campo dinâmico: {TITULO}
# Não reconstruir título. Não adicionar marca/modelo/SKU.
# Se título vazio → retorna string vazia.
# ============================================================

from src.config import DESCRICAO_CURTA_TEMPLATE


def build_short_description(titulo: str) -> str:
    """
    Gera o HTML da Descrição Curta usando o template fixo em config.py.

    - O único campo dinâmico é o título informado.
    - Não adiciona marca, modelo, SKU ou qualquer outra informação.
    - Retorna string vazia se o título estiver vazio (não inventa).
    - Garante linha única sem quebras (\\n/\\r) que corrompem o CSV.
    """
    titulo = (titulo or "").strip()
    if not titulo:
        return ""

    html = DESCRICAO_CURTA_TEMPLATE.replace("{TITULO}", titulo)
    # Remove quebras de linha para garantir linha única no CSV
    return html.replace("\n", "").replace("\r", "").strip()
