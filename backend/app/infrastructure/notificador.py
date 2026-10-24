"""Canais de envio das notificações (demo): simulado, Twilio (conta de teste), ntfy.sh (push) e WhatsApp (WAHA).

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
    exige_destino = False

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        return ResultadoEnvio(True, "simulado: nada foi enviado")


class NotificadorNtfy:
    """Push pelo ntfy.sh (ou um servidor próprio): grátis, sem cadastro, texto livre. Quem assina o tópico recebe.

    O tópico é o único "segredo" no servidor público: use um nome difícil de adivinhar e, se der, `NTFY_TOKEN`.
    """

    canal = "ntfy"
    exige_destino = False  # não há telefone: o destino é o tópico

    def __init__(self, url: str, topico: str, token: str = "", client: httpx.Client | None = None,
                 timeout: float = 15.0):
        self._url, self._topico, self._token = url.rstrip("/"), topico, token
        self._client = client or httpx.Client(timeout=timeout)

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        cabecalhos = {"Title": "Atualizacao da fila cirurgica", "Tags": "hospital", "Content-Type": "text/plain; charset=utf-8"}
        if self._token:
            cabecalhos["Authorization"] = f"Bearer {self._token}"
        try:
            r = self._client.post(f"{self._url}/{self._topico}", content=texto.encode("utf-8"), headers=cabecalhos)
        except httpx.HTTPError as e:
            return ResultadoEnvio(False, f"falha de rede: {e.__class__.__name__}")
        if r.status_code == 200:
            try:
                return ResultadoEnvio(True, f"ntfy {r.json().get('id')}")
            except ValueError:
                return ResultadoEnvio(True, "ntfy")
        return ResultadoEnvio(False, f"ntfy {r.status_code}: {r.text[:120]}")


class NotificadorWaha:
    """WhatsApp pelo WAHA (WhatsApp HTTP API): um contêiner que controla o WhatsApp Web de um chip da demo.

    NÃO É OFICIAL (contra os termos do WhatsApp): só para a demonstração, com chip descartável e poucos envios
    para gente que sabe. O destino pode ter vários números separados por vírgula.
    """

    canal = "waha"
    exige_destino = True

    def __init__(self, url: str, sessao: str = "default", api_key: str = "",
                 client: httpx.Client | None = None, timeout: float = 20.0):
        self._url, self._sessao, self._key = url.rstrip("/"), sessao or "default", api_key
        self._client = client or httpx.Client(timeout=timeout)

    @staticmethod
    def _chat_id(numero: str) -> str:
        return f"{''.join(c for c in numero if c.isdigit())}@c.us"

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        numeros = [n.strip() for n in destino.split(",") if n.strip()]
        if not numeros:
            return ResultadoEnvio(False, "sem número de destino (HP_NOTIFICA_DESTINO)")
        cabecalhos = {"X-Api-Key": self._key} if self._key else {}
        erros, ok = [], 0
        for n in numeros:
            try:
                r = self._client.post(f"{self._url}/api/sendText", headers=cabecalhos,
                                      json={"session": self._sessao, "chatId": self._chat_id(n), "text": texto})
            except httpx.HTTPError as e:
                erros.append(f"falha de rede: {e.__class__.__name__}")
                continue
            if r.status_code in (200, 201):
                ok += 1
            else:
                erros.append(f"WAHA {r.status_code}: {r.text[:100]}")
        if erros:
            return ResultadoEnvio(False, "; ".join(erros) if not ok else f"{ok} enviada(s); " + "; ".join(erros))
        return ResultadoEnvio(True, f"waha: {ok} enviada(s)")


class NotificadorMultiplo:
    """Vários canais ao mesmo tempo (ex.: waha + ntfy como plano B). Conta como enviada se algum entregou."""

    def __init__(self, canais: list):
        self._canais = canais
        self.canal = "+".join(c.canal for c in canais)
        self.exige_destino = any(getattr(c, "exige_destino", True) for c in canais)

    def enviar(self, destino: str, texto: str) -> ResultadoEnvio:
        resultados = [(c.canal, c.enviar(destino, texto)) for c in self._canais]
        detalhe = " | ".join(f"{nome}: {'ok' if r.ok else 'falhou'} ({r.detalhe})" for nome, r in resultados)
        return ResultadoEnvio(any(r.ok for _, r in resultados), detalhe)


class NotificadorTwilio:
    canal = "twilio"
    exige_destino = True

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


def _um_canal(nome: str):
    if nome == "ntfy" and settings.ntfy_topic:
        return NotificadorNtfy(settings.ntfy_url, settings.ntfy_topic, settings.ntfy_token)
    if nome == "waha" and settings.notifica_destino:
        return NotificadorWaha(settings.waha_url, settings.waha_session, settings.waha_api_key)
    tem_senha = settings.twilio_auth_token or (settings.twilio_api_key_sid and settings.twilio_api_key_secret)
    if (nome == "twilio" and settings.twilio_account_sid and tem_senha
            and settings.twilio_from and settings.notifica_destino):
        return NotificadorTwilio(settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from,
                                 api_key_sid=settings.twilio_api_key_sid,
                                 api_key_secret=settings.twilio_api_key_secret,
                                 modelo=settings.twilio_sms_template)
    return None


def criar_notificador():
    """Simulado, a menos que o(s) canal(is) em `HP_NOTIFICA_CANAL` (`twilio`, `ntfy`, `waha`; vários com vírgula)
    estejam completos na configuração. Canal incompleto é ignorado; sem nenhum, cai no simulado."""
    canais = [c for c in (_um_canal(n.strip()) for n in settings.notifica_canal.split(",")) if c is not None]
    if not canais:
        return NotificadorSimulado()
    return canais[0] if len(canais) == 1 else NotificadorMultiplo(canais)
