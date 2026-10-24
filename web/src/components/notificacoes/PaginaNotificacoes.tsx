import { useCallback, useEffect, useMemo, useState } from "react"
import { AlertTriangle, BellRing, Loader2, RefreshCw, Send } from "lucide-react"
import { toast } from "sonner"
import { enviarNotificacoes, listarNotificacoes, type ListaNotificacoes, type Notificacao } from "@/api/cliente"
import { mensagemDeErro, nomeDoPaciente, plural } from "@/lib/mensagens"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { DialogoConfirmacao } from "@/components/shared/DialogoConfirmacao"

type Filtro = "todas" | "pendente" | "enviada" | "falhou"

const MOTIVO: Record<Notificacao["motivo"], string> = {
  posicao: "Mudou de posição",
  situacao: "Situação atualizada",
  recontato: "Sem notícias há muito tempo",
}
const STATUS: Record<Notificacao["status"], { rotulo: string; ponto: string }> = {
  pendente: { rotulo: "Para enviar", ponto: "bg-amber-500" },
  enviada: { rotulo: "Enviada", ponto: "bg-emerald-600" },
  falhou: { rotulo: "Falhou", ponto: "bg-destructive" },
}
const NOME_CANAL: Record<string, string> = { waha: "WhatsApp", ntfy: "push (ntfy)", twilio: "SMS/WhatsApp (Twilio)" }
const FILTROS: { id: Filtro; rotulo: string }[] = [
  { id: "todas", rotulo: "Todos" },
  { id: "pendente", rotulo: "Para enviar" },
  { id: "enviada", rotulo: "Enviados" },
  { id: "falhou", rotulo: "Falharam" },
]

type Estado = { tipo: "carregando" } | { tipo: "erro"; mensagem: string } | { tipo: "ok"; dados: ListaNotificacoes }

/** O texto que o paciente lê, sem o prefixo de demonstração (o paciente já aparece na linha). */
const semPrefixo = (texto: string) => texto.replace(/^\[DEMO [^\]]+\]\s*(Atualizacao da fila cirurgica:\s*)?/i, "")
const hora = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : ""
const nomeCanal = (canal: string) => canal.split("+").map((c) => NOME_CANAL[c] ?? c).join(" + ")

export default function PaginaNotificacoes() {
  const abrirFicha = useStore((s) => s.abrirFicha)
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" })
  const [filtro, setFiltro] = useState<Filtro>("todas")
  const [enviando, setEnviando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    listarNotificacoes(controle.signal)
      .then((dados) => setEstado({ tipo: "ok", dados }))
      .catch((e: unknown) => {
        if (!controle.signal.aborted) setEstado({ tipo: "erro", mensagem: mensagemDeErro(e) })
      })
    return () => controle.abort()
  }, [tentativa])

  const recarregar = useCallback(() => setTentativa((t) => t + 1), [])

  const dados = estado.tipo === "ok" ? estado.dados : null
  const real = !!dados && dados.canal !== "simulado"

  const contagem = useMemo(() => {
    const c = { todas: 0, pendente: 0, enviada: 0, falhou: 0 }
    for (const n of dados?.itens ?? []) {
      c.todas++
      c[n.status]++
    }
    return c
  }, [dados])
  const pendentes = contagem.pendente
  const itens = useMemo(() => (dados?.itens ?? []).filter((n) => filtro === "todas" || n.status === filtro), [dados, filtro])

  async function enviar() {
    setConfirmando(false)
    setEnviando(true)
    try {
      const r = await enviarNotificacoes()
      const descricao = [r.falhas > 0 ? `${plural(r.falhas, "falhou", "falharam")}.` : "", r.pendentes > 0 ? `Ainda faltam ${r.pendentes}: envie de novo.` : ""].filter(Boolean).join(" ") || undefined
      if (r.enviadas === 0 && r.falhas > 0) toast.error("Nenhum aviso foi enviado", { description: descricao })
      else if (r.enviadas === 0) toast.info("Não havia avisos para enviar")
      else toast.success(plural(r.enviadas, "aviso enviado", "avisos enviados"), { description: descricao })
    } catch (e) {
      toast.error("Não foi possível enviar os avisos", { description: mensagemDeErro(e) })
    } finally {
      setEnviando(false)
      recarregar()
    }
  }

  // Num canal real cada aviso é uma mensagem separada no celular: sempre confirma antes. No simulado nada sai.
  const aoClicarEnviar = () => (real ? setConfirmando(true) : void enviar())

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-4xl space-y-4 p-4">
        <header className="space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <BellRing className="size-4" aria-hidden /> Avisos ao paciente
          </h2>
          <p className="text-sm text-muted-foreground">
            Quando a situação ou a posição de um paciente muda, um aviso curto fica pronto aqui. Cada aviso é uma mensagem separada, sem classe nem posição exata.
          </p>
        </header>

        {dados && (
          <div className={cn("flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border p-3 text-sm", real ? "border-primary/30 bg-primary/5" : "bg-muted/40")}>
            <p className="min-w-full flex-1 @lg:min-w-0">
              {real ? (
                <>
                  Os avisos saem por <b>{nomeCanal(dados.canal)}</b> para <b className="break-all">{dados.destino ?? "um destino sem nome"}</b>, nunca para o telefone do paciente.
                </>
              ) : (
                <>Modo de demonstração: <b>nada é enviado de verdade</b>. A lista mostra o que o paciente receberia.</>
              )}
            </p>
            <div className="flex items-center gap-2">
              <Button variant="outline" className="h-9" onClick={recarregar} aria-label="Atualizar a lista">
                <RefreshCw aria-hidden /> Atualizar
              </Button>
              <Button className="h-9" disabled={enviando || pendentes === 0} onClick={aoClicarEnviar}>
                {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <Send aria-hidden />}
                {pendentes === 0 ? "Nada para enviar" : `Enviar pendentes (${pendentes})`}
              </Button>
            </div>
          </div>
        )}

        {dados && dados.itens.length > 0 && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filtrar avisos">
            {FILTROS.map((f) => (
              <button
                key={f.id}
                type="button"
                aria-pressed={filtro === f.id}
                onClick={() => setFiltro(f.id)}
                className={cn(
                  "inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                  filtro === f.id ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-muted"
                )}
              >
                {f.rotulo}
                <span className="tabular-nums opacity-80">{contagem[f.id]}</span>
              </button>
            ))}
          </div>
        )}

        {estado.tipo === "carregando" && (
          <div className="space-y-2" role="status" aria-label="Carregando os avisos">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
          </div>
        )}
        {estado.tipo === "erro" && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm" role="alert">
            <p className="flex items-center gap-2 font-semibold text-destructive"><AlertTriangle className="size-4" aria-hidden /> Não foi possível carregar os avisos</p>
            <p className="mt-1 text-muted-foreground">{estado.mensagem}</p>
            <Button variant="outline" className="mt-3 h-9" onClick={recarregar}><RefreshCw aria-hidden /> Tentar de novo</Button>
          </div>
        )}
        {dados && dados.itens.length === 0 && (
          <div className="rounded-xl bg-muted/40 p-8 text-center text-sm text-muted-foreground">
            Nenhum aviso ainda. Eles aparecem quando você muda a classe de um paciente, resolve uma pendência que bloqueia ou publica a fila.
          </div>
        )}
        {dados && dados.itens.length > 0 && itens.length === 0 && (
          <p className="rounded-xl bg-muted/40 p-6 text-center text-sm text-muted-foreground">Nenhum aviso nesta lista.</p>
        )}
        {itens.length > 0 && (
          <ul className="divide-y rounded-xl border bg-card" aria-label="Avisos">
            {itens.map((n) => (
              <li key={n.notificacao_id} className="flex flex-col gap-1 p-3 text-sm @lg:flex-row @lg:items-start @lg:gap-4">
                <div className="flex shrink-0 items-center gap-2 @lg:w-44 @lg:flex-col @lg:items-start @lg:gap-1">
                  <span className="inline-flex items-center gap-1.5 font-medium">
                    <span className={cn("size-2 rounded-full", STATUS[n.status].ponto)} aria-hidden />
                    {STATUS[n.status].rotulo}
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {n.status === "pendente" ? `Criado ${hora(n.criada_em)}` : hora(n.enviada_em ?? n.criada_em)}
                  </span>
                </div>
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="flex flex-wrap items-baseline gap-x-2">
                    <button type="button" className="font-medium underline-offset-2 hover:underline focus-visible:underline" onClick={() => abrirFicha(n.solicitacao_id)}>
                      {nomeDoPaciente(n.solicitacao_id)}
                    </button>
                    <span className="text-muted-foreground">{MOTIVO[n.motivo]}</span>
                  </p>
                  <p className="leading-snug text-muted-foreground">“{semPrefixo(n.texto)}”</p>
                  {n.status === "falhou" && n.detalhe && <p className="text-xs text-destructive">Motivo da falha: {n.detalhe}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <DialogoConfirmacao
        aberto={confirmando}
        titulo={`Enviar ${plural(pendentes, "aviso", "avisos")}?`}
        descricao={
          <>
            Cada aviso chega como uma mensagem separada em <b>{dados?.destino ?? "o destino configurado"}</b>.
          </>
        }
        rotuloConfirmar="Enviar"
        aoConfirmar={() => void enviar()}
        aoCancelar={() => setConfirmando(false)}
        ocupado={enviando}
      />
    </div>
  )
}
