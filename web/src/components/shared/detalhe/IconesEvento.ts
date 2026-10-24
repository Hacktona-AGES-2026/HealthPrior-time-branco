import { Ambulance, BedDouble, CalendarX, Droplet, FileSearch, LogIn, Microscope, Phone, Stethoscope, type LucideIcon } from "lucide-react"
import type { TipoEvento } from "@/data/tipos"

export const ICONE_EVENTO: Record<TipoEvento, LucideIcon> = {
  entrada: LogIn,
  pronto_socorro: Ambulance,
  internacao: BedDouble,
  biopsia: Microscope,
  exame_imagem: FileSearch,
  consulta_reavaliacao: Stethoscope,
  hba1c: Droplet,
  falta: CalendarX,
  contato_telefonico: Phone,
}

export const ROTULO_EVENTO_TIPO: Record<TipoEvento, string> = {
  entrada: "Entrada",
  pronto_socorro: "Pronto-socorro",
  internacao: "Internação",
  biopsia: "Biópsia",
  exame_imagem: "Exame de imagem",
  consulta_reavaliacao: "Reavaliação",
  hba1c: "HbA1c",
  falta: "Falta",
  contato_telefonico: "Contato telefônico",
}

export const COR_EVENTO: Record<TipoEvento, string> = {
  entrada: "var(--primary)",
  pronto_socorro: "var(--desce)",
  internacao: "var(--cls-a2)",
  biopsia: "oklch(0.62 0.15 300)",
  exame_imagem: "var(--cls-c)",
  consulta_reavaliacao: "var(--sobe)",
  hba1c: "var(--prazo-limite)",
  falta: "var(--muted-foreground)",
  contato_telefonico: "var(--muted-foreground)",
}
