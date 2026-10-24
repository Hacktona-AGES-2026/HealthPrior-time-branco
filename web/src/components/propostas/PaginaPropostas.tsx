import { useState } from "react"
import { AlertTriangle, ArrowRight, Check, FileCheck2, Loader2, RefreshCw, ShieldCheck, Undo2, X } from "lucide-react"
import { toast } from "sonner"
import { decidirProposta, reverterRegra, type Proposta, type StatusProposta } from "@/api/cliente"
import { mensagemDeErro, plural } from "@/lib/mensagens"
import { formatarData } from "@/lib/datas"
import { usuarioAtual } from "@/lib/usuario"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { usePropostas } from "./usePropostas"

const ABAS: Record<StatusProposta, string> = {
  pendente: "Para decidir",
  aprovada: "Aprovadas",
  rejeitada: "Rejeitadas",
  revertida: "Revertidas",
  descartada: "Descartadas",
}
const ROTULO_MOTIVO = (m: string) => m.replaceAll("_", " ")

export default function PaginaPropostas() {
  const [status, setStatus] = useState<StatusProposta>("pendente")
  const { estado, recarregar } = usePropostas(status)
  const itens = estado.tipo === "ok" ? estado.dados.itens : []

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-5xl space-y-4 p-4">
        <header className="fx-fade-up space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <FileCheck2 className="size-4" aria-hidden /> Propostas de regra
          </h2>
          <p className="text-sm text-muted-foreground">
            Padrões que os reguladores repetiram. Veja o <b className="text-foreground">impacto simulado</b> na fila e aprove ou rejeite. Aprovar não muda ninguém sozinho: os afetados vão ao Inbox para decisão humana.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Status das propostas">
          {(Object.keys(ABAS) as StatusProposta[]).map((s) => (
            <Button key={s} className="h-9 lg:h-7" role="tab" aria-selected={status === s} size="sm" variant={status === s ? "default" : "outline"} onClick={() => setStatus(s)}>
              {ABAS[s]}
            </Button>
          ))}
          <div className="ml-auto flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
            {estado.tipo === "ok" && (
              <span>
                <b className="text-foreground tabular-nums">{estado.dados.total}</b> {estado.dados.total === 1 ? "proposta" : "propostas"}
              </span>
            )}
            <Button variant="outline" size="sm" className="h-9 lg:h-7" onClick={recarregar} aria-label="Atualizar a lista">
              <RefreshCw className={cn(estado.tipo === "ok" && estado.atualizando && "animate-spin")} aria-hidden /> Atualizar
            </Button>
          </div>
        </div>

        {estado.tipo === "carregando" && (
          <div className="space-y-3" role="status" aria-live="polite">
            <span className="fx-loading-dots text-sm text-muted-foreground">Carregando propostas</span>
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-40 w-full rounded-xl" />
            ))}
          </div>
        )}
        {estado.tipo === "erro" && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm" role="alert">
            <p className="flex items-center gap-2 font-semibold text-destructive">
              <AlertTriangle className="size-4" aria-hidden /> Não foi possível carregar as propostas
            </p>
            <p className="mt-1 text-muted-foreground">{estado.mensagem}</p>
            {!estado.mensagem.includes("equipe técnica") && <p className="mt-2 text-muted-foreground">Se o problema continuar, avise a equipe técnica.</p>}
            <Button variant="outline" size="sm" className="mt-3" onClick={recarregar}>
              <RefreshCw aria-hidden /> Tentar de novo
            </Button>
          </div>
        )}
        {estado.tipo === "ok" && itens.length === 0 && (
          <div className="rounded-xl bg-muted/40 p-8 text-center text-sm text-muted-foreground">
            {status === "pendente" ? "Nenhuma proposta para decidir. Rode “gerar propostas” para agrupar as decisões novas." : "Nada nesta aba."}
          </div>
        )}
        {estado.tipo === "ok" && itens.length > 0 && (
          <ul className={cn("space-y-3 transition-opacity", estado.atualizando && "opacity-60")} aria-label="Propostas de regra">
            {itens.map((p) => (
              <CartaoProposta key={p.proposta_id} proposta={p} aoDecidir={recarregar} />
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function CartaoProposta({ proposta: p, aoDecidir }: { proposta: Proposta; aoDecidir: () => void }) {
  const [rejeitando, setRejeitando] = useState(false)
  const [observacao, setObservacao] = useState("")
  const [enviando, setEnviando] = useState(false)
  const [revertendo, setRevertendo] = useState(false)
  const [motivoReversao, setMotivoReversao] = useState("")
  const i = p.impacto

  async function reverter() {
    setEnviando(true)
    try {
      const r = await reverterRegra(p.proposta_id, { usuario_id: usuarioAtual(), motivo: motivoReversao.trim() })
      toast.success("Regra revertida", {
        description: `${plural(r.devolvidos_ao_inbox, "paciente saiu", "pacientes saíram")} do Inbox: a sugestão voltou à classe anterior.`,
      })
      setRevertendo(false)
    } catch (e) {
      toast.error("Não foi possível reverter a regra", { description: mensagemDeErro(e) })
    } finally {
      setEnviando(false)
      aoDecidir() // também no erro: um 409 significa que já foi revertida
    }
  }

  async function decidir(decisao: "aprovar" | "rejeitar") {
    setEnviando(true)
    try {
      const r = await decidirProposta(p.proposta_id, { decisao, usuario_id: usuarioAtual(), observacao: observacao.trim() || undefined })
      if (r.status === "aprovada") {
        toast.success(`Regra aprovada (versão ${r.versao})`, {
          description: `${plural(r.enviados_ao_inbox, "paciente foi", "pacientes foram")} ao Inbox para decisão do regulador.`,
        })
      } else {
        toast.info("Proposta rejeitada", { description: "O motivo ficou registrado." })
      }
      setRejeitando(false)
    } catch (e) {
      toast.error("Não foi possível decidir a proposta", { description: mensagemDeErro(e) })
    } finally {
      setEnviando(false)
      aoDecidir() // também no erro: um 409 significa que alguém já decidiu
    }
  }

  return (
    <li className="rounded-xl border bg-card p-3 sm:p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="min-w-0 text-sm font-semibold">{p.procedimento ?? p.procedimento_id}</span>
        <Badge variant="outline">{ROTULO_MOTIVO(p.motivo)}</Badge>
        <span className="flex items-center gap-1.5 text-sm">
          <Badge variant="secondary">{p.classe_de}</Badge>
          <ArrowRight className="size-4 text-muted-foreground" aria-hidden />
          <Badge>{p.classe_para}</Badge>
          <span className="text-xs text-muted-foreground">({p.direcao === "subir" ? "sobe" : "rebaixa"})</span>
        </span>
        <span className="ml-auto hidden font-mono text-xs text-muted-foreground md:inline">{p.proposta_id}</span>
      </div>

      <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <div><dt className="inline text-muted-foreground">Casos </dt><dd className="inline tabular-nums">{p.n_casos}</dd></div>
        <div><dt className="inline text-muted-foreground">Reguladores </dt><dd className="inline tabular-nums">{p.n_reguladores}</dd></div>
        <div><dt className="inline text-muted-foreground">Consistência </dt><dd className="inline tabular-nums">{Math.round(p.consistencia * 100)}%</dd></div>
      </dl>

      {p.status === "descartada" && (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-destructive/5 p-2.5 text-sm text-destructive" role="note">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden /> {p.motivo_descarte}
        </p>
      )}

      {i && (
        <div className="mt-3 rounded-lg bg-muted/50 p-3 text-sm">
          <h4 className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">Impacto simulado (nada foi aplicado)</h4>
          <p>
            <b className="tabular-nums">{i.afetados}</b> {i.afetados === 1 ? "paciente mudaria" : "pacientes mudariam"} de {p.classe_de} para {p.classe_para}.{" "}
            <span className={cn(i.oncologicos_rebaixados > 0 && "font-semibold text-destructive")}>
              Oncológicos afetados: <b className="tabular-nums">{i.oncologicos_afetados}</b>; rebaixados: <b className="tabular-nums">{i.oncologicos_rebaixados}</b>.
            </span>
          </p>
          {i.exemplos.length > 0 && <p className="mt-1 text-xs text-muted-foreground">Ex.: <span className="font-mono">{i.exemplos.join(", ")}</span></p>}
        </div>
      )}

      {p.casos_origem.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="flex min-h-9 cursor-pointer items-center font-medium">Casos de origem ({p.casos_origem.length})</summary>
          <ul className="mt-2 grid gap-2 @lg:grid-cols-2">
            {p.casos_origem.map((c) => (
              <li key={c.decisao_id} className="rounded-lg bg-muted/50 p-2.5">
                <div className="mb-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                  <span className="font-mono text-foreground">{c.solicitacao_id}</span>
                  <span>{c.regulador_id}</span>
                  <span>{c.acao}</span>
                  <span>{c.classe_de} → {c.classe_para}</span>
                  <span>{formatarData(c.data.slice(0, 10))}</span>
                </div>
                <p className="leading-snug">{c.justificativa || "Sem justificativa em texto."}</p>
              </li>
            ))}
          </ul>
        </details>
      )}

      {p.status === "pendente" && (
        <div className="mt-3 border-t pt-3">
          {rejeitando ? (
            <div className="space-y-2">
              <Textarea value={observacao} onChange={(e) => setObservacao(e.target.value)} placeholder="Motivo da rejeição (obrigatório)" aria-label="Motivo da rejeição" />
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" className="h-9 lg:h-7" variant="destructive" disabled={enviando || observacao.trim() === ""} onClick={() => decidir("rejeitar")}>
                  {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <X aria-hidden />} Rejeitar: confirmar
                </Button>
                <Button size="sm" className="h-9 lg:h-7" variant="ghost" onClick={() => { setRejeitando(false); setObservacao("") }}>Cancelar</Button>
                <span className="ml-auto text-xs text-muted-foreground">por {usuarioAtual()}</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" className="h-9 lg:h-7" disabled={enviando} onClick={() => decidir("aprovar")}>
                {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <Check aria-hidden />} Aprovar regra
              </Button>
              <Button size="sm" className="h-9 lg:h-7" variant="outline" disabled={enviando} onClick={() => setRejeitando(true)}>
                <X aria-hidden /> Rejeitar
              </Button>
              <span className="ml-auto text-xs text-muted-foreground">por {usuarioAtual()}</span>
            </div>
          )}
        </div>
      )}

      {(p.status === "aprovada" || p.status === "rejeitada" || p.status === "revertida") && (
        <div className="mt-3 border-t pt-3 text-sm">
          <p>
            <b>{p.status === "rejeitada" ? "Rejeitada" : `Aprovada (versão ${p.versao ?? "?"})`}</b>
            {p.decidida_por && <> por <span className="font-mono">{p.decidida_por}</span></>}
            {p.decidida_em && <> em {formatarData(p.decidida_em.slice(0, 10))}</>}
          </p>
          {p.observacao && <p className="mt-1 text-muted-foreground">{p.observacao}</p>}
          {p.status === "revertida" && (
            <p className="mt-2">
              <b className="text-destructive">Revertida</b>
              {p.revertida_por && <> por <span className="font-mono">{p.revertida_por}</span></>}
              {p.revertida_em && <> em {formatarData(p.revertida_em.slice(0, 10))}</>}
              {p.motivo_reversao && <span className="text-muted-foreground">: {p.motivo_reversao}</span>}
            </p>
          )}
          {p.status === "aprovada" &&
            (revertendo ? (
              <div className="mt-3 space-y-2">
                <Textarea value={motivoReversao} onChange={(e) => setMotivoReversao(e.target.value)} placeholder="Motivo da reversão (obrigatório)" aria-label="Motivo da reversão" />
                <div className="flex flex-wrap items-center gap-2">
                  <Button size="sm" className="h-9 lg:h-7" variant="destructive" disabled={enviando || motivoReversao.trim() === ""} onClick={reverter}>
                    {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <Undo2 aria-hidden />} Reverter: confirmar
                  </Button>
                  <Button size="sm" className="h-9 lg:h-7" variant="ghost" onClick={() => { setRevertendo(false); setMotivoReversao("") }}>Cancelar</Button>
                  <span className="ml-auto text-xs text-muted-foreground">por {usuarioAtual()}</span>
                </div>
                <p className="text-xs text-muted-foreground">A regra deixa de valer. Quem ela mandou ao Inbox e ninguém decidiu sai de lá; quem o regulador já decidiu não muda.</p>
              </div>
            ) : (
              <Button size="sm" className="mt-3 h-9 lg:h-7" variant="outline" onClick={() => setRevertendo(true)}>
                <Undo2 aria-hidden /> Reverter regra
              </Button>
            ))}
        </div>
      )}
    </li>
  )
}
