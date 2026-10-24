import { useRef, useState } from "react"
import { AlertTriangle, CheckCircle2, Download, FileUp, Loader2, Upload } from "lucide-react"
import { toast } from "sonner"
import { importarSolicitacoes, URL_MODELO_CSV, type ResultadoImportacao } from "@/api/cliente"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

const TAMANHO_MAX = 2 * 1024 * 1024

type Mostrado = { ok: boolean; dados: ResultadoImportacao }
// Depois de importar, a fila é recarregada e a página remonta (key por versaoDados): o resultado fica aqui para sobreviver.
let ultimoResultado: Mostrado | null = null

export default function PaginaImportar() {
  const [texto, setTexto] = useState("")
  const [arquivo, setArquivo] = useState<string | null>(null)
  const [publicar, setPublicar] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultadoLocal] = useState<Mostrado | null>(ultimoResultado)
  const setResultado = (r: Mostrado | null) => {
    ultimoResultado = r
    setResultadoLocal(r)
  }
  const [arrastando, setArrastando] = useState(false)
  const entrada = useRef<HTMLInputElement>(null)
  const recarregar = useStore((s) => s.recarregar)
  const ir = useStore((s) => s.ir)

  const linhas = texto.split(/\r?\n/).filter((l) => l.trim() !== "").length
  const registros = Math.max(linhas - 1, 0)

  async function lerArquivo(f: File | undefined) {
    if (!f) return
    if (f.size > TAMANHO_MAX) {
      toast.error("Arquivo maior que 2 MB", { description: "Divida em partes menores." })
      return
    }
    setTexto(await f.text())
    setArquivo(f.name)
    setResultado(null)
  }

  async function enviar() {
    setEnviando(true)
    try {
      const r = await importarSolicitacoes(texto, publicar)
      setResultado({ ok: r.ok, dados: r.resultado })
      if (r.ok && r.resultado.novas > 0) {
        setTexto("")
        setArquivo(null)
        toast.success(`${r.resultado.novas} ${r.resultado.novas === 1 ? "solicitação importada" : "solicitações importadas"}`, {
          description: r.resultado.fila_publicada ? "Fila recalculada e publicada." : undefined,
        })
        await recarregar() // a fila e o inbox passam a mostrar as novas
      } else if (!r.ok) {
        toast.error("Nada foi importado", { description: "Corrija os erros abaixo e envie de novo." })
      }
    } catch (e) {
      toast.error("Não foi possível importar", { description: e instanceof Error ? e.message : undefined })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-4xl space-y-4 p-4">
        <header className="fx-fade-up space-y-1">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <FileUp className="size-4" aria-hidden /> Importar solicitações
          </h2>
          <p className="text-sm text-muted-foreground">
            Envie um CSV com <b className="text-foreground">uma linha ou várias</b> solicitações novas. Elas passam pelo mesmo caminho da carga: normalização, alertas, pendências e
            suspensão, e a fila é recalculada e verificada. Quem já existe é ignorado (nunca sobrescrito) e, se houver qualquer erro, <b className="text-foreground">nada é gravado</b>.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" render={<a href={URL_MODELO_CSV} download />}>
            <Download aria-hidden /> Baixar modelo
          </Button>
          <span className="text-xs text-muted-foreground">
            Obrigatórias: solicitacao_id, paciente_id, nome_paciente, procedimento_id, cid_principal, data_entrada_fila. Aceita vírgula ou ponto e vírgula.
          </span>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setArrastando(true) }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => { e.preventDefault(); setArrastando(false); void lerArquivo(e.dataTransfer.files[0]) }}
          className={cn("rounded-xl border border-dashed p-6 text-center text-sm transition-colors", arrastando ? "border-primary bg-primary/5" : "bg-muted/30")}
        >
          <Upload className="mx-auto mb-2 size-5 text-muted-foreground" aria-hidden />
          <p>
            Arraste o arquivo aqui ou{" "}
            <button type="button" className="font-medium text-primary underline underline-offset-2" onClick={() => entrada.current?.click()}>
              escolha um CSV
            </button>
          </p>
          <input ref={entrada} type="file" accept=".csv,text/csv" className="sr-only" aria-label="Escolher arquivo CSV" onChange={(e) => void lerArquivo(e.target.files?.[0])} />
          {arquivo && <p className="mt-2 text-xs text-muted-foreground">{arquivo}</p>}
        </div>

        <div className="space-y-1.5">
          <label htmlFor="csv-colado" className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Ou cole o CSV (cabeçalho + linhas)</label>
          <Textarea id="csv-colado" value={texto} onChange={(e) => { setTexto(e.target.value); setArquivo(null); setResultado(null) }} rows={6} className="font-mono text-xs" placeholder="solicitacao_id,paciente_id,nome_paciente,procedimento_id,cid_principal,data_entrada_fila&#10;SOL-2026-90001,PAC-90001,Maria Exemplo,PROC004,K80.2,2026-10-01" />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={enviar} disabled={enviando || registros === 0}>
            {enviando ? <Loader2 className="animate-spin" aria-hidden /> : <FileUp aria-hidden />} Importar {registros > 0 ? `${registros} ${registros === 1 ? "linha" : "linhas"}` : ""}
          </Button>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publicar} onChange={(e) => setPublicar(e.target.checked)} /> Republicar a fila depois de importar
          </label>
        </div>

        {resultado && <Resultado ok={resultado.ok} r={resultado.dados} aoVerFila={() => ir("fila")} />}
      </div>
    </div>
  )
}

function Resultado({ ok, r, aoVerFila }: { ok: boolean; r: ResultadoImportacao; aoVerFila: () => void }) {
  return (
    <section className={cn("space-y-3 rounded-xl border p-4 text-sm", ok ? "border-primary/30" : "border-destructive/40 bg-destructive/5")} aria-live="polite">
      <h3 className="flex items-center gap-2 font-semibold">
        {ok ? <CheckCircle2 className="size-4 text-primary" aria-hidden /> : <AlertTriangle className="size-4 text-destructive" aria-hidden />}
        {ok ? (r.novas > 0 ? "Importação concluída" : "Nada novo para importar") : "Nada foi importado: há erros no arquivo"}
      </h3>
      <div className="flex flex-wrap gap-2">
        <Badge variant="outline">{r.lidas} lidas</Badge>
        <Badge variant={r.novas > 0 ? "default" : "secondary"}>{r.novas} novas</Badge>
        {r.ja_existentes.length > 0 && <Badge variant="secondary">{r.ja_existentes.length} já existiam (ignoradas)</Badge>}
        {r.suspensas > 0 && <Badge variant="destructive">{r.suspensas} entraram suspensas (pendência bloqueante)</Badge>}
        {r.fila_publicada === true && <Badge variant="outline">fila republicada: {r.total_fila} na fila</Badge>}
        {r.fila_publicada === false && <Badge variant="destructive">fila não republicada (a anterior segue valendo)</Badge>}
      </div>
      {r.novas_ids.length > 0 && <p className="text-xs text-muted-foreground">Novas: <span className="font-mono">{r.novas_ids.slice(0, 10).join(", ")}{r.novas > 10 ? "…" : ""}</span></p>}
      {r.ja_existentes.length > 0 && <p className="text-xs text-muted-foreground">Já existiam: <span className="font-mono">{r.ja_existentes.slice(0, 10).join(", ")}{r.ja_existentes.length > 10 ? "…" : ""}</span></p>}
      {r.erros.length > 0 && (
        <table className="w-full text-left text-xs">
          <thead className="text-muted-foreground"><tr><th className="py-1 pr-3 font-medium">Linha</th><th className="py-1 pr-3 font-medium">Campo</th><th className="py-1 font-medium">Problema</th></tr></thead>
          <tbody>
            {r.erros.map((e, i) => (
              <tr key={i} className="border-t"><td className="py-1 pr-3 tabular-nums">{e.linha === 1 ? "cabeçalho" : e.linha}</td><td className="py-1 pr-3 font-mono">{e.campo ?? ""}</td><td className="py-1">{e.mensagem}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {ok && r.novas > 0 && <Button variant="outline" size="sm" onClick={aoVerFila}>Ver na fila</Button>}
    </section>
  )
}
