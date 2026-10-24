"""Twilio (conta de teste) pela API REST, sem rede: o transporte é simulado."""
import httpx

from app.infrastructure.notificador import NotificadorNtfy, NotificadorSimulado, NotificadorTwilio, sem_acentos


def cliente(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_envia_com_basic_auth_e_corpo_sem_acentos():
    vistos = {}

    def handler(request: httpx.Request) -> httpx.Response:
        vistos["url"], vistos["auth"] = str(request.url), request.headers["authorization"]
        vistos["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(201, json={"sid": "SM123", "status": "queued"})

    t = NotificadorTwilio("ACtest", "segredo", "+15005550006", cliente(handler))
    r = t.enviar("+5551999990000", "[DEMO] situação atualizada")
    assert (r.ok, r.detalhe) == (True, "SM123")
    assert vistos["url"] == "https://api.twilio.com/2010-04-01/Accounts/ACtest/Messages.json"
    assert vistos["auth"].startswith("Basic ")
    assert vistos["form"] == {"To": "+5551999990000", "From": "+15005550006", "Body": "[DEMO] situacao atualizada"}


def test_api_key_autentica_com_sk_mas_o_endereco_usa_o_account_sid():
    vistos = {}

    def handler(request):
        vistos["url"], vistos["auth"] = str(request.url), request.headers["authorization"]
        return httpx.Response(201, json={"sid": "SM9"})

    t = NotificadorTwilio("ACtest", "", "+1500", cliente(handler), api_key_sid="SKabc", api_key_secret="s3gredo")
    assert t.enviar("+55", "x").ok
    assert "/Accounts/ACtest/" in vistos["url"]
    import base64
    assert base64.b64decode(vistos["auth"].split()[1]).decode() == "SKabc:s3gredo"


def test_account_sid_com_cara_de_api_key_da_um_erro_claro_sem_chamar_a_rede():
    def handler(request):
        raise AssertionError("não devia chamar a rede")

    r = NotificadorTwilio("SKabc", "segredo", "+1500", cliente(handler)).enviar("+55", "x")
    assert r.ok is False and "Account SID" in r.detalhe and "segredo" not in r.detalhe


def test_modelo_da_conta_de_teste_vai_como_body_no_lugar_do_texto():
    vistos = {}

    def handler(request):
        vistos["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(201, json={"sid": "SMm"})

    t = NotificadorTwilio("ACtest", "segredo", "+15005550006", cliente(handler), modelo="sms_event_notifications")
    r = t.enviar("+5511999990002", "[DEMO] texto livre")
    assert vistos["form"]["Body"] == "sms_event_notifications" and "modelo sms_event_notifications" in r.detalhe


def test_whatsapp_prefixa_o_destino_e_mantem_os_acentos():
    vistos = {}

    def handler(request):
        vistos["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(201, json={"sid": "SMwa"})

    t = NotificadorTwilio("ACtest", "segredo", "whatsapp:+14155238886", cliente(handler))
    assert t.enviar("+5551999990000", "situação atualizada").ok
    assert vistos["form"] == {"To": "whatsapp:+5551999990000", "From": "whatsapp:+14155238886",
                              "Body": "situação atualizada"}
    t.enviar("whatsapp:+5551999990000", "x")  # já com prefixo: não duplica
    assert vistos["form"]["To"] == "whatsapp:+5551999990000"


def test_erro_do_twilio_vira_falha_sem_vazar_a_credencial():
    def handler(request):
        return httpx.Response(400, json={"code": 21608, "message": "The number is unverified (trial account)"})

    r = NotificadorTwilio("ACtest", "segredo", "+1500", cliente(handler)).enviar("+55", "x")
    assert r.ok is False and "21608" not in r.detalhe and "unverified" in r.detalhe
    assert "segredo" not in r.detalhe and "ACtest" not in r.detalhe


def test_falha_de_rede_vira_falha():
    def handler(request):
        raise httpx.ConnectError("sem rede")

    r = NotificadorTwilio("ACtest", "segredo", "+1500", cliente(handler)).enviar("+55", "x")
    assert r.ok is False and "ConnectError" in r.detalhe


def test_simulado_nao_envia_nada():
    r = NotificadorSimulado().enviar("+55", "x")
    assert r.ok and "nada foi enviado" in r.detalhe


def test_sem_acentos():
    assert sem_acentos("posição são ção") == "posicao sao cao"


def test_ntfy_posta_no_topico_com_texto_livre_e_acentos():
    vistos = {}

    def handler(request):
        vistos["url"], vistos["corpo"], vistos["h"] = str(request.url), request.content.decode("utf-8"), request.headers
        return httpx.Response(200, json={"id": "abc123", "event": "message"})

    r = NotificadorNtfy("https://ntfy.sh/", "healthprior-teste", client=cliente(handler)).enviar("", "sua posição mudou")
    assert (r.ok, r.detalhe) == (True, "ntfy abc123")
    assert vistos["url"] == "https://ntfy.sh/healthprior-teste" and vistos["corpo"] == "sua posição mudou"
    assert "authorization" not in vistos["h"] and vistos["h"]["title"] == "Atualizacao da fila cirurgica"


def test_ntfy_com_token_e_com_erro():
    def handler(request):
        assert request.headers["authorization"] == "Bearer tk_x"
        return httpx.Response(403, text="forbidden")

    r = NotificadorNtfy("https://ntfy.sh", "t", token="tk_x", client=cliente(handler)).enviar("", "x")
    assert r.ok is False and "403" in r.detalhe and "tk_x" not in r.detalhe


def test_ntfy_nao_exige_destino_e_cai_no_simulado_sem_topico():
    from app.infrastructure import notificador as n
    import dataclasses

    assert NotificadorNtfy("https://ntfy.sh", "t").exige_destino is False
    original = n.settings
    try:
        n.settings = dataclasses.replace(original, notifica_canal="ntfy", ntfy_topic="")
        assert n.criar_notificador().canal == "simulado"
        n.settings = dataclasses.replace(original, notifica_canal="ntfy", ntfy_topic="meu-topico")
        assert n.criar_notificador().canal == "ntfy"
    finally:
        n.settings = original
