"""Canais de envio das notificações (demo): simulado e Twilio (conta de teste).

O Twilio é chamado pela API REST (`httpx`), sem SDK. A conta de teste só entrega a números verificados e
acrescenta um aviso de "trial" à mensagem; por isso o destino é sempre o número da demo, nunca o do paciente.
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
                 client: httpx.Client | None = None, timeout: float = 15.0):
        self._sid, self._token, self._from = account_sid, auth_token, remetente
        self._client = client or httpx.Client(timeout=timeout)

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        try:
            r = self._client.post(url, auth=(self._sid, self._token),
                                  data={"To": destino, "From": self._from, "Body": sem_acentos(texto)})
        except httpx.HTTPError as e:
            return ResultadoEnvio(False, f"falha de rede: {e.__class__.__name__}")
        corpo = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code in (200, 201):
            return ResultadoEnvio(True, corpo.get("sid"))
        # o erro do Twilio traz código e mensagem; nunca a credencial
        return ResultadoEnvio(False, f"Twilio {r.status_code}: {corpo.get('message') or r.text[:120]}")


def criar_notificador() -> NotificadorSimulado | NotificadorTwilio:
    """Simulado, a menos que o canal seja `twilio` e as credenciais e o destino estejam configurados."""
    if (settings.notifica_canal == "twilio" and settings.twilio_account_sid and settings.twilio_auth_token
            and settings.twilio_from and settings.notifica_destino):
        return NotificadorTwilio(settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from)
    return NotificadorSimulado()
