import { useMemo, useRef, useState } from "react"
import { ExternalLink, Printer, UserSearch } from "lucide-react"
import { PACIENTES, PACIENTE_POR_ID } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { AcoesDecisao } from "@/components/shared/AcoesDecisao"
import { ClasseBadge, SetaVariacao, StatusAprovacao } from "@/components/shared/Basicos"
import { LinhaResumo } from "@/components/shared/LinhaResumo"
import { PacienteDetalhe } from "@/components/shared/PacienteDetalhe"
import { normalizar } from "@/lib/filtros"
import { AlcaColuna } from "@/components/shared/AlcaColuna"
import { COLUNAS, estiloColuna, useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"
import { FichaSus } from "./FichaSus"

const indiceBusca = PACIENTES.map((p) => ({
  p,
  alvo: normalizar([p.solicitacao_id, p.iniciais, p.cns_mascarado, p.cid, p.cid_descricao, p.procedimento, p.municipio, p.especialidade, ...p.sinais].join(" ")),
}))

export default function PaginaPacientes() {
  const selecionadoId = useStore((s) => s.selecionadoId)
  const decisoes = useStore((s) => s.decisoes)
  const selecionar = useStore((s) => s.selecionar)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const [consulta, setConsulta] = useState("")
  const [aberta, setAberta] = useState(false)
  const caixa = useRef<HTMLDivElement>(null)
  const larguras = useColunas((c) => c.larguras)
  const paciente = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined

  const resultados = useMemo(() => {
    const termos = normalizar(consulta.trim()).split(/\s+/).filter(Boolean)
    const lista = termos.length === 0 ? indiceBusca : indiceBusca.filter((i) => termos.every((t) => i.alvo.includes(t)))
    return lista.slice(0, 14).map((i) => i.p)
  }, [consulta])

  const escolher = (p: Paciente) => {
    selecionar(p.solicitacao_id, false)
    setConsulta("")
    setAberta(false)
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-6xl space-y-4 p-4">
        <div ref={caixa} className="no-print relative" onBlur={(e) => !caixa.current?.contains(e.relatedTarget as Node) && setAberta(false)}>
          <Command shouldFilter={false} className="h-auto rounded-xl border border-border/60 bg-card">
            <CommandInput
              value={consulta}
              onValueChange={(v) => {
                setConsulta(v)
                setAberta(true)
              }}
              onFocus={() => setAberta(true)}
              placeholder="Buscar por ID, iniciais, CNS, CID, procedimento, município, especialidade ou sinal"
              className="h-10 text-base"
              aria-label="Buscar paciente"
            />
            {aberta && (
              <CommandList className="max-h-80 border-t">
                <CommandEmpty>Nenhum paciente encontrado.</CommandEmpty>
                <CommandGroup heading={`${resultados.length} resultado${resultados.length === 1 ? "" : "s"}`}>
                  {resultados.map((p, i) => (
                    <CommandItem key={p.solicitacao_id} value={p.solicitacao_id} onSelect={() => escolher(p)} className="fx-fade-up gap-3 py-2" style={{ animationDelay: `${i * 25}ms` }}>
                      <ClasseBadge classe={p.classe} />
                      <span className="w-32 shrink-0 font-semibold tabular-nums">{p.solicitacao_id}</span>
                      <span className="min-w-0 flex-1 truncate">
                        <span className="text-muted-foreground">{p.iniciais} · </span>
                        {p.procedimento}
                      </span>
                      <span className="hidden text-xs text-muted-foreground tabular-nums sm:inline">
                        #{p.posicao_antiga} → #{p.posicao_nova}
                      </span>
                      <SetaVariacao antiga={p.posicao_antiga} nova={p.posicao_nova} animada={false} />
                      <StatusAprovacao decisao={decisoes[p.solicitacao_id]} />
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            )}
          </Command>
        </div>

        {!paciente ? (
          <div className="fx-fade-up flex flex-col items-center gap-3 rounded-xl border border-dashed py-20 text-center text-sm text-muted-foreground">
            <UserSearch className="size-10" aria-hidden />
            <p className="text-base font-medium text-foreground">Busque um paciente para ver a ficha completa</p>
            <p>Tente “K43.0”, “hérnia”, “Canoas” ou “oncológico”.</p>
          </div>
        ) : (
          <div key={paciente.solicitacao_id} className="space-y-4">
            <div className="fx-fade-up flex flex-wrap items-center gap-3 rounded-xl bg-muted/40 p-3">
              <div className="min-w-0 flex-1">
                <div className="text-lg font-bold tabular-nums">{paciente.solicitacao_id}</div>
                <div className="truncate text-sm text-muted-foreground">
                  {paciente.iniciais} · {paciente.idade} anos · {paciente.procedimento}
                </div>
              </div>
              <div className="no-print flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm" className="gap-1.5" onClick={() => abrirNaFila(paciente.solicitacao_id)}>
                  <ExternalLink aria-hidden /> Abrir na fila
                </Button>
                <Button variant="outline" size="sm" className="gap-1.5" onClick={() => window.print()}>
                  <Printer aria-hidden /> Imprimir
                </Button>
              </div>
              <div className="no-print w-full max-w-sm">
                <AcoesDecisao paciente={paciente} />
              </div>
            </div>

            <section className="fx-fade-up @container overflow-hidden rounded-xl bg-muted/40" aria-label="Linha da tabela">
              <div className="flex items-center gap-2 border-b border-border/60 px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {COLUNAS.map((c) => (
                  <div key={c.id} className="relative" style={estiloColuna(c.id, larguras)}>
                    {c.rotulo}
                    {c.id !== "alerta" && <AlcaColuna id={c.id} />}
                  </div>
                ))}
              </div>
              <div className="relative flex h-11 items-center gap-2 overflow-hidden bg-primary/5 px-3 text-sm shadow-[inset_2px_0_0_var(--primary)]">
                <LinhaResumo paciente={paciente} decisao={decisoes[paciente.solicitacao_id]} selecionado />
              </div>
            </section>

            <FichaSus p={paciente} />
            <PacienteDetalhe paciente={paciente} />
          </div>
        )}
      </div>
    </div>
  )
}
