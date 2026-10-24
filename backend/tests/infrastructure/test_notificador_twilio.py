"""Twilio (conta de teste) pela API REST, sem rede: o transporte é simulado."""
import httpx

from app.infrastructure.notificador import NotificadorSimulado, NotificadorTwilio, sem_acentos


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
