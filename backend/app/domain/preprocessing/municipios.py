"""Nomes oficiais (IBGE) dos 38 municípios do dataset, para PRE-03 (D-19).

Um teste garante que nenhum valor de fila_cirurgica.csv fica de fora.
"""
from __future__ import annotations

from app.domain.preprocessing.normalizacao import normalizar_nome

_NOMES = [
    "Alegrete", "Alvorada", "Bagé", "Cachoeira do Sul", "Cachoeirinha", "Camaquã",
    "Canoas", "Caxias do Sul", "Charqueadas", "Cruz Alta", "Eldorado do Sul", "Erechim",
    "Esteio", "Gravataí", "Guaíba", "Ijuí", "Lajeado", "Montenegro", "Novo Hamburgo",
    "Osório", "Passo Fundo", "Pelotas", "Porto Alegre", "Rio Grande", "Santa Cruz do Sul",
    "Santa Maria", "Santa Rosa", "Santana do Livramento", "Santo Ângelo", "São Borja",
    "São Gabriel", "São Leopoldo", "Sapucaia do Sul", "Taquara", "Torres", "Tramandaí",
    "Uruguaiana", "Viamão",
]

# chave de busca (sem acento, minúsculo) -> nome oficial
MUNICIPIOS_OFICIAIS: dict[str, str] = {normalizar_nome(n): n for n in _NOMES}
