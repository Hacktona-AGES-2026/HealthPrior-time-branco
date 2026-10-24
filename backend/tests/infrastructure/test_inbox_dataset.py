"""US-12 · Inbox sobre o dataset real, sem banco (SWALIS por regras)."""
from __future__ import annotations

import pytest

from app.application.listar_inbox import ListarInbox
from app.config import settings
from app.domain.inbox import classe_referencia, ORDEM_CLASSES
from app.domain.models import LinhaFila
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.swalis_regras import criar_swalis

pytestmark = pytest.mark.skipif(not (settings.data_dir / "fila_cirurgica.csv").exists(),
                                reason="dataset ausente")


class _Fila:
    def __init__(self, ids):
        self._ids = ids

    def obter_publicada(self):
        return [LinhaFila(i, n, "", 2, "C", 0.0, 0, 0.0, False, "r")
                for n, i in enumerate(self._ids, start=1)]

    def publicada_em(self):
        return None


class _Sols:
    def __init__(self, sols):
        self._s = sols

    def listar(self, apenas_ativas=True):
        return list(self._s)


class _Eventos:
    def __init__(self, por_id):
        self._e = por_id

    def listar_todos(self):
        return [e for lst in self._e.values() for e in lst]


def test_inbox_do_dataset():
    sols, eventos = carregar_do_csv(settings.data_dir)
    inbox = ListarInbox(_Fila([s.solicitacao_id for s in sols]), _Sols(sols),
                        _Eventos(eventos), criar_swalis()).executar()
    ordem = {c: i for i, c in enumerate(ORDEM_CLASSES)}
    sobem = sum(1 for i in inbox.itens if ordem[i.classe_sugerida] < ordem[i.classe_atual])
    desce = inbox.total - sobem
    print(f"\nINBOX: total={inbox.total} sobem={sobem} descem={desce} "
          f"primeiros={[i.solicitacao_id for i in inbox.itens[:3]]}")
    assert inbox.total > 0
    item = next((i for i in inbox.itens if i.solicitacao_id == "SOL-2025-00048"), None)
    assert item is not None, "SOL-2025-00048 deveria estar no inbox"
    assert item.classe_sugerida.value == "A2"
