import { TriangleAlert } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { PRAZO_MAX } from "@/lib/cores"
import { formatarData } from "@/lib/datas"
import { CamadaBadge, ClasseBadge } from "@/components/shared/Basicos"
import { CartaoGrafico } from "./Cartao"

function Linha({ rotulo, children, alto }: { rotulo: string; children: React.ReactNode; alto?: boolean }) {
  return (
    <TableRow>
      <TableCell className={`w-48 font-medium text-muted-foreground ${alto ? "align-top" : ""}`}>{rotulo}</TableCell>
      <TableCell className="whitespace-normal">{children}</TableCell>
    </TableRow>
  )
}

export function DadosSistema({ p }: { p: Paciente }) {
  const nuncaRevisada = p.data_revisao_prioridade === p.data_entrada
  return (
    <CartaoGrafico titulo="Dados do sistema" descricao="O que o pipeline calculou e o que veio do cadastro" className="@lg:col-span-2">
      <Table>
        <TableBody>
          <Linha rotulo="Classe sugerida">
            <span className="inline-flex flex-wrap items-center gap-2">
              <ClasseBadge classe={p.classe} />
              <span className="text-xs text-muted-foreground">prazo de {PRAZO_MAX[p.classe]} dias · regras {p.versao_regras}</span>
              {p.versao_regras.startsWith("stub") && <Badge variant="outline" className="font-normal">SWALIS provisório: classe pela prioridade manual</Badge>}
            </span>
          </Linha>
          <Linha rotulo="Eixos do classificador" alto>
            <ul className="space-y-1 text-xs">
              <li>
                <b>Progressão {p.eixos.progressao.nivel}/3</b>
                <span className="text-muted-foreground"> · {p.eixos.progressao.motivos.join("; ") || "nenhum risco registrado"}</span>
              </li>
              <li>
                <b>Sintoma {p.eixos.sintoma.nivel}/2</b>
                <span className="text-muted-foreground"> · {p.eixos.sintoma.motivos.join("; ") || "nenhum sintoma relevante"}</span>
              </li>
            </ul>
          </Linha>
          {p.sinais_texto.length > 0 && (
            <Linha rotulo="Sinais extraídos do texto" alto>
              <ul className="space-y-1 text-xs">
                {p.sinais_texto.map((s, i) => (
                  <li key={`${s.trecho}-${i}`} className="fx-fade-up flex flex-wrap items-center gap-1.5" style={{ animationDelay: `${i * 60}ms` }}>
                    <Badge variant={s.origem === "regra" ? "secondary" : "outline"} className="px-1.5 font-normal">
                      {s.origem === "regra" ? "regra · muda a classe" : "LLM · só alerta"}
                    </Badge>
                    <span className="text-muted-foreground">{s.categoria.replaceAll("_", " ")}</span>
                    <span>“{s.trecho}”</span>
                  </li>
                ))}
              </ul>
            </Linha>
          )}
          <Linha rotulo="Camada">
            <CamadaBadge camada={p.camada} />
          </Linha>
          <Linha rotulo="% do prazo consumido">
            <span className="tabular-nums">{p.pct.toLocaleString("pt-BR")}%</span>
            <span className="ml-2 text-xs text-muted-foreground">
              {p.dias_em_fila.toLocaleString("pt-BR")} dias ÷ {PRAZO_MAX[p.classe]}
            </span>
          </Linha>
          <Linha rotulo="Prioridade manual do cadastro">
            {p.prioridade_atual ? <span className="capitalize">{p.prioridade_atual === "media" ? "média" : p.prioridade_atual}</span> : <span className="text-muted-foreground">vazia</span>}
            <span className="ml-2 text-xs text-muted-foreground">
              {p.data_revisao_prioridade ? (nuncaRevisada ? "nunca revisada desde a entrada" : `revisada em ${formatarData(p.data_revisao_prioridade)}`) : "sem data de revisão"}
            </span>
          </Linha>
          <Linha rotulo="CID">
            <span className="font-semibold">{p.cid}</span>
            {p.cid !== p.cid_norm && <span className="text-xs text-muted-foreground"> (normalizado: {p.cid_norm})</span>} · {p.cid_descricao}
            {p.cid_secundario && <div className="text-xs text-muted-foreground">Secundário: {p.cid_secundario}</div>}
          </Linha>
          <Linha rotulo="Comorbidades" alto>
            {p.comorbidades.length === 0 ? (
              <span className="text-muted-foreground">Nenhuma registrada</span>
            ) : (
              <span className="flex flex-wrap gap-1.5">
                {p.comorbidades.map((c) => (
                  <Badge key={c} variant="secondary" className="font-normal">
                    {c}
                  </Badge>
                ))}
              </span>
            )}
          </Linha>
          <Linha rotulo="Alertas de dados" alto>
            {p.alertas.length === 0 ? (
              <span className="text-muted-foreground">Nenhum</span>
            ) : (
              <ul className="space-y-1 text-xs">
                {p.alertas.map((a) => (
                  <li key={a} className="flex items-center gap-1.5">
                    <TriangleAlert className="size-3.5 shrink-0" style={{ color: "var(--prazo-limite)" }} aria-hidden />
                    {a}
                  </li>
                ))}
              </ul>
            )}
          </Linha>
        </TableBody>
      </Table>
    </CartaoGrafico>
  )
}
