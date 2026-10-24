import { useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { resolverPendencia, type Pendencia, type Resolucao } from "@/api/cliente"
import { ACOES, acoesDaRegra, rotuloDesfecho } from "@/lib/pendencias"
import { usuarioAtual } from "@/lib/usuario"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

/** Duas duplicadas (PRE-20): as solicitações citadas na evidência, com o texto "entrada em ..., CID ...". */
const duplicadas = (p: Pendencia) => p.evidencias.filter((e) => e.fonte === "solicitacao" && e.ref)

export function AcoesPendencia({ pendencia: p, aoResolver }: { pendencia: Pendencia; aoResolver: () => void }) {
  const acoes = acoesDaRegra(p.regra)
  const [escolhida, setEscolhida] = useState<Resolucao | null>(null)
  const [observacao, setObservacao] = useState("")
  const opcoes = duplicadas(p)
  // por padrão fica a outra duplicada (a mais antiga): a mais nova é a que a pendência suspendeu
  const [permanece, setPermanece] = useState(() => opcoes.find((e) => e.ref !== p.solicitacao_id)?.ref ?? opcoes[0]?.ref ?? "")
  const [enviando, setEnviando] = useState(false)

  if (acoes.length === 0) return null
  const acao = escolhida ? ACOES[escolhida] : null
  const faltaObservacao = !!acao?.exigeObservacao && observacao.trim() === ""
  const rotuloPermanece = Object.fromEntries(opcoes.map((e) => [e.ref ?? "", e.texto]))

  const cancelar = () => {
    setEscolhida(null)
    setObservacao("")
  }

  const confirmar = async () => {
    if (!escolhida || faltaObservacao) return
    setEnviando(true)
    try {
      const r = await resolverPendencia(p.pendencia_id, {
        resolucao: escolhida,
        usuario_id: usuarioAtual(),
        observacao: observacao.trim() || null,
        fundir_com: escolhida === "fundir" ? permanece : null,
      })
      const desfecho = rotuloDesfecho(r.status_fila)
      if (r.fila_publicada) {
        toast.success(`${p.pendencia_id} resolvida`, { description: `${desfecho} Fila recalculada e publicada.`.trim() })
      } else {
        toast.warning(`${p.pendencia_id} resolvida, mas a fila não foi republicada`, {
          description: `${desfecho} O verificador reprovou ou houve falha: a fila anterior segue valendo.`.trim(),
          duration: 10000,
        })
      }
      cancelar()
      aoResolver()
    } catch (e) {
      toast.error(`Não foi possível resolver ${p.pendencia_id}`, { description: e instanceof Error ? e.message : undefined })
      if (e instanceof Error && "status" in e && e.status === 409) aoResolver() // alguém resolveu antes: atualiza a lista
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="mt-3 border-t pt-3">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Resolver ${p.pendencia_id}`}>
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Resolver</span>
        {acoes.map((a) => (
          <Button
            key={a.resolucao}
            size="sm"
            variant={escolhida === a.resolucao ? "default" : "outline"}
            aria-pressed={escolhida === a.resolucao}
            disabled={enviando}
            onClick={() => (escolhida === a.resolucao ? cancelar() : setEscolhida(a.resolucao))}
          >
            <a.icone aria-hidden /> {a.rotulo}
          </Button>
        ))}
      </div>

      {acao && escolhida && (
        <div className="fx-fade-up mt-3 space-y-2 rounded-lg bg-muted/50 p-3">
          <p className="text-sm">{acao.dica(p.regra)}</p>

          {escolhida === "fundir" && opcoes.length > 1 && (
            <label className="block text-sm">
              <span className="mb-1 block text-xs font-medium text-muted-foreground">Qual solicitação permanece</span>
              <Select items={rotuloPermanece} value={permanece} onValueChange={(v) => setPermanece(v ?? permanece)}>
                <SelectTrigger size="sm" className="w-full max-w-xl" aria-label="Solicitação que permanece">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {opcoes.map((e) => (
                    <SelectItem key={e.ref} value={e.ref ?? ""}>
                      {e.texto}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
          )}

          <label className="block text-sm">
            <span className="mb-1 block text-xs font-medium text-muted-foreground">
              Observação {acao.exigeObservacao ? <b className="text-destructive">(obrigatória)</b> : "(opcional)"}
            </span>
            <Textarea
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              placeholder={acao.exigeObservacao ? "Ex.: confirmado por telefone com a família" : "Ex.: contato atualizado"}
              aria-invalid={faltaObservacao && observacao.length > 0}
              disabled={enviando}
              className="min-h-14 max-w-xl"
            />
          </label>

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={confirmar} disabled={enviando || faltaObservacao}>
              {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <Check aria-hidden />} {acao.resolucao === "confirmar_saida" ? "Confirmar a saída" : `${acao.rotulo}: confirmar`}
            </Button>
            <Button size="sm" variant="ghost" onClick={cancelar} disabled={enviando}>
              Cancelar
            </Button>
            <span className="ml-auto text-xs text-muted-foreground">por {usuarioAtual()}</span>
          </div>
        </div>
      )}
    </div>
  )
}
