"""NexoBot Advanced — assistente de navegação e suporte do portal NEXO.

Camadas (ver Docs/NEXOBOT_ADVANCED.md):
  A. normalizacao  — texto defensivo, abreviações, erros de digitação, citações
  B. classificacao — intenções por evidências e conflitos explícitos
  C. conhecimento  — busca BM25 no Guia (GuiaTopico) + fatos do portal
  D. contexto      — memória mínima da conversa, validada a cada mensagem
  E. servico       — decisão, resposta e única ação autorizada (catálogo fechado)
Apoio: navegacao (catálogo), seguranca, respostas, providers (IA opcional).
"""

from .servico import responder

__all__ = ["responder"]
