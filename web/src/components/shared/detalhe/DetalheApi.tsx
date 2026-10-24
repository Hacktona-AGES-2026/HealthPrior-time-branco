import { useEffect, useMemo, useState } from "react"
import { ORIGEM_DADOS } from "@/data/fila"
import type { Evento, Paciente, TipoEvento } from "@/data/tipos"
import { type DetalheApi, MOTIVOS_CODIFICADOS, type MotivoCodificado, obterDetalheEmCache } from "@/lib/api"
import { useStore } from "@/store/useStore"
import { CorrigirCid } from "./CorrigirCid"
import { HistoricoPaciente, type DecisaoHistorico } from "./HistoricoPaciente"

const TIPOS: TipoEvento[] = ["biopsia", "hba1c", "pronto_socorro", "internacao", "exame_imagem", "consulta_reavaliacao", "contato_telefonico", "falta"]

const PENDENCIA: Record<string, string> = {
  "PRE-10": "Contato do paciente perdido: confirmar telefone com o agente de saúde",
  "PRE-11": "Contato só pelo agente de saúde",
  "PRE-12": "Possível câncer não registrado: conferir diagnóstico",
  "PRE-13": "Possível diabetes fora do cadastro: conferir",
  "PRE-20": "Possível duplicata de outra solicitação",
  "PRE-21": "Paciente pode ter operado em outro serviço",
  "PRE-22": "Paciente pode ter operado pelo convênio",
  "PRE-23": "Paciente pode ter desistido da cirurgia",
  "PRE-24": "Registro sem solicitação correspondente: conferir",
  "PRE-25": "Informações contraditórias no cadastro: conferir",
}

const ALERTA: [RegExp, string][] = [
  [/flag de piora/i, "Cadastro indica piora diferente do histórico: conferir"],
  [/flag oncol/i, "Cadastro de câncer não bate com o diagnóstico: conferir"],
]

const traduzirAlerta = (a: string) => {
  const hit = ALERTA.find(([re]) => re.test(a))
  if (hit) return hit[1]
  const t = a.replaceAll("_", " ").replace(/PRE-\d+/g, "").trim()
  return t.charAt(0).toUpperCase() + t.slice(1)
}

type PendenciaApi = DetalheApi["pendencias"][number]

/** Lista de pendências e alertas em frases; some quando não há nada. */
export function PendenciasAlertas({ alertas, pendencias = [] }: { alertas: string[]; pendencias?: PendenciaApi[] }) {
  const abertas = pendencias.filter((x) => x.status === "aberta")
  const frases = [
    ...abertas.map((x) => (PENDENCIA[x.regra] ?? "Pendência a conferir") + (x.bloqueante ? " (aguardando conferência da equipe)" : "")),
    ...alertas.map(traduzirAlerta),
  ]
  const unicas = [...new Set(frases)]
  if (unicas.length === 0) return null
  return (
    <section aria-labelledby="pendencias" className="space-y-2">
      <h3 id="pendencias" className="text-sm font-semibold">
        Pendências e alertas
      </h3>
      <ul className="list-disc space-y-0.5 pl-4 text-sm">
        {unicas.map((f) => (
          <li key={f} className="break-words">
            {f}
          </li>
        ))}
      </ul>
    </section>
  )
}

const frasesDecisao = (d: DetalheApi["decisoes"][number]): string => {
  const quem = `Dr(a). ${d.regulador_id}`
  const motivo = d.motivo_codificado ? (MOTIVOS_CODIFICADOS[d.motivo_codificado as MotivoCodificado] ?? "") : ""
  const extra = [motivo, d.justificativa ?? ""].filter(Boolean).join(": ")
  const base =
    d.acao === "editar" ? `Classe alterada${d.classe_decidida ? ` para ${d.classe_decidida}` : ""} por ${quem}`
    : d.acao === "aprovar" ? `Classe${d.classe_decidida ? ` ${d.classe_decidida}` : ""} aprovada por ${quem}`
    : `Classe mantida por ${quem}`
  return extra ? `${base} — ${extra}` : base
}

/** Detalhe da API com cache em memória por id (uma só chamada por solicitação). Nulo no modo offline. */
export function useDetalheApi(id: string): { d: DetalheApi | null; erro: boolean } {
  const [estado, setEstado] = useState<{ id: string; d: DetalheApi | null; erro: boolean } | null>(null)
  const versaoDados = useStore((s) => s.versaoDados)  // depois de uma ação (ex.: CID corrigido) a ficha busca de novo

  useEffect(() => {
    if (ORIGEM_DADOS !== "api") return
    let vivo = true
    obterDetalheEmCache(id).then((r) => vivo && setEstado({ id, d: r, erro: false })).catch(() => vivo && setEstado({ id, d: null, erro: true }))
    return () => {
      vivo = false
    }
  }, [id, versaoDados])

  return estado && estado.id === id ? { d: estado.d, erro: estado.erro } : { d: null, erro: false }
}

/** Histórico e pendências com os registros reais da API somados aos do paciente. */
export function DetalheApiPaciente({ p }: { p: Paciente }) {
  const { d, erro } = useDetalheApi(p.id)
  const recarregar = useStore((s) => s.recarregar)

  const comApi = useMemo(() => {
    if (!d) return { p, decisoes: [] as DecisaoHistorico[] }
    const conhecidos = new Set(p.eventos.map((e) => e.id))
    const novos: Evento[] = d.eventos
      .filter((e) => !conhecidos.has(e.evento_id) && !e.duplicado)
      .map((e) => ({
        id: e.evento_id,
        data: e.data_evento,
        tipo: (TIPOS.includes(e.tipo_evento as TipoEvento) ? e.tipo_evento : "consulta_reavaliacao") as TipoEvento,
        resultado: e.resultado,
        valor: e.valor_numerico ?? null,
        descricao: e.descricao ?? "",
        origem: e.origem ?? null,
        historico: e.historico,
      }))
    return {
      p: { ...p, eventos: [...p.eventos, ...novos] },
      decisoes: d.decisoes.map((x) => ({ id: x.decisao_id, data: x.data.slice(0, 10), texto: frasesDecisao(x) })),
    }
  }, [d, p])

  return (
    <>
      <HistoricoPaciente p={comApi.p} decisoes={comApi.decisoes} carregando={ORIGEM_DADOS === "api" && !d && !erro} />
      <PendenciasAlertas alertas={d ? d.alertas : p.alertas} pendencias={d?.pendencias} />
      {d?.cid_original && (
        <p className="text-sm text-muted-foreground">
          CID corrigido pelo regulador: {d.cid_original} → <span className="font-medium text-foreground">{d.cid}</span>
        </p>
      )}
      {d?.pendencias
        .filter((x) => x.regra === "PRE-12" && x.status === "aberta")
        .map((x) => (
          <CorrigirCid key={x.pendencia_id} pendencia={x} cidAtual={d.cid} aoCorrigir={() => void recarregar()} />
        ))}
    </>
  )
}
