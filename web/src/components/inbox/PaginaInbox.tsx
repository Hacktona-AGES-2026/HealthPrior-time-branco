import { Inbox } from "lucide-react"
import { PACIENTES } from "@/data/fila"
import { ClasseBadge } from "@/components/shared/Basicos"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { CLASSES } from "@/lib/cores"
import { useStore } from "@/store/useStore"

/** US-12: classe sugerida pelo SWALIS diferente da classe em vigor; só vale depois de um profissional decidir. */
export default function PaginaInbox() {
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const itens = PACIENTES.filter((p) => p.divergencia).sort(
    (a, b) => CLASSES.indexOf(a.classe) - CLASSES.indexOf(b.classe) || a.posicao_nova - b.posicao_nova
  )

  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <div className="mb-3 flex items-center gap-2">
        <Inbox className="size-4 text-muted-foreground" aria-hidden />
        <h2 className="text-sm font-semibold">Inbox do regulador</h2>
        <span className="text-xs text-muted-foreground tabular-nums">{itens.length} propostas aguardando decisão</span>
      </div>
      {itens.length === 0 ? (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">Nenhuma proposta pendente.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Solicitação</TableHead>
              <TableHead>Procedimento</TableHead>
              <TableHead>Classe atual → sugerida</TableHead>
              <TableHead>Posição</TableHead>
              <TableHead>Motivo principal</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {itens.map((p) => (
              <TableRow key={p.solicitacao_id}>
                <TableCell className="font-medium tabular-nums">{p.solicitacao_id}</TableCell>
                <TableCell className="max-w-56 truncate">{p.procedimento}</TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5">
                    <ClasseBadge classe={p.classe_antiga} /> → <ClasseBadge classe={p.classe} />
                  </span>
                </TableCell>
                <TableCell className="tabular-nums">{p.posicao_nova}</TableCell>
                <TableCell className="max-w-96 truncate text-xs text-muted-foreground">{p.evidencias[0]?.trecho ?? "—"}</TableCell>
                <TableCell>
                  <Button size="xs" variant="outline" onClick={() => abrirNaFila(p.solicitacao_id)}>
                    Revisar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
