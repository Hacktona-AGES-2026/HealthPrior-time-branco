import { ArrowUpCircle, Lightbulb } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { formatarData } from "@/lib/datas"
import { ClasseBadge } from "@/components/shared/Basicos"
import { RegrasChips } from "@/components/shared/RegrasChips"
import { CartaoGrafico } from "./Cartao"

const ROTULO_FONTE = { texto: "Texto", evento: "Evento", cid: "CID", regra: "Regra" }

export function ParametrosIA({ p }: { p: Paciente }) {
  const ia = p.parametros_ia
  return (
    <CartaoGrafico titulo="Parâmetros da IA" descricao="Tudo o que o modelo e as regras usaram para decidir" className="@lg:col-span-2">
      <Table>
        <TableBody>
          <TableRow>
            <TableCell className="w-44 font-medium text-muted-foreground">Modelo</TableCell>
            <TableCell>{ia.modelo}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="font-medium text-muted-foreground">Versão das regras</TableCell>
            <TableCell>
              <Badge variant="outline">{ia.versao_regras}</Badge>
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="font-medium text-muted-foreground">Classe base do CID</TableCell>
            <TableCell>
              <span className="inline-flex items-center gap-2">
                <ClasseBadge classe={ia.classe_base_cid} />
                <span className="text-xs text-muted-foreground">
                  {p.cid} · {p.cid_descricao}
                </span>
              </span>
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="align-top font-medium text-muted-foreground">Regras acionadas</TableCell>
            <TableCell className="whitespace-normal">
              <RegrasChips regras={ia.regras_acionadas} />
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="align-top font-medium text-muted-foreground">Sinais extraídos do texto</TableCell>
            <TableCell className="whitespace-normal">
              <ul className="space-y-1.5">
                {ia.sinais_texto.map((s, i) => (
                  <li key={s.trecho} className="fx-fade-up flex items-center gap-2 text-xs" style={{ animationDelay: `${i * 80}ms` }}>
                    <Badge variant="secondary">{s.sinal}</Badge>
                    <span className="min-w-0 flex-1 truncate text-muted-foreground" title={s.trecho}>
                      “{s.trecho}”
                    </span>
                    <span className="relative h-1.5 w-16 overflow-hidden rounded-full bg-muted" aria-hidden>
                      <span className="fx-grow-x absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${s.confianca * 100}%`, animationDelay: `${i * 80 + 200}ms` }} />
                    </span>
                    <span className="w-9 text-right font-semibold tabular-nums">{Math.round(s.confianca * 100)}%</span>
                  </li>
                ))}
              </ul>
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="align-top font-medium text-muted-foreground">Evidências</TableCell>
            <TableCell className="whitespace-normal">
              <ul className="space-y-1">
                {p.evidencias.map((e, i) => (
                  <li key={`${e.trecho}-${i}`} className="flex items-start gap-2 text-xs">
                    <Badge variant="outline" className="shrink-0 uppercase">
                      {ROTULO_FONTE[e.fonte]}
                    </Badge>
                    <span className="text-muted-foreground">
                      {e.trecho}
                      {e.data && <span className="ml-1 tabular-nums">({formatarData(e.data)})</span>}
                    </span>
                  </li>
                ))}
              </ul>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      <div className="mt-3 grid gap-2 @lg:grid-cols-2">
        <div className="rounded-lg border bg-muted/40 p-2.5 text-xs">
          <div className="mb-1 flex items-center gap-1.5 font-semibold uppercase tracking-wide text-muted-foreground">
            <Lightbulb className="size-3.5" aria-hidden /> Contrafactual
          </div>
          {ia.contrafactual}
        </div>
        <div className="rounded-lg border bg-muted/40 p-2.5 text-xs">
          <div className="mb-1 flex items-center gap-1.5 font-semibold uppercase tracking-wide text-muted-foreground">
            <ArrowUpCircle className="size-3.5" aria-hidden /> O que falta para subir
          </div>
          {p.falta_para_subir}
        </div>
      </div>
    </CartaoGrafico>
  )
}
