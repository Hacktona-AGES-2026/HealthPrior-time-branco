import { useEffect, useRef, useState } from "react"
import { Check, Undo2, X } from "lucide-react"
import { daApi } from "@/data/adaptador"
import type { Paciente } from "@/data/tipos"
import { CLASSES, DESCRICAO_CLASSE } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { ClasseBadge } from "@/components/shared/Basicos"
import { MOTIVOS_CODIFICADOS, type MotivoCodificado } from "@/lib/api"
import { useStore } from "@/store/useStore"
import type { Classe } from "@/data/tipos"

const ITENS: Record<string, string> = Object.fromEntries(CLASSES.map((c) => [c, `${c} · ${DESCRICAO_CLASSE[c]}`]))

export function AcoesDecisao({ paciente }: { paciente: Paciente }) {
  const id = paciente.solicitacao_id
  const decisao = useStore((s) => s.decisoes[id])
  const rejeitando = useStore((s) => s.rejeitando)
  const setRejeitando = useStore((s) => s.setRejeitando)
  const aprovar = useStore((s) => s.aprovar)
  const rejeitar = useStore((s) => s.rejeitar)
  const desfazer = useStore((s) => s.desfazer)
  const enviando = useStore((s) => s.enviando)
  const [motivoCodificado, setMotivoCodificado] = useState<MotivoCodificado>("outro")
  const [classe, setClasse] = useState<Classe>(paciente.classe_antiga)
  const [motivo, setMotivo] = useState("")
  const campo = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setClasse(paciente.classe_antiga)
    setMotivo("")
  }, [id, paciente.classe_antiga])

  useEffect(() => {
    if (rejeitando) setTimeout(() => campo.current?.focus(), 60)
  }, [rejeitando])

  if (decisao) {
    const ok = decisao.status === "aprovado"
    return (
      <div className="fx-pop space-y-2 rounded-xl p-3 text-sm" style={{ background: `color-mix(in oklab, ${ok ? "var(--sobe)" : "var(--desce)"} 10%, transparent)` }}>
        <div className="flex items-center gap-2 font-semibold">
          {ok ? <Check className="size-4" style={{ color: "var(--sobe)" }} aria-hidden /> : <X className="size-4" style={{ color: "var(--desce)" }} aria-hidden />}
          {ok ? "Aprovado" : "Rejeitado"}
          <span className="ml-auto flex items-center gap-1 text-xs font-normal text-muted-foreground">
            classe final <ClasseBadge classe={decisao.classeFinal} />
          </span>
        </div>
        {decisao.motivo && <p className="text-xs text-muted-foreground">Motivo: {decisao.motivo}</p>}
        {/* Na API a decisão fica no log e não se desfaz; para mudar, nova decisão com justificativa. */}
        {!daApi(paciente) && (
          <Button size="sm" variant="outline" className="w-full gap-1" onClick={() => desfazer(id)}>
            <Undo2 aria-hidden /> Desfazer decisão
          </Button>
        )}
      </div>
    )
  }

  // API: só se aprova o que está no inbox (D-98)
  const semProposta = daApi(paciente) && !paciente.divergencia

  if (rejeitando) {
    const valido = motivo.trim().length >= 3
    return (
      <form
        className="fx-expand space-y-2 rounded-xl bg-muted/40 p-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (valido) rejeitar(id, classe, motivo.trim(), motivoCodificado)
        }}
      >
        <div className="text-xs font-semibold">Rejeitar proposta da IA</div>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Classe final
          <Select items={ITENS} value={classe} onValueChange={(v) => setClasse((v ?? paciente.classe_antiga) as Classe)}>
            <SelectTrigger size="sm" className="w-full text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ITENS).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Motivo codificado
          <Select items={MOTIVOS_CODIFICADOS} value={motivoCodificado} onValueChange={(v) => setMotivoCodificado((v ?? "outro") as MotivoCodificado)}>
            <SelectTrigger size="sm" className="w-full text-foreground" aria-label="Motivo codificado">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(MOTIVOS_CODIFICADOS).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Justificativa (obrigatória)
          <Textarea ref={campo} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Descreva por que a classe proposta não se aplica" rows={3} className="text-foreground" aria-required />
        </label>
        <div className="flex gap-2">
          <Button type="button" size="sm" variant="outline" className="flex-1" onClick={() => setRejeitando(false)}>
            Cancelar
          </Button>
          <Button type="submit" size="sm" disabled={!valido || enviando} className="flex-1 bg-[var(--desce)]/20 text-foreground hover:bg-[var(--desce)]/30" variant="ghost">
            <X aria-hidden /> Confirmar
          </Button>
        </div>
      </form>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      <Button variant="ghost" disabled={enviando || semProposta} title={semProposta ? "Sem proposta no inbox: a classe sugerida já é a classe em vigor" : undefined} className="gap-1.5 bg-[var(--sobe)]/15 text-foreground hover:bg-[var(--sobe)]/25" onClick={() => aprovar(id)}>
        <Check className="text-[var(--sobe)]" aria-hidden /> Aprovar <kbd className="rounded bg-background/60 px-1 text-[10px] text-muted-foreground">A</kbd>
      </Button>
      <Button variant="ghost" disabled={enviando} className="gap-1.5 bg-[var(--desce)]/15 text-foreground hover:bg-[var(--desce)]/25" onClick={() => setRejeitando(true)}>
        <X className="text-[var(--desce)]" aria-hidden /> Rejeitar <kbd className="rounded bg-background/60 px-1 text-[10px] text-muted-foreground">R</kbd>
      </Button>
    </div>
  )
}
