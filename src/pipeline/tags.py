# ============================================================
# pipeline/tags.py — Geração das Tags do Bling
# ============================================================
# Formato: "GRUPO1:TAG1|GRUPO2:TAG2"
# Configuração em src/config.py → TAG_CONFIG
# Para mudar a tag mensal: edite TAG_CONFIG["tag_mensal"]["valor"]
# ============================================================

from src.config import TAG_CONFIG as _DEFAULT_TAG_CONFIG


def build_tags(tag_config: dict | None = None) -> str:
    """
    Monta a string de tags no formato esperado pelo Bling.
    Usa TAG_CONFIG de config.py se nenhuma config for passada.

    Resultado exemplo: "CADASTRO:1 - CONFERÊNCIA|ROGER:AGOSTO 2026"
    """
    cfg = tag_config if tag_config is not None else _DEFAULT_TAG_CONFIG
    partes: list = []

    for item in cfg.get("tags_fixas", []):
        grupo = (item.get("grupo") or "").strip()
        tag   = (item.get("tag")   or "").strip()
        if grupo and tag:
            partes.append(f"{grupo}:{tag}")

    mensal = cfg.get("tag_mensal", {})
    if mensal.get("habilitada", False):
        grupo = (mensal.get("grupo") or "").strip()
        valor = (mensal.get("valor") or "").strip()
        if grupo and valor:
            partes.append(f"{grupo}:{valor}")

    return "|".join(partes)
