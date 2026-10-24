"""NotificarMudancas / EnviarNotificacoes com repositório em memória."""
from datetime import datetime, timezone

from app.application.notificacoes import EnviarNotificacoes, NotificarMudancas
from app.domain.models import LinhaFila
from app.domain.ports import ResultadoEnvio

AGORA = datetime(2026, 10, 24, tzinfo=timezone.utc)


class Repo:
    def __init__(self):
        self.itens = []

    def proximo_id(self):
        return f"NTF-{len(self.itens) + 1:05d}"

    def adicionar(self, n):
        self.itens.append(n)

    def existe_pendente(self, sid, motivo):
        return any(n.solicitacao_id == sid and n.motivo == motivo and n.status == "pendente" for n in self.itens)

    def pendentes(self, limite):
        return [n for n in self.itens if n.status == "pendente"][:limite]

    def registrar_envio(self, nid, status, em, detalhe):
        n = next(n for n in self.itens if n.notificacao_id == nid)
        n.status, n.enviada_em, n.detalhe, n.tentativas = status, em, detalhe, n.tentativas + 1


class Uow:
    def __init__(self):
        self.commits = self.desfeitos = 0

    def confirmar(self):
        self.commits += 1

    def desfazer(self):
        self.desfeitos += 1


class Canal:
    canal = "twilio"

    def __init__(self, ok=True, explode=False):
        self.ok, self.explode, self.enviadas = ok, explode, []

    def enviar(self, destino, texto):
        if self.explode:
            raise RuntimeError("boom")
        self.enviadas.append((destino, texto))
        return ResultadoEnvio(self.ok, "SM1" if self.ok else "erro")


def linha(sid, pos):
    return LinhaFila(sid, pos, "", 3, "C", 0.0, 0, 0.0, False, "v")


def montar(canal=None, limite=5, destino="+5551999990000", **kw):
    repo, uow = Repo(), Uow()
    envio = EnviarNotificacoes(repo, canal, uow, destino, limite, lambda: AGORA) if canal else None
    return NotificarMudancas(repo, uow, "twilio", kw.get("min", 10), kw.get("max", 3), envio, lambda: AGORA), repo, uow


def test_primeira_publicacao_nao_avisa_ninguem():
    n, repo, _ = montar()
    n.fila_publicada([], [linha("A", 1)])
    assert repo.itens == []


def test_mudanca_de_posicao_enfileira_e_envia_para_o_destino_da_demo():
    canal = Canal()
    n, repo, uow = montar(canal)
    n.fila_publicada([linha("A", 50), linha("B", 10)], [linha("A", 5), linha("B", 11)])
    assert [(i.solicitacao_id, i.motivo, i.status) for i in repo.itens] == [("A", "posicao", "enviada")]
    assert canal.enviadas[0][0] == "+5551999990000" and "subiu" in canal.enviadas[0][1]


def test_mesmo_aviso_pendente_nao_duplica_e_o_limite_deixa_o_resto():
    canal = Canal()
    n, repo, _ = montar(canal, limite=1)
    n.evento("A", "situacao"), n.evento("B", "situacao"), n.evento("A", "situacao")
    assert [i.status for i in repo.itens] == ["enviada", "enviada", "enviada"]  # a 1ª já tinha saído: não há pendente igual
    n2, repo2, _ = montar(None)  # sem canal: só enfileira, nada some
    n2.evento("A", "situacao"), n2.evento("A", "situacao")
    assert len(repo2.itens) == 1


def test_recontato_enfileira_no_maximo_o_limite_sem_commit():
    n, repo, uow = montar(max=2)
    n.enfileirar(["C", "A", "B", "D"], "recontato")
    assert sorted(i.solicitacao_id for i in repo.itens) == ["A", "B"] and uow.commits == 0


def test_canal_que_falha_marca_falhou_e_canal_que_explode_nao_levanta():
    n, repo, _ = montar(Canal(ok=False))
    n.evento("A", "situacao")
    assert repo.itens[0].status == "falhou" and repo.itens[0].detalhe == "erro"
    n2, repo2, uow2 = montar(Canal(explode=True))
    n2.evento("A", "situacao")  # a decisão que disparou já valeu
    assert uow2.desfeitos == 1
