import { useState } from "react"
import { Sparkles } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { corrigirCid, type PendenciaDetalheApi, pedirSugestaoCid, type SugestaoCidApi } from "@/lib/api"
import { reguladorAtual } from "@/lib/usuario"

/**
 * PRE-12 "câncer escondido" (D-125): laudo de biópsia positiva com CID não oncológico.
 * O LLM sugere o CID e cita o laudo; o regulador confere, ajusta se quiser e confirma (I-05).
 */
export function CorrigirCid({ pendencia, cidAtual, aoCorrigir }: { pendencia: PendenciaDetalheApi; cidAtual: string; aoCorrigir: () => void }) {
  const [sugestao, setSugestao] = useState<SugestaoCidApi | null>(pendencia.sugestao_cid ?? null)
  const [cid, setCid] = useState(pendencia.sugestao_cid?.cid ?? "")
  const [ocupado, setOcupado] = useState<"sugerir" | "corrigir" | null>(null)
  const laudos = (pendencia.evidencias ?? []).filter((e) => e.fonte === "evento")

  const sugerir = async () => {
    setOcupado("sugerir")
    try {
      const s = await pedirSugestaoCid(pendencia.pendencia_id)
      setSugestao(s)
      if (s) setCid(s.cid)
      else toast.info("Sem sugestão válida para este laudo", { description: "Digite o CID depois de conferir o laudo." })
    } catch (e) {
      toast.error("Não foi possível pedir a sugestão", { description: e instanceof Error ? e.message : undefined })
    } finally {
      setOcupado(null)
    }
  }

  const corrigir = async () => {
    setOcupado("corrigir")
    try {
      const r = await corrigirCid(pendencia.pendencia_id, cid.trim(), reguladorAtual())
      toast.success(`CID corrigido: ${cidAtual} → ${cid.trim().toUpperCase()}`, {
        description: r.fila_publicada ? "Fila recalculada e publicada." : "O verificador reprovou: a fila anterior continua publicada.",
      })
      aoCorrigir()
    } catch (e) {
      toast.error("Não foi possível corrigir o CID", { description: e instanceof Error ? e.message : undefined })
    } finally {
      setOcupado(null)
    }
  }

  return (
    <section aria-label="Conferir diagnóstico (CID)" className="space-y-2 rounded-md border border-dashed p-2 text-xs">
      <h4 className="text-sm font-semibold">Conferir diagnóstico (CID {cidAtual})</h4>
      {laudos.map((l) => (
        <p key={l.ref ?? l.texto} className="text-muted-foreground">
          Laudo{l.ref ? ` (${l.ref})` : ""}: <q>{l.texto}</q>
        </p>
      ))}
      {sugestao ? (
        <div className="flex gap-1.5">
          <Sparkles className="mt-0.5 size-3.5 shrink-0 text-[var(--sobe)]" aria-hidden />
          <div>
            <div>
              Sugestão: <span className="font-semibold tabular-nums">{sugestao.cid}</span> {sugestao.descricao}
            </div>
            <div className="text-muted-foreground">
              cita <q>{sugestao.citacao}</q> · {sugestao.modelo} · confiança {Math.round(sugestao.confianca * 100)}%
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-muted-foreground">
          Sem sugestão de CID ainda.
          <Button size="sm" variant="outline" onClick={sugerir} disabled={ocupado !== null}>
            {ocupado === "sugerir" ? "Pedindo…" : "Pedir sugestão"}
          </Button>
        </div>
      )}
      <div className="flex items-center gap-2">
        <Input value={cid} onChange={(e) => setCid(e.target.value)} placeholder="CID, ex.: C50.9" className="h-7 w-28 text-xs" aria-label="CID novo" />
        <Button size="sm" onClick={corrigir} disabled={ocupado !== null || !cid.trim()}>
          {ocupado === "corrigir" ? "Corrigindo…" : "Corrigir CID"}
        </Button>
        <span className="text-muted-foreground">confira o laudo: quem decide é o regulador</span>
      </div>
    </section>
  )
}
