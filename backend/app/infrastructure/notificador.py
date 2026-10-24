"""Canais de envio das notificações (demo): simulado e Twilio (conta de teste).

O Twilio é chamado pela API REST (`httpx`), sem SDK. A conta de teste só entrega a números verificados e
acrescenta um aviso de "trial" à mensagem; por isso o destino é sempre o número da demo, nunca o do paciente.

WhatsApp: se `TWILIO_FROM` começa com `whatsapp:` (o número do sandbox do Twilio, `whatsapp:+14155238886`), o
destino também vai como `whatsapp:+55...` e o texto segue com acentos. No sandbox a pessoa precisa antes mandar
`join <código>` ao número do sandbox, e só recebe texto livre por 24 h depois da última mensagem dela.
"""
from __future__ import annotations

import unicodedata

import httpx

from app.config import settings
from app.domain.ports import ResultadoEnvio


def sem_acentos(texto: str) -> str:
    """SMS com acento vira UCS-2 (70 caracteres por parte); sem acento cabe em GSM-7 (160)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


class NotificadorSimulado:
    canal = "simulado"

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        return ResultadoEnvio(True, "simulado: nada foi enviado")


class NotificadorTwilio:
    canal = "twilio"

    def __init__(self, account_sid: str, auth_token: str, remetente: str,
                 client: httpx.Client | None = None, timeout: float = 15.0,
                 api_key_sid: str = "", api_key_secret: str = "", modelo: str = ""):
        # Conta de teste enviando ao Brasil: só aceita modelos pré-definidos; o Body é o NOME do modelo.
        self._modelo = modelo
        # O endereço usa sempre o Account SID (AC...); a senha pode ser o Auth Token ou uma API Key (SK... + secret).
        self._sid, self._from = account_sid, remetente
        self._usuario, self._token = (api_key_sid, api_key_secret) if api_key_sid else (account_sid, auth_token)
        self._client = client or httpx.Client(timeout=timeout)

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        if not self._sid.startswith("AC"):
            return ResultadoEnvio(False, "TWILIO_ACCOUNT_SID precisa ser o Account SID (começa com AC); "
                                         "SK é a API Key: use TWILIO_API_KEY_SID e TWILIO_API_KEY_SECRET")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        whatsapp = self._from.lower().startswith("whatsapp:")
        para = destino if not whatsapp or destino.lower().startswith("whatsapp:") else f"whatsapp:{destino}"
        try:
            r = self._client.post(url, auth=(self._usuario, self._token),
                                  data={"To": para, "From": self._from, "Body": self._modelo or (texto if whatsapp else sem_acentos(texto))})
        except httpx.HTTPError as e:
            return ResultadoEnvio(False, f"falha de rede: {e.__class__.__name__}")
        corpo = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code in (200, 201):
            return ResultadoEnvio(True, f"{corpo.get('sid')} (modelo {self._modelo})" if self._modelo else corpo.get("sid"))
        # o erro do Twilio traz código e mensagem; nunca a credencial
        return ResultadoEnvio(False, f"Twilio {r.status_code}: {corpo.get('message') or r.text[:120]}")


def criar_notificador() -> NotificadorSimulado | NotificadorTwilio:
    """Simulado, a menos que o canal seja `twilio` e as credenciais e o destino estejam configurados."""
    tem_senha = settings.twilio_auth_token or (settings.twilio_api_key_sid and settings.twilio_api_key_secret)
    if (settings.notifica_canal == "twilio" and settings.twilio_account_sid and tem_senha
            and settings.twilio_from and settings.notifica_destino):
        return NotificadorTwilio(settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from,
                                 api_key_sid=settings.twilio_api_key_sid,
                                 api_key_secret=settings.twilio_api_key_secret,
                                 modelo=settings.twilio_sms_template)
    return NotificadorSimulado()
