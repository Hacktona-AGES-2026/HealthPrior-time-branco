import { useState } from "react"
import { AlertTriangle, ArrowRight, Check, Inbox as IconeInbox, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { aprovarProposta, URL_API, type ItemInbox } from "@/api/cliente"
import { formatarData } from "@/lib/datas"
import { reguladorAtual } from "@/lib/usuario"
import { useStore } from "@/store/useStore"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { frasePrazo, motivosDoInbox } from "./motivosInbox"
import { useInbox } from "./useInbox"

export default function PaginaInbox() {
  const { estado, recarregar } = useInbox()
  const itens = estado.tipo === "ok" ? estado.dados.itens : []

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-5xl space-y-4 p-4">
        <header className="fx-fade-up space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <IconeInbox className="size-4" aria-hidden /> Casos para revisar
          </h2>
          <p className="text-sm text-muted-foreground">
            Casos em que a classe sugerida merece a sua decisão. <b className="text-foreground">Aprovar</b> confirma a classe e atualiza a fila.
          </p>
        </header>

        <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          {estado.tipo === "ok" && (
            <span>
              <b className="text-foreground tabular-nums">{estado.dados.total}</b> {estado.dados.total === 1 ? "caso" : "casos"} para revisar
            </span>
          )}
          <Button variant="outline" size="sm" className="ml-auto h-9 lg:h-7" onClick={recarregar} aria-label="Atualizar a lista">
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
      const r = await aprovarProposta(item.solicitacao_id, reguladorAtual())
      const posicao =
        r.posicao_anterior !== null && r.posicao_nova !== null && r.posicao_anterior !== r.posicao_nova
          ? `Posição ${r.posicao_anterior} → ${r.posicao_nova}.`
          : r.posicao_nova !== null
            ? `Segue na posição ${r.posicao_nova}.`
            : ""
      if (r.fila_publicada) {
        toast.success(`${item.solicitacao_id} aprovada como ${item.classe_sugerida}`, { description: `${posicao} Fila recalculada e publicada.`.trim() })
        void useStore.getState().recarregar()  // a fila do front acompanha a nova publicação
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

  const { frases, trecho } = motivosDoInbox(item)
  const previa = item.previa
  const de = previa?.posicao_atual
  const para = previa?.posicao_estimada

  return (
    <li className="rounded-xl border bg-card p-3 sm:p-4">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-mono text-sm font-semibold">{item.solicitacao_id}</span>
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">{item.dias_em_fila} dias em fila</span>
      </div>
      <p className="mt-0.5 text-sm text-muted-foreground">{item.procedimento}</p>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Classe</span>
        <Badge variant="secondary">{item.classe_atual ?? "sem classe"}</Badge>
        <ArrowRight className="size-4 text-muted-foreground" aria-hidden />
        <Badge>{item.classe_sugerida}</Badge>
      </div>

      {previa && (
        <p className="mt-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Se aprovar {item.classe_sugerida}:</span>{" "}
          {para == null ? (
            "sai da fila publicada"
          ) : (
            <>
              posição {de ?? "—"} → <span className="font-semibold tabular-nums text-foreground">{para}</span>
              {de === para && " (sem mudança)"}
            </>
          )}{" "}
          · {frasePrazo(previa.pct_prazo_consumido)}
        </p>
      )}

      {item.editado_anteriormente && (
        <p className="mt-2 text-xs text-muted-foreground">
          Editado antes por {item.editado_anteriormente.por} em {formatarData(item.editado_anteriormente.em)}. Aprovar remove essa edição.
        </p>
      )}

      {(frases.length > 0 || trecho) && (
        <div className="mt-2 space-y-1.5">
          {frases.length > 0 && (
            <ul className="flex flex-wrap gap-1.5" aria-label="Por que está aqui">
              {frases.map((f) => (
                <li key={f} className="rounded-md bg-muted px-2 py-1 text-xs leading-tight">
                  {f}
                </li>
              ))}
            </ul>
          )}
          {trecho && <TrechoLongo texto={trecho} />}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
        <Button className="h-9 lg:h-7" size="sm" onClick={aprovar} disabled={enviando}>
          <Check aria-hidden /> {enviando ? "Aprovando…" : `Aprovar ${item.classe_sugerida}`}
        </Button>
        <Button className="h-9 lg:h-7" size="sm" variant="outline" onClick={() => useStore.getState().abrirNaFila(item.solicitacao_id)}>
          Abrir na fila
        </Button>
      </div>
    </li>
  )
}

function TrechoLongo({ texto }: { texto: string }) {
  const [aberto, setAberto] = useState(false)
  const longo = texto.length > 90
  return (
    <p className="text-xs text-muted-foreground">
      <span className={cn("italic", longo && !aberto && "line-clamp-2")}>“{texto}”</span>
      {longo && (
        <button type="button" className="-my-2 inline-flex min-h-9 items-center py-2 text-xs font-medium text-foreground underline lg:min-h-0 lg:py-0" onClick={() => setAberto((v) => !v)}>
          {aberto ? "Ler menos" : "Ler mais"}
        </button>
      )}
    </p>
  )
}
