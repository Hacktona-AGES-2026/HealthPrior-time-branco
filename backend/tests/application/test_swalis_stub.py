from datetime import date

from app.domain.enums import Classe
from app.domain.models import Solicitacao
from app.infrastructure.swalis_stub import SwalisStub


def test_stub_oncologico_vira_a2():
    sol = Solicitacao("SOL-2023-00010", "PAC-00467", "PROC", "C18.7", date(2023, 3, 15),
                      oncologico=True, prioridade_norm="baixa")
    r = SwalisStub(ref_date=date(2026, 10, 23)).calcular(sol, [])
    assert r.classe_sistema == Classe.A2
    assert r.pct_prazo_consumido > 100
