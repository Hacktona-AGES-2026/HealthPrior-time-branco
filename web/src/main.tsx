import { StrictMode, createElement } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"

const iniciar = async () => {
  const raiz = createRoot(document.getElementById("root")!)
  const { carregarFila } = await import("@/data/fila")
  let falha: unknown = null
  try {
    await carregarFila()
  } catch (e) {
    falha = e
  }
  const { iniciarPersistencia } = await import("@/lib/persistencia")
  iniciarPersistencia()
  const { default: App } = await import("./App.tsx")
  raiz.render(createElement(StrictMode, null, createElement(App)))
  if (falha) {
    const { toast } = await import("sonner")
    const { API_URL } = await import("@/lib/api")
    setTimeout(() => toast.warning("API indisponível: usando os dados dos CSVs (somente leitura)", { description: `${API_URL} (${String(falha)})`, duration: 10000 }), 500)
  }
}

void iniciar()
