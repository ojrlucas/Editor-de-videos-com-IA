"""Roteiro, janelas de tempo e palavras-chave (fatos conferidos em SOURCES.md)."""
FPS = 30
DURATION = 25.0
# (id, inicio_s, fim_s, texto, palavras_destaque)
SEGMENTS = [
    ("hook",    0.15,  2.90, "A Rockstar acabou de surpreender os fãs!", {"rockstar", "surpreender"}),
    ("context", 3.10,  7.90, "São trinta e sete imagens inéditas de GTA 6, liberadas a duas semanas do lançamento.", {"trinta", "sete", "inéditas", "gta", "6,"}),
    ("reveal",  8.10, 15.80, "Vice City em festas lotadas, perseguições policiais e os protagonistas Jason e Lucia, em closes cheios de detalhes.", {"vice", "city", "jason", "lucia,", "detalhes."}),
    ("impact", 16.10, 20.90, "E um detalhe chamou atenção: Jason de moto na chuva, sem capacete.", {"detalhe", "sem", "capacete."}),
    ("outro",  21.10, 24.80, "Qual dessas imagens te convenceu? Conta nos comentários!", {"qual", "convenceu?", "comentários!"}),
]
