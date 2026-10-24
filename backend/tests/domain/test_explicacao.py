"""US-21 · Textos de explicação (funções puras)."""
from app.domain.explicacao import camada_motivo, montar_explicacao


def _explica(**kw):
    base = dict(posicao=1, camada=1, cid="C18.7", classe="A2", prazo_dias=21, pct_prazo=6276.2,
                dias_em_fila=1318, motivos=[], editado_manualmente=False, editado_por=None,
                status_fila="ativa", motivo_status=None)
    base.update(kw)
    return montar_explicacao(**base)


def test_camada_1_menciona_cid_e_posicao():
    texto = _explica()
    assert "Posição 1" in texto
    assert "C18.7" in texto
    assert "camada 1" in texto
    assert "1318 dias em fila" in texto and "6276.2% do prazo" in texto


def test_sem_fila_publicada_diz_que_ainda_nao_esta_na_fila():
    texto = _explica(posicao=None, camada=None)
    assert texto.startswith("Ainda não está na fila publicada.")
    assert "Classe A2" in texto  # o score continua explicável


def test_editado_menciona_quem_editou():
    texto = _explica(editado_manualmente=True, editado_por="Silas")
    assert "editada manualmente por Silas" in texto


def test_editado_sem_nome_fala_do_regulador():
    assert "editada manualmente pelo regulador" in _explica(editado_manualmente=True)


def test_suspensa_menciona_o_motivo():
    texto = _explica(status_fila="suspensa", motivo_status="paciente operou pelo convênio")
    assert "Solicitação suspensa: paciente operou pelo convênio." in texto


def test_removida_sem_motivo_registrado():
    assert _explica(status_fila="removida").endswith("Solicitação removida.")


def test_no_maximo_tres_motivos_e_quatro_frases():
    motivos = ["m1", "m2", "m3", "m4"]
    texto = _explica(motivos=motivos, editado_manualmente=True, editado_por="X",
                     status_fila="suspensa", motivo_status="saiu")
    assert "m3" in texto and "m4" not in texto
    assert texto.count(". ") + 1 <= 4


def test_camada_motivo_por_camada():
    assert camada_motivo(1, "C18.7", None) == "Oncológico pelo CID C18.7"
    assert camada_motivo(2, "I50", "Camada 2: urgente (dor EVA 8). Sintomas: x.") == \
        "Camada 2: urgente (dor EVA 8)"
    assert camada_motivo(3, "I10", "Camada 3: sem sinais clínicos de urgência. Classe B.") == \
        "Camada 3: sem sinais clínicos de urgência"
    assert camada_motivo(None, "I10", None) is None
