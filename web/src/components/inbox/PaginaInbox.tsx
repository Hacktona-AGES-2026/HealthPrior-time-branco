import { useState } from "react"
import { AlertTriangle, ArrowRight, Check, Inbox as IconeInbox, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { aprovarProposta, URL_API, type ItemInbox } from "@/api/cliente"
import { formatarData } from "@/lib/datas"
import { usuarioAtual } from "@/lib/usuario"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useInbox } from "./useInbox"

export default function PaginaInbox() {
  const { estado, recarregar } = useInbox()
  const itens = estado.tipo === "ok" ? estado.dados.itens : []

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-5xl space-y-4 p-4">
        <header className="fx-fade-up space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <IconeInbox className="size-4" aria-hidden /> Inbox de revisão
          </h2>
          <p className="text-sm text-muted-foreground">
            Casos em que a classe sugerida pelo sistema merece a sua decisão. <b className="text-foreground">Aprovar</b> confirma a classe sugerida, registra no log e recalcula a fila.
          </p>
        </header>

        <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          {estado.tipo === "ok" && (
            <span>
              <b className="text-foreground tabular-nums">{estado.dados.total}</b> {estado.dados.total === 1 ? "caso" : "casos"} para revisar
            </span>
          )}
          <Button variant="outline" size="sm" className="ml-auto" onClick={recarregar} aria-label="Atualizar o inbox">
            <RefreshCw className={cn(estado.tipo === "ok" && estado.atualizando && "animate-spin")} aria-hidden /> Atualizar
          </Button>
        </div>

        {estado.tipo === "carregando" && (
          <div className="space-y-3" role="status" aria-live="polite">
            <span className="fx-loading-dots text-sm text-muted-foreground">Carregando o inbox</span>
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
        )}
        {estado.tipo === "erro" && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm" role="alert">
            <p className="flex items-center gap-2 font-semibold text-destructive">
              <AlertTriangle className="size-4" aria-hidden /> Não foi possível carregar o inbox
            </p>
            <p className="mt-1 text-muted-foreground">{estado.mensagem}</p>
            <p className="mt-2 text-muted-foreground">
              Confira se o back está no ar em <code className="rounded bg-muted px-1">{URL_API}</code> (com <code className="rounded bg-muted px-1">HP_USE_MOCKS=false</code>) e se a carga foi feita.
            </p>
            <Button variant="outline" size="sm" className="mt-3" onClick={recarregar}>
              <RefreshCw aria-hidden /> Tentar de novo
            </Button>
          </div>
        )}
        {estado.tipo === "ok" && itens.length === 0 && (
          <div className="rounded-xl bg-muted/40 p-8 text-center text-sm text-muted-foreground">Nada para revisar. Inbox vazio.</div>
        )}
        {estado.tipo === "ok" && itens.length > 0 && (
          <ul className={cn("space-y-3 transition-opacity", estado.atualizando && "opacity-60")} aria-label="Casos do inbox">
            {itens.map((item) => (
              <CartaoInbox key={item.solicitacao_id} item={item} aoDecidir={recarregar} />
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function CartaoInbox({ item, aoDecidir }: { item: ItemInbox; aoDecidir: () => void }) {
  const [enviando, setEnviando] = useState(false)

  async function aprovar() {
    setEnviando(true)
    try {
      const r = await aprovarProposta(item.solicitacao_id, usuarioAtual())
      const posicao =
        r.posicao_anterior !== null && r.posicao_nova !== null && r.posicao_anterior !== r.posicao_nova
          ? `Posição ${r.posicao_anterior} → ${r.posicao_nova}.`
          : r.posicao_nova !== null
            ? `Segue na posição ${r.posicao_nova}.`
            : ""
      if (r.fila_publicada) {
        toast.success(`${item.solicitacao_id} aprovada como ${item.classe_sugerida}`, { description: `${posicao} Fila recalculada e publicada.`.trim() })
      } else {
        toast.warning(`${item.solicitacao_id} aprovada, mas a fila não foi republicada`, {
          description: "A decisão ficou registrada; a fila anterior segue publicada até a próxima publicação válida.",
        })
      }
    } catch (e) {
      toast.error(`Não foi possível aprovar ${item.solicitacao_id}`, { description: e instanceof Error ? e.message : undefined })
    } finally {
      setEnviando(false)
      aoDecidir() // também no erro: um 409 significa que o caso já saiu do inbox
    }
  }

  return (
    <li className="rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm font-semibold">{item.solicitacao_id}</span>
        <Badge variant="outline">Camada {item.camada}</Badge>
        <span className="text-sm text-muted-foreground">{item.procedimento}</span>
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">{item.dias_em_fila} dias em fila</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Classe</span>
        <Badge variant="secondary">{item.classe_atual ?? "sem classe"}</Badge>
        <ArrowRight className="size-4 text-muted-foreground" aria-hidden />
        <Badge>{item.classe_sugerida}</Badge>
        {item.evento_gatilho && <span className="text-xs text-muted-foreground">gatilho: {item.evento_gatilho}</span>}
      </div>

      {item.editado_anteriormente && (
        <p className="mt-2 text-sm text-muted-foreground">
          Editado antes por <span className="font-mono">{item.editado_anteriormente.por}</span> em {formatarData(item.editado_anteriormente.em)}. Aprovar remove essa edição.
        </p>
      )}

      {item.motivos.length > 0 && (
        <ul className="mt-3 grid gap-2 @lg:grid-cols-2">
          {item.motivos.map((m, i) => (
            <li key={`${i}-${m.sinal}`} className="rounded-lg bg-muted/50 p-2.5 text-sm">
              <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">{m.sinal}</span>
                <span>{m.fonte}</span>
                {m.ref && <span className="font-mono">{m.ref}</span>}
                {m.data && <span>{formatarData(m.data)}</span>}
              </div>
              <p className="leading-snug">{m.evidencia}</p>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex items-center gap-2 border-t pt-3">
        <Button size="sm" onClick={aprovar} disabled={enviando}>
          <Check aria-hidden /> {enviando ? "Aprovando…" : `Aprovar ${item.classe_sugerida}`}
        </Button>
        <span className="ml-auto text-xs text-muted-foreground">por {usuarioAtual()}</span>
      </div>
    </li>
  )
}
