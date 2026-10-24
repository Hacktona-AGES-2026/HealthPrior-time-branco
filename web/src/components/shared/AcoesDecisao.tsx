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
import { PreviaDecisao, usePrevia } from "@/components/shared/PreviaDecisao"
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
  // Prévia do Editar: posição e prazo que a classe escolhida daria, antes de salvar.
  const previaEdicao = usePrevia(id, "editar", classe, ORIGEM_DADOS === "api" && editando)

  if (decisao) {
    const ok = decisao.status === "aprovado"
    return (
      <div className="space-y-2 text-sm">
        <div className="flex flex-wrap items-center gap-2 font-semibold">
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
          <Button size="sm" variant="outline" className="h-9 w-full gap-1 sm:h-8" onClick={() => desfazer(id)}>
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
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (valido) editar(id, classe, motivoCodigo, texto.trim())
        }}
      >
        <div className="text-xs font-semibold">Editar classe sugerida ({paciente.classe})</div>
        <label className="block space-y-1 text-xs text-muted-foreground">
          Classe final
          <Select items={ITENS_CLASSE} value={classe} onValueChange={(v) => setClasse((v ?? paciente.classe) as Classe)}>
            <SelectTrigger size="sm" className="h-9 w-full text-foreground sm:h-8">
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
            <SelectTrigger size="sm" className="h-9 w-full text-foreground sm:h-8">
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
          Justificativa
          <Textarea ref={campo} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Por que mudar a classe?" rows={3} className="text-foreground" aria-required />
        </label>
        {previaEdicao?.previa && <PreviaDecisao previa={previaEdicao.previa} rotulo={`Se salvar ${classe}`} />}
        {previaEdicao?.erro && <p className="text-xs text-[var(--desce)]">{previaEdicao.erro}</p>}
        <div className="flex gap-2">
          <Button type="button" size="sm" variant="outline" className="h-9 flex-1 sm:h-8" onClick={() => setEditando(false)}>
            Cancelar
          </Button>
          <Button type="submit" size="sm" disabled={!valido || enviando} variant="ghost" className="h-9 flex-1 bg-primary/15 sm:h-8 text-foreground hover:bg-primary/25">
            <Pencil aria-hidden /> Salvar
          </Button>
        </div>
      </form>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      <Button variant="ghost" disabled={enviando || semProposta} title={semProposta ? "Sem proposta pendente" : "Aprovar (A)"} className="gap-1.5 bg-[var(--sobe)]/15 text-foreground hover:bg-[var(--sobe)]/25" onClick={() => aprovar(id)}>
        <Check className="text-[var(--sobe)]" aria-hidden /> Aprovar
      </Button>
      <Button variant="ghost" disabled={enviando} title="Editar (R)" className="gap-1.5 bg-muted text-foreground hover:bg-muted/70" onClick={() => setEditando(true)}>
        <Pencil aria-hidden /> Editar
      </Button>
    </div>
  )
}
