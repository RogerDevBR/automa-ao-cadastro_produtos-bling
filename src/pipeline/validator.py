# ============================================================
# pipeline/validator.py — Validação dos Produtos
# ============================================================
# validate(produto)       → list[ValidationAlert]
# validate_batch(lista)   → list[ValidationAlert]
#
# Severidade:
#   ERROR   → bloqueia exportação (campo obrigatório ausente)
#   WARNING → alerta visual (campo importante ausente ou duplicata)
#
# REGRA: o validador apenas INFORMA — não corrige, não preenche.
# ============================================================

from dataclasses import dataclass
from enum import Enum
from collections import Counter
from src.domain.produto import Produto


class Severity(str, Enum):
    ERROR   = "ERROR"
    WARNING = "WARNING"


@dataclass
class ValidationAlert:
    source_id:   str
    source_name: str
    campo:       str
    problema:    str
    acao:        str
    severity:    Severity


# ----------------------------------------------------------
def validate(produto: Produto) -> list:
    """
    Valida um único produto.
    Retorna lista de ValidationAlert (pode ser vazia = produto OK).
    """
    alerts: list = []

    def _add(campo: str, problema: str, acao: str, severity: Severity):
        alerts.append(ValidationAlert(
            source_id   = produto.source_id,
            source_name = produto.source_name,
            campo       = campo,
            problema    = problema,
            acao        = acao,
            severity    = severity,
        ))

    # ── Obrigatório — bloqueia exportação ────────────────────
    if not produto.codigo:
        _add(
            campo    = "codigo",
            problema = "Código ausente",
            acao     = "Produto não será exportado — adicionar Código no Trello",
            severity = Severity.ERROR,
        )

    # ── Importantes — alerta visual ───────────────────────────
    if not produto.titulo:
        _add(
            campo    = "titulo",
            problema = "Título ausente",
            acao     = "Bling.Descrição ficará vazio — revisar na finalização",
            severity = Severity.WARNING,
        )

    if not produto.categoria:
        _add(
            campo    = "categoria",
            problema = "Categoria ausente",
            acao     = "Bling.Categoria ficará vazio — adicionar na finalização",
            severity = Severity.WARNING,
        )

    if not produto.marca:
        _add(
            campo    = "marca",
            problema = "Marca ausente",
            acao     = "Bling.Marca ficará vazio",
            severity = Severity.WARNING,
        )

    if not produto.numero_peca:
        _add(
            campo    = "numero_peca",
            problema = "Número de peça (OEM) ausente",
            acao     = "numeroDePeca ficará vazio",
            severity = Severity.WARNING,
        )

    return alerts


# ----------------------------------------------------------
def validate_batch(produtos: list) -> list:
    """
    Valida todos os produtos.
    Também detecta e reporta códigos duplicados.
    """
    alerts: list = []

    # Validação individual
    for p in produtos:
        alerts.extend(validate(p))

    # Detecção de duplicatas
    codigos = [p.codigo for p in produtos if p.codigo]
    contagem = Counter(codigos)
    duplicados = {cod for cod, cnt in contagem.items() if cnt > 1}

    if duplicados:
        for p in produtos:
            if p.codigo in duplicados:
                alerts.append(ValidationAlert(
                    source_id   = p.source_id,
                    source_name = p.source_name,
                    campo       = "codigo",
                    problema    = f"Código '{p.codigo}' aparece {contagem[p.codigo]} vezes",
                    acao        = "Verificar manualmente — não exportar automaticamente",
                    severity    = Severity.WARNING,
                ))

    return alerts
