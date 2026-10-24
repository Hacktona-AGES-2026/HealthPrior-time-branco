import { useState } from "react"
import { AlertTriangle, ClipboardList, FilterX, RefreshCw, ShieldAlert } from "lucide-react"
import { URL_API, type Evidencia, type Pendencia, type StatusPendencia } from "@/api/cliente"
import { ACOES, REGRAS_PENDENCIA, STATUS_PENDENCIA, rotuloFonte } from "@/lib/pendencias"
import { formatarData } from "@/lib/datas"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ORIGEM_DADOS } from "@/data/fila"
import { AcoesPendencia } from "./AcoesPendencia"
import { AlertasDeDados } from "./AlertasDeDados"
import { usePendencias } from "./usePendencias"

type TipoFiltro = "todas" | "bloqueantes" | "nao-bloqueantes"

const ITENS_TIPO: Record<TipoFiltro, string> = {
  todas: "Todas",
  bloqueantes: "Bloqueantes",
  "nao-bloqueantes": "Não bloqueantes",
}
const ITENS_REGRA: Record<string, string> = {
  todas: "Todas as regras",
  ...Object.fromEntries(Object.entries(REGRAS_PENDENCIA).map(([codigo, nome]) => [codigo, `${codigo} · ${nome}`])),
}
const BLOQUEANTE_DO_FILTRO: Record<TipoFiltro, boolean | undefined> = {
  todas: undefined,
  bloqueantes: true,
  "nao-bloqueantes": false,
}

export default function PaginaPendencias() {
  const [tipo, setTipo] = useState<TipoFiltro>("todas")
  const [regra, setRegra] = useState("todas")
  const [status, setStatus] = useState<StatusPendencia>("aberta")
  const { estado, recarregar } = usePendencias({
    bloqueante: BLOQUEANTE_DO_FILTRO[tipo],
    regra: regra === "todas" ? undefined : regra,
    status,
  })
  const filtrando = tipo !== "todas" || regra !== "todas" || status !== "aberta"
  const limpar = () => {
    setTipo("todas")
    setRegra("todas")
    setStatus("aberta")
  }

  const itens = estado.tipo === "ok" ? estado.dados.itens : []
  const bloqueantes = itens.filter((p) => p.bloqueante).length

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-6xl space-y-4 p-4">
        <header className="fx-fade-up space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <ClipboardList className="size-4" aria-hidden /> Pendências
          </h2>
          <p className="text-sm text-muted-foreground">
            Motivo, evidência e ação sugerida. Pendência <b className="text-foreground">bloqueante</b> tira
            a solicitação da fila priorizada até alguém confirmar; as demais só alertam.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-2" role="search" aria-label="Filtros de pendências">
          <Select items={ITENS_TIPO} value={tipo} onValueChange={(v) => setTipo((v ?? "todas") as TipoFiltro)}>
            <SelectTrigger size="sm" className="h-9 w-full data-[size=sm]:h-9 sm:w-44" aria-label="Filtrar por tipo">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ITENS_TIPO).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select items={ITENS_REGRA} value={regra} onValueChange={(v) => setRegra(v ?? "todas")}>
            <SelectTrigger size="sm" className="h-9 w-full data-[size=sm]:h-9 sm:w-64" aria-label="Filtrar por regra">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ITENS_REGRA).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select items={STATUS_PENDENCIA} value={status} onValueChange={(v) => setStatus((v ?? "aberta") as StatusPendencia)}>
            <SelectTrigger size="sm" className="h-9 w-full data-[size=sm]:h-9 sm:w-40" aria-label="Filtrar por status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(STATUS_PENDENCIA).map(([valor, rotulo]) => (
                <SelectItem key={valor} value={valor}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {filtrando && (
            <Button variant="ghost" size="sm" className="h-9 lg:h-8" onClick={limpar}>
              <FilterX aria-hidden /> Limpar
            </Button>
          )}
          <div className="flex w-full flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground sm:ml-auto sm:w-auto sm:justify-end" aria-live="polite">
            {estado.tipo === "ok" && (
              <>
                <span>
                  <b className="text-foreground tabular-nums">{estado.dados.total}</b> {estado.dados.total === 1 ? "pendência" : "pendências"}
                </span>
                {bloqueantes > 0 && (
                  <Badge variant="destructive">
                    <ShieldAlert aria-hidden /> {bloqueantes} {bloqueantes === 1 ? "bloqueante" : "bloqueantes"}
                  </Badge>
                )}
              </>
            )}
            <Button variant="outline" size="sm" className="h-9 lg:h-8" onClick={recarregar} aria-label="Atualizar a lista">
              <RefreshCw className={cn(estado.tipo === "ok" && estado.atualizando && "animate-spin")} aria-hidden /> Atualizar
            </Button>
          </div>
        </div>

        {estado.tipo === "carregando" && <ListaCarregando />}
        {estado.tipo === "erro" && (ORIGEM_DADOS === "csv" ? <AlertasDeDados onTentar={recarregar} /> : <ErroApi mensagem={estado.mensagem} onTentar={recarregar} />)}
        {estado.tipo === "ok" && itens.length === 0 && <Vazio filtrando={filtrando} onLimpar={limpar} />}
        {estado.tipo === "ok" && itens.length > 0 && (
          <ul className={cn("space-y-3 transition-opacity", estado.atualizando && "opacity-60")} aria-label="Lista de pendências">
            {itens.map((p) => (
              <CartaoPendencia key={p.pendencia_id} pendencia={p} aoResolver={recarregar} />
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function CartaoPendencia({ pendencia: p, aoResolver }: { pendencia: Pendencia; aoResolver: () => void }) {
  const lado = p.evidencias.length > 1 // fontes diferentes aparecem lado a lado
  return (
    <li className={cn("rounded-xl border bg-card p-4", p.bloqueante && "border-destructive/40")}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono">
          {p.regra}
        </Badge>
        {p.bloqueante ? (
          <Badge variant="destructive">
            <ShieldAlert aria-hidden /> Bloqueante
          </Badge>
        ) : (
          <Badge variant="secondary">Não bloqueante</Badge>
        )}
        <h3 className="min-w-0 break-words text-sm font-semibold">{p.titulo}</h3>
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">
          {p.pendencia_id} · aberta em {formatarData(p.aberta_em)}
        </span>
      </div>

      <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm @md:grid-cols-[auto_1fr]">
        <dt className="text-muted-foreground">Solicitação</dt>
        <dd className="font-mono">{p.solicitacao_id}</dd>
        <dt className="text-muted-foreground">Ação sugerida</dt>
        <dd>{p.acao_sugerida}</dd>
      </dl>

      {p.evidencias.length > 0 && (
        <div className="mt-3">
          <h4 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {lado ? "Evidências" : "Evidência"}
          </h4>
          <ul className={cn("grid gap-2", lado && "@lg:grid-cols-2")}>
            {p.evidencias.map((e, i) => (
              <ItemEvidencia key={`${e.fonte}-${e.ref ?? i}`} evidencia={e} />
            ))}
          </ul>
        </div>
      )}

      {p.status === "aberta" ? <AcoesPendencia pendencia={p} aoResolver={aoResolver} /> : <Desfecho pendencia={p} />}
    </li>
  )
}

/** Quem resolveu, quando e como (aparece nas listas de resolvidas e descartadas). */
function Desfecho({ pendencia: p }: { pendencia: Pendencia }) {
  const quando = p.resolvido_em ? formatarData(p.resolvido_em.slice(0, 10)) : null
  return (
    <div className="mt-3 border-t pt-3 text-sm">
      <p>
        <b>{p.status === "descartada" ? "Descartada" : "Resolvida"}</b>
        {p.resolucao && <> · {ACOES[p.resolucao as keyof typeof ACOES]?.rotulo ?? p.resolucao}</>}
        {p.resolvido_por && <> por <span className="font-mono">{p.resolvido_por}</span></>}
        {quando && <> em {quando}</>}
      </p>
      {p.observacao && <p className="mt-1 text-muted-foreground">{p.observacao}</p>}
    </div>
  )
}

function ItemEvidencia({ evidencia: e }: { evidencia: Evidencia }) {
  return (
    <li className="min-w-0 border-l-2 pl-3 text-sm">
      <div className="mb-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
        <span className="font-semibold text-foreground">{rotuloFonte(e.fonte)}</span>
        {e.ref && <span className="break-all font-mono">{e.ref}</span>}
      </div>
      <p className="break-words leading-snug">{e.texto}</p>
    </li>
  )
}

function ListaCarregando() {
  return (
    <div className="space-y-3" role="status" aria-live="polite">
      <span className="fx-loading-dots text-sm text-muted-foreground">Carregando pendências</span>
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-28 w-full rounded-xl" />
      ))}
    </div>
  )
}

function ErroApi({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return (
    <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm" role="alert">
      <p className="flex items-center gap-2 font-semibold text-destructive">
        <AlertTriangle className="size-4" aria-hidden /> Não foi possível carregar as pendências
      </p>
      <p className="mt-1 text-muted-foreground">{mensagem}</p>
      <p className="mt-2 text-muted-foreground">
        Confira se o back está no ar em <code className="break-all rounded bg-muted px-1">{URL_API}</code> (<code className="rounded bg-muted px-1">uvicorn app.main:app</code>, com{" "}
        <code className="rounded bg-muted px-1">HP_USE_MOCKS=false</code> para ver os dados reais) e se a carga foi feita.
      </p>
      <Button variant="outline" size="sm" className="mt-3" onClick={onTentar}>
        <RefreshCw aria-hidden /> Tentar de novo
      </Button>
    </div>
  )
}

function Vazio({ filtrando, onLimpar }: { filtrando: boolean; onLimpar: () => void }) {
  return (
    <div className="rounded-xl bg-muted/40 p-8 text-center text-sm text-muted-foreground">
      <p>{filtrando ? "Nenhuma pendência com esses filtros." : "Nenhuma pendência aberta. Tudo em dia."}</p>
      {filtrando && (
        <Button variant="ghost" size="sm" className="mt-2" onClick={onLimpar}>
          <FilterX aria-hidden /> Limpar filtros
        </Button>
      )}
    </div>
  )
}
