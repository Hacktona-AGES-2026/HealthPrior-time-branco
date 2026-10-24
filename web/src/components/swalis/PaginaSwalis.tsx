import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { META, PACIENTES } from "@/data/fila"
import { CLASSES, corClasse } from "@/lib/cores"
import { CRITERIOS_SWALIS, REGRAS_SWALIS } from "@/lib/regrasSwalis"
import { cn } from "@/lib/utils"
import { ClasseBadge } from "@/components/shared/Basicos"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useStore } from "@/store/useStore"

const TITULO = "text-base font-semibold"

export default function PaginaSwalis() {
  const destaque = useStore((s) => s.destaqueSwalis)
  const limpar = useStore((s) => s.limparDestaqueSwalis)

  const porClasse = useMemo(() => CLASSES.map((c) => ({ classe: c, total: PACIENTES.filter((p) => p.classe === c).length })), [])

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-6xl space-y-6 p-4">
        {destaque && (
          <div role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/40 bg-primary/10 p-3 text-sm">
            <span>
              Destacando a classe <b>{destaque.classe}</b> de <b>{destaque.iniciais}</b>
            </span>
            <Button variant="outline" className="min-h-9" onClick={limpar}>
              Limpar
            </Button>
          </div>
        )}

        <section className="overflow-hidden rounded-xl bg-muted/40" aria-labelledby="sw-classes">
          <h2 id="sw-classes" className={cn("px-4 pt-4 pb-2", TITULO)}>
            Classes
          </h2>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Classe</TableHead>
                  <TableHead className="w-24">Prazo</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead className="hidden md:table-cell">Exemplos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {META.swalis.map((c) => {
                  const atual = destaque?.classe === c.classe
                  return (
                    <TableRow key={c.classe} aria-current={atual ? "true" : undefined} className={cn(atual && "bg-primary/15")}>
                      <TableCell>
                        <ClasseBadge classe={c.classe} />
                      </TableCell>
                      <TableCell className="font-semibold tabular-nums">{c.prazo} dias</TableCell>
                      <TableCell className="whitespace-normal text-sm">{c.descricao}</TableCell>
                      <TableCell className="hidden whitespace-normal text-sm text-muted-foreground md:table-cell">{c.exemplos}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </section>

        <section className="space-y-2 rounded-xl bg-muted/40 p-4" aria-labelledby="sw-criterios">
          <h2 id="sw-criterios" className={TITULO}>
            Como a classe é definida
          </h2>
          <p className="max-w-prose text-sm text-muted-foreground">A classe sai do cruzamento de dois critérios. Quanto maior o nível, mais urgente.</p>
          <ul className="space-y-1 text-sm">
            {CRITERIOS_SWALIS.map((c) => (
              <li key={c.nome}>
                <b>{c.nome}:</b> {c.texto}
              </li>
            ))}
          </ul>
        </section>

        <div className="grid gap-4 @3xl:grid-cols-2">
          <section className="space-y-2 rounded-xl bg-muted/40 p-4" aria-labelledby="sw-regras">
            <h2 id="sw-regras" className={TITULO}>
              Regras do sistema
            </h2>
            <ul className="space-y-2">
              {REGRAS_SWALIS.map((r) => (
                <li key={r.id} className={cn("rounded-lg p-3 text-sm", r.ouro ? "bg-[color-mix(in_oklab,var(--ouro)_14%,transparent)]" : "bg-background/60")}>
                  <p className="font-semibold">{r.titulo}</p>
                  <p className="mt-0.5 max-w-prose text-muted-foreground">{r.texto}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-2 rounded-xl bg-muted/40 p-4" aria-labelledby="sw-grafico">
            <h2 id="sw-grafico" className={TITULO}>
              Na fila por classe
            </h2>
            <div className="h-48 sm:h-64" role="img" aria-label={`Solicitações na fila por classe: ${porClasse.map((d) => `${d.classe} ${d.total}`).join(", ")}`}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={porClasse} margin={{ top: 16, right: 8, bottom: 0, left: -6 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="classe" tick={{ fontSize: 12, fontWeight: 600, fill: "var(--foreground)" }} stroke="var(--border)" />
                  <YAxis tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                  <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
                  <Bar name="Na fila" dataKey="total" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    {porClasse.map((d) => (
                      <Cell key={d.classe} fill={corClasse(d.classe)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
