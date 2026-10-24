import { AlertCircle, ArrowRight, CheckCircle2, Clock, Gauge, HeartPulse, Hourglass, Layers, ListOrdered, Stethoscope, TriangleAlert, Activity } from "lucide-react"
import type { ReactNode } from "react"
import type { Paciente } from "@/data/tipos"
import { PRAZO_MAX } from "@/lib/cores"
import { HOJE, diffDias, formatarData } from "@/lib/datas"
import { cn } from "@/lib/utils"
import { CamadaBadge, ClasseBadge, PrazoBar, SetaVariacao } from "@/components/shared/Basicos"

function Cartao({ icone: Icone, titulo, children, alerta, indice }: { icone: typeof Clock; titulo: string; children: ReactNode; alerta?: boolean; indice: number }) {
  return (
    <div
      className={cn("fx-fade-up flex min-w-0 flex-col gap-1.5 rounded-xl bg-muted/40 p-2.5")}
      style={{ animationDelay: `${indice * 45}ms`, background: alerta ? "color-mix(in oklab, var(--prazo-limite) 10%, transparent)" : undefined }}
    >
      <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        <Icone className="size-3.5" aria-hidden />
        {titulo}
        {alerta && <TriangleAlert className="ml-auto size-3.5" style={{ color: "var(--prazo-limite)" }} aria-label="Atenção" />}
      </div>
      <div className="min-w-0 text-sm">{children}</div>
    </div>
  )
}

function Pontos({ valor, total, cor }: { valor: number; total: number; cor: string }) {
  return (
    <span className="flex gap-0.5" aria-hidden>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className="h-1.5 flex-1 rounded-full" style={{ background: i < valor ? cor : "var(--muted)", transition: "background 0.3s", transitionDelay: `${i * 30}ms` }} />
      ))}
    </span>
  )
}

const NIVEL_LIMITACAO = { nenhuma: 0, leve: 1, moderada: 2, grave: 3 }
const ASA_ROMANO = ["", "I", "II", "III", "IV"]
const NAO_INFORMADO = <span className="text-xs text-muted-foreground">Não informado</span>

export function Kpis({ p }: { p: Paciente }) {
  const hba1cEventos = p.eventos.filter((e) => e.tipo === "hba1c" && e.valor !== null)
  const ultimoEvento = hba1cEventos[hba1cEventos.length - 1]
  const hba1cValor = ultimoEvento?.valor ?? p.hba1c?.valor ?? null
  const hba1cData = ultimoEvento?.data ?? p.hba1c?.data ?? null
  const hba1cAlta = hba1cValor !== null && hba1cValor > 8.5
  const hba1cAntiga = hba1cData ? diffDias(hba1cData, HOJE) > 90 : false
  const corDor = p.dor === null ? "var(--muted-foreground)" : p.dor >= 7 ? "var(--desce)" : p.dor >= 4 ? "var(--prazo-limite)" : "var(--sobe)"
  const preOpOk = p.pre_anestesica === "realizada" && p.exames_pre_op

  return (
    <div className="@container">
      <div className="grid grid-cols-2 gap-2 @lg:grid-cols-3 @3xl:grid-cols-4">
        <Cartao indice={0} icone={Clock} titulo="Dias em fila">
          <span className="text-xl font-bold tabular-nums">{p.dias_em_fila.toLocaleString("pt-BR")}</span>
          <span className="ml-1 text-xs text-muted-foreground">desde {formatarData(p.data_entrada)}</span>
        </Cartao>
        <Cartao indice={1} icone={Hourglass} titulo={`% do prazo (${PRAZO_MAX[p.classe]} dias)`} alerta={p.pct > 100}>
          <PrazoBar pct={p.pct} />
        </Cartao>
        <Cartao indice={2} icone={Activity} titulo="Prioridade → classe">
          <span className="inline-flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground">{p.prioridade_atual ? (p.prioridade_atual === "media" ? "média" : p.prioridade_atual) : "sem prioridade"}</span>
            <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
            <ClasseBadge classe={p.classe} className="fx-pop" />
          </span>
        </Cartao>
        <Cartao indice={3} icone={ListOrdered} titulo="Posição atual → proposta">
          <span className="inline-flex flex-wrap items-center gap-1.5 font-bold tabular-nums">
            {p.posicao_atual}
            <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
            {p.posicao}
            <SetaVariacao antiga={p.posicao_atual} nova={p.posicao} />
          </span>
        </Cartao>
        <Cartao indice={4} icone={Layers} titulo="Camada">
          <CamadaBadge camada={p.camada} />
        </Cartao>
        <Cartao indice={5} icone={HeartPulse} titulo="Dor (EVA)">
          {p.dor === null ? (
            NAO_INFORMADO
          ) : (
            <>
              <div className="mb-1 font-bold tabular-nums" style={{ color: corDor }}>
                {p.dor}
                <span className="text-xs font-normal text-muted-foreground">/10</span>
              </div>
              <Pontos valor={p.dor} total={10} cor={corDor} />
            </>
          )}
        </Cartao>
        <Cartao indice={6} icone={Gauge} titulo="Limitação funcional">
          {p.limitacao === null ? (
            NAO_INFORMADO
          ) : (
            <>
              <div className="mb-1 font-semibold capitalize">{p.limitacao}</div>
              <Pontos valor={NIVEL_LIMITACAO[p.limitacao]} total={3} cor="var(--primary)" />
            </>
          )}
        </Cartao>
        <Cartao indice={7} icone={Stethoscope} titulo="ASA">
          {p.asa === null ? (
            NAO_INFORMADO
          ) : (
            <>
              <span className="text-xl font-bold">{ASA_ROMANO[p.asa]}</span>
              <span className="ml-1 text-xs text-muted-foreground">risco anestésico</span>
            </>
          )}
        </Cartao>
        <Cartao indice={8} icone={AlertCircle} titulo="HbA1c" alerta={hba1cAlta}>
          {hba1cValor === null ? (
            <span className="text-xs text-muted-foreground">Sem registro</span>
          ) : (
            <>
              <span className="text-lg font-bold tabular-nums" style={{ color: hba1cAlta ? "var(--desce)" : undefined }}>
                {String(hba1cValor).replace(".", ",")}%
              </span>
              <div className="text-[11px] text-muted-foreground">
                {hba1cData ? formatarData(hba1cData) : "sem data"}
                {hba1cAlta && " · acima de 8,5%"}
                {hba1cAntiga && " · há mais de 90 dias"}
              </div>
            </>
          )}
        </Cartao>
        <Cartao indice={9} icone={CheckCircle2} titulo="Pré-operatório" alerta={p.pre_anestesica === "vencida"}>
          <ul className="space-y-0.5 text-xs">
            <li className="flex items-center gap-1">
              {p.pre_anestesica === "realizada" ? <CheckCircle2 className="size-3.5" style={{ color: "var(--sobe)" }} aria-hidden /> : <AlertCircle className="size-3.5" style={{ color: "var(--prazo-limite)" }} aria-hidden />}
              Anestésica {p.pre_anestesica ?? "sem registro"}
            </li>
            <li className="flex items-center gap-1">
              {p.exames_pre_op ? <CheckCircle2 className="size-3.5" style={{ color: "var(--sobe)" }} aria-hidden /> : <AlertCircle className="size-3.5" style={{ color: "var(--prazo-limite)" }} aria-hidden />}
              Exames {p.exames_pre_op ? "válidos" : "não válidos"}
            </li>
          </ul>
          {preOpOk && <span className="sr-only">Pré-operatório completo</span>}
        </Cartao>
      </div>
    </div>
  )
}
