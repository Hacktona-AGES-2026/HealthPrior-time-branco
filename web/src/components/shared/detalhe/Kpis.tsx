import { AlertCircle, ArrowRight, CheckCircle2, Clock, Gauge, HeartPulse, Hourglass, Stethoscope, TriangleAlert, Activity, ListOrdered } from "lucide-react"
import type { ReactNode } from "react"
import type { Paciente } from "@/data/tipos"
import { HOJE, diffDias, formatarData } from "@/lib/datas"
import { cn } from "@/lib/utils"
import { ClasseBadge, ConfiancaSelo, PrazoBar, SetaVariacao } from "@/components/shared/Basicos"

function Cartao({ icone: Icone, titulo, children, alerta, indice }: { icone: typeof Clock; titulo: string; children: ReactNode; alerta?: boolean; indice: number }) {
  return (
    <div
      className={cn("fx-fade-up flex min-w-0 flex-col gap-1.5 rounded-xl bg-muted/40 p-2.5",)}
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

export function Kpis({ p }: { p: Paciente }) {
  const hba1cAlta = p.hba1c ? p.hba1c.valor >= 8 : false
  const hba1cAntiga = p.hba1c ? diffDias(p.hba1c.data, HOJE) > 90 : false
  const hba1cAlerta = hba1cAlta || hba1cAntiga
  const corDor = p.intensidade_dor_eva >= 7 ? "var(--desce)" : p.intensidade_dor_eva >= 4 ? "var(--prazo-limite)" : "var(--sobe)"
  const preOpOk = p.avaliacao_pre_anestesica && p.exames_pre_op_validos

  return (
    <div className="@container">
      <div className="grid grid-cols-2 gap-2 @lg:grid-cols-3 @3xl:grid-cols-5">
        <Cartao indice={0} icone={Clock} titulo="Dias em fila">
          <span className="text-xl font-bold tabular-nums">{p.dias_em_fila}</span>
          <span className="ml-1 text-xs text-muted-foreground">desde {formatarData(p.data_entrada_fila)}</span>
        </Cartao>
        <Cartao indice={1} icone={Hourglass} titulo="% do prazo" alerta={p.prazo_consumido_pct > 100}>
          <PrazoBar pct={p.prazo_consumido_pct} />
        </Cartao>
        <Cartao indice={2} icone={Activity} titulo="Classe">
          <span className="inline-flex items-center gap-1.5">
            <ClasseBadge classe={p.classe_antiga} className="opacity-70" />
            <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
            <ClasseBadge classe={p.classe} className="fx-pop" />
          </span>
        </Cartao>
        <Cartao indice={3} icone={ListOrdered} titulo="Posição">
          <span className="inline-flex flex-wrap items-center gap-1.5 font-bold tabular-nums">
            {p.posicao_antiga}
            <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
            {p.posicao_nova}
            <SetaVariacao antiga={p.posicao_antiga} nova={p.posicao_nova} />
          </span>
        </Cartao>
        <Cartao indice={4} icone={Gauge} titulo="Confiança" alerta={p.confianca < 0.6}>
          <ConfiancaSelo valor={p.confianca} />
        </Cartao>
        <Cartao indice={5} icone={HeartPulse} titulo="Dor (EVA)">
          <div className="mb-1 font-bold tabular-nums" style={{ color: corDor }}>
            {p.intensidade_dor_eva}
            <span className="text-xs font-normal text-muted-foreground">/10</span>
          </div>
          <Pontos valor={p.intensidade_dor_eva} total={10} cor={corDor} />
        </Cartao>
        <Cartao indice={6} icone={Activity} titulo="Limitação funcional">
          <div className="mb-1 font-semibold capitalize">{p.limitacao_funcional}</div>
          <Pontos valor={NIVEL_LIMITACAO[p.limitacao_funcional]} total={3} cor="var(--primary)" />
        </Cartao>
        <Cartao indice={7} icone={Stethoscope} titulo="ASA">
          <span className="text-xl font-bold">{ASA_ROMANO[p.asa]}</span>
          <span className="ml-1 text-xs text-muted-foreground">risco anestésico</span>
        </Cartao>
        <Cartao indice={8} icone={AlertCircle} titulo="HbA1c" alerta={hba1cAlerta}>
          {p.hba1c ? (
            <>
              <span className="text-lg font-bold tabular-nums" style={{ color: hba1cAlta ? "var(--desce)" : undefined }}>
                {String(p.hba1c.valor).replace(".", ",")}%
              </span>
              <div className="text-[11px] text-muted-foreground">
                {formatarData(p.hba1c.data)}
                {hba1cAlta && " · alta"}
                {hba1cAntiga && " · desatualizada"}
              </div>
            </>
          ) : (
            <span className="text-xs text-muted-foreground">Não aplicável</span>
          )}
        </Cartao>
        <Cartao indice={9} icone={CheckCircle2} titulo="Pré-operatório" alerta={!preOpOk}>
          <ul className="space-y-0.5 text-xs">
            <li className="flex items-center gap-1">
              {p.avaliacao_pre_anestesica ? <CheckCircle2 className="size-3.5" style={{ color: "var(--sobe)" }} aria-hidden /> : <AlertCircle className="size-3.5" style={{ color: "var(--prazo-limite)" }} aria-hidden />}
              Avaliação anestésica {p.avaliacao_pre_anestesica ? "ok" : "pendente"}
            </li>
            <li className="flex items-center gap-1">
              {p.exames_pre_op_validos ? <CheckCircle2 className="size-3.5" style={{ color: "var(--sobe)" }} aria-hidden /> : <AlertCircle className="size-3.5" style={{ color: "var(--prazo-limite)" }} aria-hidden />}
              Exames {p.exames_pre_op_validos ? "válidos" : "pendentes"}
            </li>
          </ul>
        </Cartao>
      </div>
    </div>
  )
}
