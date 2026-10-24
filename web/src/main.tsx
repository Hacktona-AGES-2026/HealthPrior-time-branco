import { StrictMode, createElement } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"

// Carrega a fila da API antes de montar o app (o store nasce com as decisões já gravadas).
// Sem API, cai no mock e avisa.
const iniciar = async () => {
  const raiz = createRoot(document.getElementById("root")!)
  const { carregarFila, usarMock } = await import("@/data/fila")
  let falha: unknown = null
  try {
    await carregarFila()
  } catch (e) {
    falha = e
    usarMock()
  }
  const { default: App } = await import("./App.tsx")
  raiz.render(createElement(StrictMode, null, createElement(App)))
  if (falha) {
    const { toast } = await import("sonner")
    const { API_URL } = await import("@/lib/api")
    setTimeout(() => toast.warning("API indisponível: usando dados de exemplo", { description: `${API_URL} (${String(falha)})`, duration: 10000 }), 500)
  }
}

void iniciar()
