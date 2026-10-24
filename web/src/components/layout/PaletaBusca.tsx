import { useMemo, useState } from "react"
import { PACIENTES } from "@/data/fila"
import { ClasseBadge } from "@/components/shared/Basicos"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandDialog } from "@/components/ui/command"
import { normalizar } from "@/lib/filtros"
import { useStore } from "@/store/useStore"

const criarIndice = () => PACIENTES.map((p) => ({ p, alvo: normalizar([p.id, p.iniciais, p.cid, p.cid_descricao, p.procedimento, p.municipio, p.especialidade].join(" ")) }))

export function PaletaBusca() {
  const aberta = useStore((s) => s.paletaAberta)
  const setPaleta = useStore((s) => s.setPaleta)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const [consulta, setConsulta] = useState("")
  const versao = useStore((s) => s.versaoDados)
  const INDICE = useMemo(criarIndice, [versao])

  const resultados = useMemo(() => {
    const termos = normalizar(consulta.trim()).split(/\s+/).filter(Boolean)
    const lista = termos.length === 0 ? INDICE : INDICE.filter((i) => termos.every((t) => i.alvo.includes(t)))
    return lista.slice(0, 12).map((i) => i.p)
  }, [consulta, INDICE])

  return (
    <CommandDialog open={aberta} onOpenChange={setPaleta} title="Abrir paciente" description="Busque por ID, CID, procedimento, município ou iniciais" showCloseButton={false}>
      <Command shouldFilter={false} className="max-w-full">
        <CommandInput value={consulta} onValueChange={setConsulta} placeholder="ID, CID, procedimento, município..." />
        <CommandList className="max-h-[60svh]">
          <CommandEmpty>Nenhum paciente encontrado.</CommandEmpty>
          <CommandGroup heading={`${resultados.length} resultado${resultados.length === 1 ? "" : "s"}`}>
            {resultados.map((p) => (
              <CommandItem
                key={p.id}
                value={p.id}
                onSelect={() => {
                  abrirNaFila(p.id)
                  setPaleta(false)
                  setConsulta("")
                }}
                className="min-h-10 gap-2 sm:gap-3"
              >
                <ClasseBadge classe={p.classe} />
                <span className="w-24 shrink-0 truncate font-semibold tabular-nums sm:w-32">{p.id}</span>
                <span className="min-w-0 flex-1 truncate text-muted-foreground">{p.procedimento}</span>
                <span className="text-xs tabular-nums text-muted-foreground">#{p.posicao}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
