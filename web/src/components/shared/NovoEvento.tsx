import { useState } from "react"
import { toast } from "sonner"
import { CalendarPlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { ORIGEM_DADOS } from "@/data/fila"
import { ErroApi, registrarEvento } from "@/lib/api"
import { useStore } from "@/store/useStore"

// Tipos e resultados do dataset (docs/dicionario_dados.md).
const RESULTADOS: Record<string, string[]> = {
  pronto_socorro: ["atendido_liberado", "observacao"],
  internacao: ["alta"],
  biopsia: ["positivo", "negativo", "inconclusivo"],
  exame_imagem: ["estavel", "progressao"],
  consulta_reavaliacao: ["piora", "estavel"],
  contato_telefonico: ["atendeu", "nao_atendeu", "relata_piora", "relata_melhora", "desistiu", "informou_cirurgia_outro_servico"],
  falta: ["consulta", "exame", "avaliacao_pre_anestesica"],
}
const TIPOS: Record<string, string> = Object.fromEntries(Object.keys(RESULTADOS).map((t) => [t, t.replaceAll("_", " ")]))

const DESFECHO = {
  enviado_inbox: "Classe mudou: enviado ao inbox do regulador (a fila só muda após aprovação)",
  pendencia: "Indica saída da fila: pendência aberta para o call center",
  registrado: "Registrado (classe não mudou)",
}

export function NovoEvento({ solicitacaoId }: { solicitacaoId: string }) {
  const recarregar = useStore((s) => s.recarregar)
  const selecionar = useStore((s) => s.selecionar)
  const [aberto, setAberto] = useState(false)
  const [tipo, setTipo] = useState("pronto_socorro")
  const [resultado, setResultado] = useState(RESULTADOS.pronto_socorro[0])
  const [data, setData] = useState("2026-10-23")
  const [descricao, setDescricao] = useState("")
  const [enviando, setEnviando] = useState(false)

  if (ORIGEM_DADOS !== "api") return null

  const enviar = async () => {
    setEnviando(true)
    try {
      const r = await registrarEvento({ solicitacao_id: solicitacaoId, data_evento: data, tipo_evento: tipo, resultado, descricao, origem: "front" })
      setAberto(false)
      setDescricao("")
      await recarregar()
      selecionar(solicitacaoId)
      const classes = r.classe_antes && r.classe_depois ? ` · SWALIS ${r.classe_antes} → ${r.classe_depois}` : ""
      toast.success(`Evento ${r.evento_id} registrado`, { description: `${DESFECHO[r.desfecho]}${classes}${r.pendencia_id ? ` · ${r.pendencia_id}` : ""}` })
    } catch (e) {
      toast.error("Evento recusado", { description: e instanceof ErroApi ? `${e.codigo}: ${e.message}` : String(e) })
    } finally {
      setEnviando(false)
    }
  }

  const itensResultado = Object.fromEntries(RESULTADOS[tipo].map((r) => [r, r.replaceAll("_", " ")]))

  return (
    <>
      <Button variant="outline" size="sm" className="w-full gap-1.5" onClick={() => setAberto(true)}>
        <CalendarPlus aria-hidden /> Registrar evento
      </Button>
      <Dialog open={aberto} onOpenChange={setAberto}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Novo evento · {solicitacaoId}</DialogTitle>
            <DialogDescription>O sistema reavalia o paciente; mudança de classe vai ao inbox para um profissional aprovar.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <label className="block space-y-1 text-xs text-muted-foreground">
              Tipo
              <Select
                items={TIPOS}
                value={tipo}
                onValueChange={(v) => {
                  const t = (v as string) ?? "pronto_socorro"
                  setTipo(t)
                  setResultado(RESULTADOS[t][0])
                }}
              >
                <SelectTrigger size="sm" className="w-full text-foreground" aria-label="Tipo de evento">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TIPOS).map(([v, r]) => (
                    <SelectItem key={v} value={v}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <label className="block space-y-1 text-xs text-muted-foreground">
              Resultado
              <Select items={itensResultado} value={resultado} onValueChange={(v) => setResultado((v as string) ?? resultado)}>
                <SelectTrigger size="sm" className="w-full text-foreground" aria-label="Resultado do evento">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(itensResultado).map(([v, r]) => (
                    <SelectItem key={v} value={v}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <label className="block space-y-1 text-xs text-muted-foreground">
              Data do evento
              <Input type="date" value={data} onChange={(e) => setData(e.target.value)} aria-label="Data do evento" />
            </label>
            <label className="block space-y-1 text-xs text-muted-foreground">
              Descrição
              <Textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} rows={2} placeholder="Ex.: AP: adenocarcinoma" aria-label="Descrição do evento" />
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAberto(false)}>
              Cancelar
            </Button>
            <Button onClick={enviar} disabled={enviando}>
              {enviando ? "Enviando…" : "Registrar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
