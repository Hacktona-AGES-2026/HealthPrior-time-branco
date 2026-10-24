import type { ReactNode } from "react"
import type { Paciente } from "@/data/tipos"
import { formatarData } from "@/lib/datas"

function Linha({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-x-3">
      <dt className="text-xs text-muted-foreground">{rotulo}</dt>
      <dd className="min-w-0 break-words text-sm">{children}</dd>
    </div>
  )
}

const LIMITACAO = { nenhuma: "nenhuma", leve: "leve", moderada: "moderada", grave: "grave" } as const

/** Quadro clínico: pares rótulo/valor, justificativa do médico solicitante e observações. */
export function QuadroClinico({ p }: { p: Paciente }) {
  const preop = [p.pre_anestesica ? `avaliação pré-anestésica ${p.pre_anestesica}` : null, p.exames_pre_op ? "exames em dia" : "exames pendentes"].filter(Boolean).join(" · ")
  const hba = p.hba1c ? `${String(p.hba1c.valor).replace(".", ",")}%${p.hba1c.data ? ` em ${formatarData(p.hba1c.data)}` : ""}` : null
  const obs = p.observacoes?.trim()
  const just = p.justificativa_clinica?.trim()

  return (
    <section aria-labelledby="quadro" className="space-y-3">
      <h3 id="quadro" className="text-sm font-semibold">
        Quadro clínico
      </h3>
      <dl className="space-y-2">
        <Linha rotulo="Diagnóstico">
          {p.cid}
          {p.cid_descricao && ` — ${p.cid_descricao}`}
          {p.cid_secundario && <span className="text-muted-foreground"> · também CID {p.cid_secundario}</span>}
        </Linha>
        <Linha rotulo="Especialidade">{p.especialidade}</Linha>
        {p.dor !== null && <Linha rotulo="Dor">{p.dor}/10</Linha>}
        {p.limitacao && <Linha rotulo="Limitação funcional">{LIMITACAO[p.limitacao]}</Linha>}
        <Linha rotulo="Comorbidades">{p.comorbidades.length ? p.comorbidades.join(", ") : "Nenhuma registrada"}</Linha>
        {p.asa !== null && <Linha rotulo="Risco anestésico">ASA {p.asa}</Linha>}
        {hba && <Linha rotulo="HbA1c">{hba}</Linha>}
        <Linha rotulo="Pré-operatório">{preop}</Linha>
      </dl>
      {just && (
        <div className="space-y-1">
          <h4 className="text-xs text-muted-foreground">Justificativa do médico solicitante</h4>
          <blockquote className="whitespace-pre-line break-words border-l-2 pl-3 text-sm leading-relaxed">{just}</blockquote>
        </div>
      )}
      {obs && (
        <div className="space-y-1">
          <h4 className="text-xs text-muted-foreground">Observações</h4>
          <p className="whitespace-pre-line break-words text-sm leading-relaxed">{obs}</p>
        </div>
      )}
    </section>
  )
}
