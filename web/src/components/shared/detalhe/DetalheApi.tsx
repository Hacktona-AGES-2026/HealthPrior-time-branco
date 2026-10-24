import { useEffect, useState } from "react"
import { Gavel, ListChecks, MessageSquareQuote, TriangleAlert } from "lucide-react"
import type { Paciente, TipoEvento } from "@/data/tipos"
import { type DetalheApi, MOTIVOS_CODIFICADOS, type MotivoCodificado, obterDetalhe } from "@/lib/api"
import { formatarData } from "@/lib/datas"
import { ClasseBadge } from "@/components/shared/Basicos"
import { CarregandoBloco } from "@/components/shared/Carregando"
import { CartaoGrafico } from "./Cartao"
import { ICONE_EVENTO } from "./IconesEvento"
import { LinhaTempoEventos } from "./LinhaTempoEventos"

const TIPOS_CONHECIDOS = new Set(Object.keys(ICONE_EVENTO))

/** "ponto:obstrucao:llm" -> rótulo + origem; "eixo_*" e "revisar:*" ficam separados. */
const descreverMotivo = (sinal: string, ref?: string | null) => {
  const [tipo, ponto, origem] = sinal.split(":")
  if (tipo === "revisar") return { ponto: ponto.replaceAll("_", " "), origem: `Jev p=${ref ?? "?"} · revisar`, revisar: true }
  if (tipo === "ponto") return { ponto: ponto.replaceAll("_", " "), origem: origem === "llm" ? `Jev p=${ref ?? "?"}` : "palavra-chave", revisar: false }
  return null
}

const ACAO = { aprovar: "Aprovou", editar: "Editou", manter: "Manteve" } as Record<string, string>

/** Ficha com dados da API (US-21): explicação, motivos com origem, eventos, decisões e pendências. */
export function DetalheApiPaciente({ p }: { p: Paciente }) {
  const [d, setD] = useState<DetalheApi | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true  // remontado por paciente (key no pai): sem reset de estado aqui
    obterDetalhe(p.solicitacao_id)
      .then((r) => vivo && setD(r))
      .catch((e) => vivo && setErro(String(e)))
    return () => {
      vivo = false
    }
  }, [p.solicitacao_id])

  if (erro) return <p className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">Não foi possível carregar o detalhe: {erro}</p>
  if (!d) return <CarregandoBloco rotulo="Buscando detalhe na API" altura={220} />

  const eixos = d.score.motivos.filter((m) => m.sinal.startsWith("eixo_"))
  const pontos = d.score.motivos.map((m) => ({ m, info: descreverMotivo(m.sinal, m.ref) })).filter((x) => x.info)
  const eventos: Paciente["eventos"] = d.eventos.map((e) => ({
    data: e.data_evento,
    tipo: (TIPOS_CONHECIDOS.has(e.tipo_evento) ? e.tipo_evento : "consulta_reavaliacao") as TipoEvento,
    descricao: [e.resultado?.replaceAll("_", " "), e.descricao, e.historico ? "(antes da entrada: histórico)" : "", e.duplicado ? "(duplicado)" : ""]
      .filter(Boolean)
      .join(" · "),
  }))

  return (
    <div className="grid gap-3 @lg:grid-cols-2">
      <CartaoGrafico titulo="Por que este paciente está aqui" descricao={d.camada_motivo ?? undefined} className="@lg:col-span-2">
        <p className="flex gap-2 text-sm leading-relaxed">
          <MessageSquareQuote className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
          {d.explicacao}
        </p>
      </CartaoGrafico>

      <CartaoGrafico titulo="Motivos do SWALIS" descricao={`Regras ${d.score.versao_regras ?? ""} · classe sugerida pelo sistema`}>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            Sugerida <ClasseBadge classe={d.score.classe_sistema ?? p.classe} />
            {d.score.classe_medico && (
              <>
                · regulador <ClasseBadge classe={d.score.classe_medico} />
              </>
            )}
          </div>
          <ul className="space-y-1">
            {eixos.map((m) => (
              <li key={m.sinal} className="leading-snug">
                <span className="font-semibold">{m.evidencia.split(":")[0]}:</span>
                {m.evidencia.slice(m.evidencia.indexOf(":") + 1)}
              </li>
            ))}
          </ul>
          {pontos.length > 0 && (
            <ul className="space-y-1 border-t pt-2">
              {pontos.map(({ m, info }, i) => (
                <li key={i} className="flex flex-wrap items-baseline gap-1.5 leading-snug">
                  <span className="rounded bg-background px-1.5 py-0.5 font-medium">{info!.ponto}</span>
                  <span className={info!.revisar ? "text-[var(--prazo-limite)]" : "text-muted-foreground"}>{info!.origem}</span>
                  <q className="text-muted-foreground">{m.evidencia}</q>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CartaoGrafico>

      <LinhaTempoEventos p={{ ...p, eventos }} />

      <CartaoGrafico titulo="Decisões do regulador" descricao={`${d.decisoes.length} no log`}>
        {d.decisoes.length === 0 ? (
          <p className="text-xs text-muted-foreground">Nenhuma decisão ainda: a classe é sugestão do sistema, não confirmada.</p>
        ) : (
          <ul className="space-y-2 text-xs">
            {d.decisoes.map((x) => (
              <li key={x.decisao_id} className="flex gap-2">
                <Gavel className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold">{ACAO[x.acao] ?? x.acao}</span>
                    {x.classe_decidida && <ClasseBadge classe={x.classe_decidida} />}
                    <span className="text-muted-foreground">
                      {x.regulador_id} · {formatarData(x.data.slice(0, 10))}
                    </span>
                  </div>
                  {x.motivo_codificado && <div className="text-muted-foreground">{MOTIVOS_CODIFICADOS[x.motivo_codificado as MotivoCodificado] ?? x.motivo_codificado}</div>}
                  {x.justificativa && <q className="text-muted-foreground">{x.justificativa}</q>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CartaoGrafico>

      <CartaoGrafico titulo="Pendências e alertas" descricao={`${d.pendencias.length} pendências · ${d.alertas.length} alertas`}>
        <ul className="space-y-1 text-xs">
          {d.pendencias.map((x) => (
            <li key={x.pendencia_id} className="flex items-center gap-1.5">
              <ListChecks className="size-3.5 text-muted-foreground" aria-hidden />
              <span className="font-medium tabular-nums">{x.pendencia_id}</span> {x.regra} · {x.status}
              {x.bloqueante && <span className="text-[var(--desce)]">bloqueante</span>}
            </li>
          ))}
          {d.alertas.map((a) => (
            <li key={a} className="flex items-center gap-1.5 text-muted-foreground">
              <TriangleAlert className="size-3.5" aria-hidden /> {a.replaceAll("_", " ")}
            </li>
          ))}
          {d.pendencias.length + d.alertas.length === 0 && <li className="text-muted-foreground">Nada pendente.</li>}
        </ul>
      </CartaoGrafico>
    </div>
  )
}
