import { useMemo, useRef, useState } from "react"
import { ChevronLeft, ChevronRight, ExternalLink, Printer } from "lucide-react"
import { PACIENTES, PACIENTE_POR_ID } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { AcoesDecisao } from "@/components/shared/AcoesDecisao"
import { ClasseBadge, SetaVariacao, StatusAprovacao } from "@/components/shared/Basicos"
import { PacienteDetalhe } from "@/components/shared/PacienteDetalhe"
import { normalizar } from "@/lib/filtros"
import { useStore } from "@/store/useStore"
import { FichaSus } from "./FichaSus"

const criarIndiceBusca = () => PACIENTES.map((p) => ({
  p,
  alvo: normalizar([p.id, p.iniciais, p.cid, p.cid_norm, p.cid_descricao, p.procedimento, p.municipio, p.especialidade, ...p.motivos, ...p.alertas].join(" ")),
}))

export default function PaginaPacientes() {
  const indiceBusca = useMemo(criarIndiceBusca, [])
  const selecionadoId = useStore((s) => s.selecionadoId)
  const decisoes = useStore((s) => s.decisoes)
  const selecionar = useStore((s) => s.selecionar)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const [consulta, setConsulta] = useState("")
  const [aberta, setAberta] = useState(false)
  const caixa = useRef<HTMLDivElement>(null)
  const paciente = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined

  const resultados = useMemo(() => {
    const termos = normalizar(consulta.trim()).split(/\s+/).filter(Boolean)
    const lista = termos.length === 0 ? indiceBusca : indiceBusca.filter((i) => termos.every((t) => i.alvo.includes(t)))
    return lista.slice(0, 14).map((i) => i.p)
  }, [consulta])

  const moverNaFicha = (direcao: 1 | -1) => {
    const alvo = PACIENTES.find((x) => x.posicao === (paciente?.posicao ?? 0) + direcao)
    if (alvo) selecionar(alvo.id, false)
  }

  const escolher = (p: Paciente) => {
    selecionar(p.id, false)
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
              placeholder="Buscar paciente"
              className="h-10 text-base"
              aria-label="Buscar paciente"
            />
            {aberta && (
              <CommandList className="max-h-80 border-t">
                <CommandEmpty>Nenhum paciente encontrado.</CommandEmpty>
                <CommandGroup>
                  {resultados.map((p) => (
                    <CommandItem key={p.id} value={p.id} onSelect={() => escolher(p)} className="gap-3 py-2">
                      <ClasseBadge classe={p.classe} />
                      <span className="shrink-0 font-semibold tabular-nums sm:w-28">{p.id}</span>
                      <span className="min-w-0 flex-1 truncate">
                        <span className="text-muted-foreground">{p.iniciais} · </span>
                        {p.procedimento}
                      </span>
                      <span className="hidden text-xs text-muted-foreground tabular-nums sm:inline">
                        #{p.posicao_atual} → #{p.posicao}
                      </span>
                      <SetaVariacao antiga={p.posicao_atual} nova={p.posicao} animada={false} />
                      <StatusAprovacao decisao={decisoes[p.id]} />
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            )}
          </Command>
        </div>

        {paciente && (
          <div key={paciente.id} className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 border-b pb-3">
              <div className="min-w-0 flex-1">
                <div className="text-lg font-bold tabular-nums">{paciente.id}</div>
                <div className="break-words text-sm text-muted-foreground">
                  {paciente.iniciais} · {paciente.idade} anos · {paciente.procedimento}
                </div>
              </div>
              <div className="no-print flex flex-wrap items-center gap-2">
                <Button variant="outline" size="icon-sm" className="size-9 sm:size-8" onClick={() => moverNaFicha(-1)} disabled={paciente.posicao <= 1} aria-label="Paciente anterior na fila" title="Anterior">
                  <ChevronLeft aria-hidden />
                </Button>
                <Button variant="outline" size="icon-sm" className="size-9 sm:size-8" onClick={() => moverNaFicha(1)} aria-label="Próximo paciente na fila" title="Próximo">
                  <ChevronRight aria-hidden />
                </Button>
                <Button variant="outline" size="sm" className="h-9 gap-1.5 sm:h-8" onClick={() => abrirNaFila(paciente.id)}>
                  <ExternalLink aria-hidden /> Voltar à fila
                </Button>
                <Button variant="outline" size="sm" className="h-9 gap-1.5 sm:h-8" onClick={() => window.print()}>
                  <Printer aria-hidden /> Imprimir
                </Button>
              </div>
              <div className="no-print w-full max-w-sm">
                <AcoesDecisao paciente={paciente} />
              </div>
            </div>

            <FichaSus p={paciente} />
            <PacienteDetalhe paciente={paciente} />
          </div>
        )}
      </div>
    </div>
  )
}
