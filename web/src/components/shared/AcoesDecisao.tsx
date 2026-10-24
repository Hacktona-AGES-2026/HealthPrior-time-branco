import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react"
import { Check, Pencil, Undo2 } from "lucide-react"
import { ORIGEM_DADOS } from "@/data/fila"
import type { Classe, Paciente } from "@/data/tipos"
import { CLASSES, PRAZO_MAX } from "@/lib/cores"
import { ROTULO_MOTIVO, type MotivoCodificado } from "@/lib/filtros"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { ClasseBadge } from "@/components/shared/Basicos"
import { PreviaDecisao, usePrevia } from "@/components/shared/PreviaDecisao"
import { useStore } from "@/store/useStore"

const ITENS_MOTIVO: Record<string, string> = ROTULO_MOTIVO

export function AcoesDecisao({ paciente, variante = "painel" }: { paciente: Paciente; variante?: "painel" | "barra" }) {
  const barra = variante === "barra"
  const idBase = useId()
  const opcoes = useRef<(HTMLButtonElement | null)[]>([])
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

  const semProposta = ORIGEM_DADOS === "api" && !paciente.inbox
  // Prévia do Editar: posição e prazo que a classe escolhida daria, antes de salvar.
  const previaEdicao = usePrevia(id, "editar", classe, ORIGEM_DADOS === "api" && editando)

  if (decisao) {
    const ok = decisao.status === "aprovado"
    if (barra) {
      return (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
          {ok ? <Check className="size-4" style={{ color: "var(--sobe)" }} aria-hidden /> : <Pencil className="size-4" style={{ color: "var(--cls-c)" }} aria-hidden />}
          <span className="font-semibold">{ok ? "Classe aprovada" : "Classe editada"}</span>
          <ClasseBadge classe={decisao.classeFinal} />
          {decisao.motivoCodificado && <span className="text-xs text-muted-foreground">{ROTULO_MOTIVO[decisao.motivoCodificado]}</span>}
          {ORIGEM_DADOS !== "api" && (
            <Button size="sm" variant="outline" className="h-9 gap-1" onClick={() => desfazer(id)}>
              <Undo2 aria-hidden /> Desfazer
            </Button>
          )}
        </div>
      )
    }
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

  const valido = texto.trim().length >= 3
  const igual = classe === paciente.classe
  const podeSalvar = valido && !enviando && !igual

  function moverClasse(e: ReactKeyboardEvent, i: number) {
    let j = i
    if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i + 1) % CLASSES.length
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") j = (i - 1 + CLASSES.length) % CLASSES.length
    else return
    e.preventDefault()
    setClasse(CLASSES[j])
    opcoes.current[j]?.focus()
  }

  const dialogo = (
    <Dialog open={editando} onOpenChange={(v) => !v && setEditando(false)}>
      <DialogContent showCloseButton={false} initialFocus={() => opcoes.current[Math.max(0, CLASSES.indexOf(classe))] ?? campo.current} className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (podeSalvar) editar(id, classe, motivoCodigo, texto.trim())
          }}
        >
          <DialogHeader>
            <DialogTitle className="text-base">Alterar classe</DialogTitle>
            <DialogDescription>
              {paciente.iniciais} · {paciente.procedimento}
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 text-sm">
            Sugerida pelo sistema: <ClasseBadge classe={paciente.classe} />
          </div>
          <div className="space-y-1.5">
            <div id={`${idBase}-classe`} className="text-xs font-medium text-muted-foreground">
              Nova classe
            </div>
            <div role="radiogroup" aria-labelledby={`${idBase}-classe`} className="grid grid-cols-5 gap-1.5 sm:gap-2">
              {CLASSES.map((c, i) => {
                const sel = c === classe
                return (
                  <button
                    key={c}
                    ref={(el) => {
                      opcoes.current[i] = el
                    }}
                    type="button"
                    role="radio"
                    aria-checked={sel}
                    tabIndex={sel ? 0 : -1}
                    onClick={() => setClasse(c)}
                    onKeyDown={(e) => moverClasse(e, i)}
                    className={`flex min-h-12 flex-col items-center justify-center rounded-lg border px-0.5 py-1.5 outline-none focus-visible:ring-2 focus-visible:ring-ring ${sel ? "border-primary bg-primary/15" : "border-border hover:bg-muted"}`}
                  >
                    <span className="text-base font-semibold">{c}</span>
                    <span className="text-xs text-muted-foreground"><span className="sm:hidden">{PRAZO_MAX[c]} d</span><span className="hidden sm:inline">até {PRAZO_MAX[c]} dias</span></span>
                  </button>
                )
              })}
            </div>
            {igual && <p className="text-xs text-muted-foreground">Escolha uma classe diferente da sugerida</p>}
          </div>
          <label className="block space-y-1.5 text-xs font-medium text-muted-foreground">
            Motivo
            <Select items={ITENS_MOTIVO} value={motivoCodigo} onValueChange={(v) => setMotivoCodigo((v ?? "outro") as MotivoCodificado)}>
              <SelectTrigger className="h-10 w-full sm:h-9 text-sm font-normal text-foreground">
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
          <label className="block space-y-1.5 text-xs font-medium text-muted-foreground">
            Justificativa
            <Textarea ref={campo} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Explique a mudança" rows={3} className="text-sm font-normal text-foreground" aria-required />
          </label>
          {previaEdicao?.previa && <PreviaDecisao previa={previaEdicao.previa} rotulo={`Se salvar ${classe}`} />}
          {previaEdicao?.erro && <p className="text-xs text-[var(--desce)]">{previaEdicao.erro}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" className="h-10 sm:h-9" onClick={() => setEditando(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!podeSalvar} className="h-10 sm:h-9">
              Salvar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )

  return (
    <>
      <div className={barra ? "inline-flex gap-2" : "grid grid-cols-2 gap-2"}>
        <Button variant="ghost" disabled={enviando || semProposta} title={semProposta ? "Sem proposta pendente" : "Aprovar"} className="h-9 gap-1.5 bg-[var(--sobe)]/15 text-foreground hover:bg-[var(--sobe)]/25" onClick={() => aprovar(id)}>
          <Check className="text-[var(--sobe)]" aria-hidden /> Aprovar
        </Button>
        <Button variant="ghost" disabled={enviando} title="Editar" className="h-9 gap-1.5 bg-muted text-foreground hover:bg-muted/70" onClick={() => setEditando(true)}>
          <Pencil aria-hidden /> Editar
        </Button>
      </div>
      {dialogo}
    </>
  )
}
