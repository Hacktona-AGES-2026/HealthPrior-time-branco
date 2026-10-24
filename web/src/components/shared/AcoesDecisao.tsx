import { useEffect, useRef, useState } from "react"
import { Check, Pencil, Undo2 } from "lucide-react"
import { ORIGEM_DADOS } from "@/data/fila"
import type { Classe, Paciente } from "@/data/tipos"
import { CLASSES, DESCRICAO_CLASSE } from "@/lib/cores"
import { ROTULO_MOTIVO, type MotivoCodificado } from "@/lib/filtros"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { ClasseBadge } from "@/components/shared/Basicos"
import { useStore } from "@/store/useStore"

const ITENS_CLASSE: Record<string, string> = Object.fromEntries(CLASSES.map((c) => [c, `${c} · ${DESCRICAO_CLASSE[c].split(",")[0]}`]))
const ITENS_MOTIVO: Record<string, string> = ROTULO_MOTIVO

export function AcoesDecisao({ paciente }: { paciente: Paciente }) {
  const id = paciente.id
  const decisao = useStore((s) => s.decisoes[id])
  const editando = useStore((s) => s.rejeitando)
  const setEditando = useStore((s) => s.setRejeitando)
  const aprovar = useStore((s) => s.aprovar)
  const editar = useStore((s) => s.editar)
  const desfazer = useStore((s) => s.desfazer)
  const enviando = useStore((s) => s.enviando)
  const [classe, setClasse] = useState<Classe>(paciente.classe)
  const [motivoCodigo, setMotivoCodigo] = useState<MotivoCodificado>("outro")
  const [texto, setTexto] = useState("")
  const campo = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setClasse(paciente.classe)
    setMotivoCodigo("outro")
    setTexto("")
  }, [id, paciente.classe])

  useEffect(() => {
    if (editando) setTimeout(() => campo.current?.focus(), 60)
  }, [editando])

  const semProposta = ORIGEM_DADOS === "api" && !paciente.inbox

  if (decisao) {
    const ok = decisao.status === "aprovado"
    return (
      <div className="fx-pop space-y-2 rounded-xl bg-muted/50 p-3 text-sm">
        <div className="flex items-center gap-2 font-semibold">
          {ok ? <Check className="size-4" style={{ color: "var(--sobe)" }} aria-hidden /> : <Pencil className="size-4" style={{ color: "var(--cls-c)" }} aria-hidden />}
          {ok ? "Classe aprovada" : "Classe editada"}
          <span className="ml-auto flex items-center gap-1 text-xs font-normal text-muted-foreground">
            final <ClasseBadge classe={decisao.classeFinal} />
          </span>
        </div>
        {decisao.motivoCodificado && (
          <p className="text-xs text-muted-foreground">
            {ROTULO_MOTIVO[decisao.motivoCodificado]}
            {decisao.motivo ? `: ${decisao.motivo}` : ""}
          </p>
        )}
        {ORIGEM_DADOS !== "api" && (
          <Button size="sm" variant="outline" className="w-full gap-1" onClick={() => desfazer(id)}>
            <Undo2 aria-hidden /> Desfazer decisão
          </Button>
        )}
      </div>
    )
  }

  if (editando) {
    const valido = texto.trim().length >= 3
    return (
      <form
        className="fx-expand space-y-2 rounded-xl bg-muted/40 p-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (valido) editar(id, classe, motivoCodigo, texto.trim())
        }}
      >
        <div className="text-xs font-semibold">Editar classe sugerida ({paciente.classe})</div>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Classe final
          <Select items={ITENS_CLASSE} value={classe} onValueChange={(v) => setClasse((v ?? paciente.classe) as Classe)}>
            <SelectTrigger size="sm" className="w-full text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ITENS_CLASSE).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Motivo
          <Select items={ITENS_MOTIVO} value={motivoCodigo} onValueChange={(v) => setMotivoCodigo((v ?? "outro") as MotivoCodificado)}>
            <SelectTrigger size="sm" className="w-full text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ITENS_MOTIVO).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Justificativa (obrigatória)
          <Textarea ref={campo} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Explique por que a classe sugerida não se aplica" rows={3} className="text-foreground" aria-required />
        </label>
        {paciente.oncologico && <p className="text-[11px] text-muted-foreground">Oncológicos permanecem na camada 1, qualquer que seja a classe.</p>}
        <div className="flex gap-2">
          <Button type="button" size="sm" variant="outline" className="flex-1" onClick={() => setEditando(false)}>
            Cancelar
          </Button>
          <Button type="submit" size="sm" disabled={!valido || enviando} variant="ghost" className="flex-1 bg-primary/15 text-foreground hover:bg-primary/25">
            <Pencil aria-hidden /> Salvar
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
      <Button variant="ghost" disabled={enviando} className="gap-1.5 bg-muted text-foreground hover:bg-muted/70" onClick={() => setEditando(true)}>
        <Pencil aria-hidden /> Editar <kbd className="rounded bg-background/60 px-1 text-[10px] text-muted-foreground">R</kbd>
      </Button>
    </div>
  )
}
