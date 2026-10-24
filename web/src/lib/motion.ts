import { useEffect, useRef, useState } from "react"

export const useContagem = (alvo: number, duracao = 700) => {
  const [valor, setValor] = useState(alvo)
  const anterior = useRef(alvo)
  useEffect(() => {
    const inicio = anterior.current
    const t0 = performance.now()
    let quadro = 0
    const passo = (agora: number) => {
      const t = Math.min(1, (agora - t0) / duracao)
      const suave = 1 - Math.pow(1 - t, 3)
      setValor(inicio + (alvo - inicio) * suave)
      if (t < 1) quadro = requestAnimationFrame(passo)
      else anterior.current = alvo
    }
    quadro = requestAnimationFrame(passo)
    return () => {
      cancelAnimationFrame(quadro)
      anterior.current = alvo
    }
  }, [alvo, duracao])
  return valor
}
