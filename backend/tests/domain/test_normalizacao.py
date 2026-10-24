from app.domain.preprocessing.normalizacao import normalizar_nome, normalizar_prioridade


def test_nome_mesma_pessoa_grafias_diferentes():
    # PAC-00087
    assert normalizar_nome("Jurema Quadros Weber") == normalizar_nome("JUREMA QUADROS WEBER")


def test_prioridade():
    assert normalizar_prioridade("Média") == "media"
    assert normalizar_prioridade("Baixa") == "baixa"
    assert normalizar_prioridade("  ") is None
    assert normalizar_prioridade(None) is None
