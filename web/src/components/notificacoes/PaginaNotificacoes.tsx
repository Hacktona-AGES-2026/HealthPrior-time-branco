import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, BellRing, Loader2, RefreshCw, Send } from "lucide-react"
import { toast } from "sonner"
import { enviarNotificacoes, listarNotificacoes, URL_API, type ListaNotificacoes, type Notificacao } from "@/api/cliente"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

const MOTIVO: Record<Notificacao["motivo"], string> = {
  posicao: "Mudou de posição",
  situacao: "Situação atualizada",
  recontato: "Sem evento há muito tempo",
}
const STATUS: Record<Notificacao["status"], { rotulo: string; variante: "secondary" | "default" | "destructive" }> = {
  pendente: { rotulo: "Pendente", variante: "secondary" },
  enviada: { rotulo: "Enviada", variante: "default" },
  falhou: { rotulo: "Falhou", variante: "destructive" },
}

type Estado = { tipo: "carregando" } | { tipo: "erro"; mensagem: string } | { tipo: "ok"; dados: ListaNotificacoes }

export default function PaginaNotificacoes() {
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" })
  const [enviando, setEnviando] = useState(false)
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    listarNotificacoes(controle.signal)
      .then((dados) => setEstado({ tipo: "ok", dados }))
      .catch((e: unknown) => {
        if (!controle.signal.aborted) setEstado({ tipo: "erro", mensagem: e instanceof Error ? e.message : "Erro inesperado" })
      })
    return () => controle.abort()
  }, [tentativa])

  const recarregar = useCallback(() => setTentativa((t) => t + 1), [])

  async function enviar() {
    setEnviando(true)
    try {
      const r = await enviarNotificacoes()
      toast.success(`${r.enviadas} enviadas, ${r.falhas} com falha`, { description: r.pendentes ? `${r.pendentes} seguem pendentes (limite por rodada).` : undefined })
    } catch (e) {
      toast.error("Não foi possível enviar", { description: e instanceof Error ? e.message : undefined })
    } finally {
      setEnviando(false)
      recarregar()
    }
  }

  const dados = estado.tipo === "ok" ? estado.dados : null
  const real = !!dados && dados.canal !== "simulado"

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-5xl space-y-4 p-4">
        <header className="fx-fade-up space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <BellRing className="size-4" aria-hidden /> Notificações ao paciente (demonstração)
          </h2>
          <p className="text-sm text-muted-foreground">
            Avisos de mudança de posição, de situação e de recontato. O texto é genérico (sem classe nem posição exata) e, na demonstração, tudo vai para <b className="text-foreground">um número
            só</b>, nunca para o do paciente.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-2" aria-live="polite">
          {dados && (
            <Badge variant={real ? "default" : "secondary"}>
              {real ? `${dados.canal.replace("waha", "WhatsApp").replace("ntfy", "push (ntfy)").replace("twilio", "Twilio")} → ${dados.destino ?? "sem destino"}` : "Canal simulado: nada é enviado"}
            </Badge>
          )}
          {dados && <span className="text-sm text-muted-foreground"><b className="tabular-nums text-foreground">{dados.total}</b> mensagens</span>}
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={recarregar} aria-label="Atualizar a lista">
              <RefreshCw aria-hidden /> Atualizar
            </Button>
            <Button size="sm" disabled={enviando} onClick={enviar}>
              {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <Send aria-hidden />} Enviar pendentes
            </Button>
          </div>
        </div>

        {estado.tipo === "carregando" && (
          <div className="space-y-2" role="status">
            <span className="fx-loading-dots text-sm text-muted-foreground">Carregando notificações</span>
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
          </div>
        )}
        {estado.tipo === "erro" && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm" role="alert">
            <p className="flex items-center gap-2 font-semibold text-destructive"><AlertTriangle className="size-4" aria-hidden /> Não foi possível carregar</p>
            <p className="mt-1 text-muted-foreground">{estado.mensagem} (API em <code className="rounded bg-muted px-1">{URL_API}</code>)</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={recarregar}><RefreshCw aria-hidden /> Tentar de novo</Button>
          </div>
        )}
        {dados && dados.itens.length === 0 && (
          <div className="rounded-xl bg-muted/40 p-8 text-center text-sm text-muted-foreground">
            Nada enfileirado ainda. Aprove ou edite uma classe no Inbox, resolva uma pendência bloqueante ou rode a atualização diária.
          </div>
        )}
        {dados && dados.itens.length > 0 && (
          <ul className="space-y-2" aria-label="Notificações">
            {dados.itens.map((n) => (
              <li key={n.notificacao_id} className="rounded-xl border bg-card p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={STATUS[n.status].variante}>{STATUS[n.status].rotulo}</Badge>
                  <span className="font-medium">{MOTIVO[n.motivo]}</span>
                  <span className="font-mono text-xs text-muted-foreground">{n.solicitacao_id}</span>
                  <span className="ml-auto font-mono text-xs text-muted-foreground">{n.notificacao_id} · {n.canal}</span>
                </div>
                <p className={cn("mt-1.5 leading-snug")}>{n.texto}</p>
                {n.detalhe && <p className="mt-1 text-xs text-muted-foreground">{n.detalhe}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
