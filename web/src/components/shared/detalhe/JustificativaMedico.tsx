import { useMemo, useState } from "react"
import { FileText, Link2, Route } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type Trecho = { inicio: number; fim: number; indice: number }

const localizar = (texto: string, trechos: string[]) => {
  const achados: Trecho[] = []
  const minusculo = texto.toLowerCase()
  trechos.forEach((t, indice) => {
    const inicio = minusculo.indexOf(t.toLowerCase())
    if (inicio >= 0) achados.push({ inicio, fim: inicio + t.length, indice })
  })
  achados.sort((a, b) => a.inicio - b.inicio)
  return achados.filter((a, i) => i === 0 || a.inicio >= achados[i - 1].fim)
}

function TextoDestacado({ texto, trechos, ativo, aoAtivar }: { texto: string; trechos: string[]; ativo: number | null; aoAtivar: (i: number | null) => void }) {
  const partes = useMemo(() => {
    const achados = localizar(texto, trechos)
    const saida: { texto: string; indice?: number }[] = []
    let cursor = 0
    achados.forEach((a) => {
      if (a.inicio > cursor) saida.push({ texto: texto.slice(cursor, a.inicio) })
      saida.push({ texto: texto.slice(a.inicio, a.fim), indice: a.indice })
      cursor = a.fim
    })
    if (cursor < texto.length) saida.push({ texto: texto.slice(cursor) })
    return saida
  }, [texto, trechos])

  return (
    <>
      {partes.map((parte, i) =>
        parte.indice === undefined ? (
          <span key={i}>{parte.texto}</span>
        ) : (
          <mark
            key={i}
            className="mark-evidencia text-foreground"
            data-ativo={ativo === parte.indice}
            tabIndex={0}
            onMouseEnter={() => aoAtivar(parte.indice!)}
            onMouseLeave={() => aoAtivar(null)}
            onFocus={() => aoAtivar(parte.indice!)}
            onBlur={() => aoAtivar(null)}
          >
            {parte.texto}
            <sup className="ml-0.5 text-[9px] font-bold text-muted-foreground">{parte.indice + 1}</sup>
          </mark>
        )
      )}
    </>
  )
}

export function JustificativaMedico({ p }: { p: Paciente }) {
  const [ativo, setAtivo] = useState<number | null>(null)
  const trechos = p.sinais_texto.map((s) => s.trecho)

  return (
    <div className="grid gap-3 @container">
      <section className="fx-fade-up rounded-xl bg-muted/40 p-3" aria-label="Justificativa clínica do médico">
        <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <FileText className="size-3.5" aria-hidden /> Justificativa clínica do médico
        </h3>
        <p className="text-sm leading-relaxed">
          {p.justificativa_clinica ? <TextoDestacado texto={p.justificativa_clinica} trechos={trechos} ativo={ativo} aoAtivar={setAtivo} /> : <span className="text-muted-foreground">Sem justificativa registrada</span>}
        </p>
        {p.observacoes && (
          <p className="mt-2 border-t border-border/60 pt-2 text-xs leading-relaxed text-muted-foreground">
            <span className="font-semibold">Observações: </span>
            <TextoDestacado texto={p.observacoes} trechos={trechos} ativo={ativo} aoAtivar={setAtivo} />
          </p>
        )}
        {trechos.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-2">
            <span className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              <Link2 className="size-3" aria-hidden /> Sinais extraídos do texto
            </span>
            {trechos.map((t, i) => (
              <button
                key={t}
                type="button"
                onMouseEnter={() => setAtivo(i)}
                onMouseLeave={() => setAtivo(null)}
                onFocus={() => setAtivo(i)}
                onBlur={() => setAtivo(null)}
                className={cn("rounded-md px-1.5 py-0.5 text-[11px] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring", ativo === i ? "bg-[var(--destaque)]" : "bg-background/70")}
              >
                <span className="font-bold">{i + 1}</span> {t}<span className="ml-1 text-muted-foreground">{p.sinais_texto[i].origem === "llm" ? "· LLM, só alerta" : "· regra"}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="fx-fade-up rounded-xl bg-primary/5 p-3" style={{ animationDelay: "120ms" }} aria-label="Por que este paciente está aqui">
        <h3 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-primary">
          <Route className="size-3.5" aria-hidden /> Por que está nesta posição
        </h3>
        <p className="text-sm leading-relaxed">{p.justificativa}</p>
        {p.alertas.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {p.alertas.map((a, i) => (
              <Badge key={a} variant="secondary" className="fx-pop bg-[var(--prazo-limite)]/15 font-normal" style={{ animationDelay: `${200 + i * 60}ms` }}>
                {a}
              </Badge>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
