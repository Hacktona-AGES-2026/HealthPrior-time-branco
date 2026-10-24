import type { ReactNode } from "react"
import { ClipboardPlus, IdCard, Stethoscope } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import { Badge } from "@/components/ui/badge"
import { formatarData } from "@/lib/datas"
import { ClasseBadge } from "@/components/shared/Basicos"

function Campo({ rotulo, children, larga }: { rotulo: string; children: ReactNode; larga?: boolean }) {
  return (
    <div className={larga ? "col-span-full" : undefined}>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{rotulo}</dt>
      <dd className="mt-0.5 text-sm">{children}</dd>
    </div>
  )
}

function Bloco({ titulo, icone: Icone, children, indice }: { titulo: string; icone: typeof IdCard; children: ReactNode; indice: number }) {
  return (
    <section className="fx-fade-up rounded-xl bg-muted/40" style={{ animationDelay: `${indice * 90}ms` }}>
      <h3 className="flex items-center gap-1.5 border-b bg-muted/50 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
        <Icone className="size-3.5" aria-hidden /> {titulo}
      </h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 p-3 @lg:grid-cols-3">{children}</dl>
    </section>
  )
}

export function FichaSus({ p }: { p: Paciente }) {
  return (
    <div className="@container space-y-3" aria-label="Ficha SUS">
      <Bloco titulo="Identificação" icone={IdCard} indice={0}>
        <Campo rotulo="Solicitação">{p.solicitacao_id}</Campo>
        <Campo rotulo="Iniciais">{p.iniciais}</Campo>
        <Campo rotulo="CNS (mascarado)">
          <span className="tabular-nums">{p.cns_mascarado}</span>
        </Campo>
        <Campo rotulo="Idade / sexo">
          {p.idade} anos · {p.sexo === "F" ? "Feminino" : "Masculino"}
        </Campo>
        <Campo rotulo="Município">{p.municipio}</Campo>
        <Campo rotulo="Distância do hospital">{p.distancia_hospital_km} km</Campo>
      </Bloco>

      <Bloco titulo="Pedido cirúrgico" icone={ClipboardPlus} indice={1}>
        <Campo rotulo="Procedimento" larga>
          {p.procedimento}
        </Campo>
        <Campo rotulo="Especialidade">{p.especialidade}</Campo>
        <Campo rotulo="Data de entrada na fila">{formatarData(p.data_entrada_fila)}</Campo>
        <Campo rotulo="Dias em fila">{p.dias_em_fila}</Campo>
        <Campo rotulo="CID principal" larga>
          <span className="font-semibold">{p.cid}</span> · {p.cid_descricao}
        </Campo>
        <Campo rotulo="CID secundário" larga>
          {p.cid_secundario ?? <span className="text-muted-foreground">Não informado</span>}
        </Campo>
        <Campo rotulo="Classe (antiga → nova)">
          <span className="inline-flex items-center gap-1.5">
            <ClasseBadge classe={p.classe_antiga} /> → <ClasseBadge classe={p.classe} />
          </span>
        </Campo>
      </Bloco>

      <Bloco titulo="Quadro clínico" icone={Stethoscope} indice={2}>
        <Campo rotulo="Comorbidades" larga>
          <span className="flex flex-wrap gap-1.5">
            {p.comorbidades.length === 0 && <span className="text-muted-foreground">Nenhuma registrada</span>}
            {p.comorbidades.map((c) => (
              <Badge key={c} variant="secondary">
                {c}
              </Badge>
            ))}
          </span>
        </Campo>
        <Campo rotulo="ASA">{p.asa}</Campo>
        <Campo rotulo="Dor (EVA)">{p.intensidade_dor_eva}/10</Campo>
        <Campo rotulo="Limitação funcional">
          <span className="capitalize">{p.limitacao_funcional}</span>
        </Campo>
        <Campo rotulo="HbA1c">{p.hba1c ? `${String(p.hba1c.valor).replace(".", ",")}% em ${formatarData(p.hba1c.data)}` : <span className="text-muted-foreground">Não aplicável</span>}</Campo>
        <Campo rotulo="Avaliação pré-anestésica">{p.avaliacao_pre_anestesica ? "Realizada" : "Pendente"}</Campo>
        <Campo rotulo="Exames pré-operatórios">{p.exames_pre_op_validos ? "Válidos" : "Pendentes"}</Campo>
        <Campo rotulo="Justificativa clínica" larga>
          {p.justificativa_clinica}
        </Campo>
        <Campo rotulo="Observações" larga>
          {p.observacoes || <span className="text-muted-foreground">Sem observações</span>}
        </Campo>
      </Bloco>
    </div>
  )
}
