# NEXO-COM-002 — Avaliações e depoimentos

**Situação: PLANEJADA, NÃO IMPLEMENTADA.** Registro de requisitos em 24/10/2026
(America/Sao_Paulo). A COM-001 prepara a apresentação da landing, sem criar
sistema de avaliações, tabelas, migrações ou gatilho de 60 dias.

## O que a COM-001 entrega

- Carrossel reutilizável em `templates/landing.html`, `static/js/landing.js` e
  `static/css/landing.css`, com anterior/próximo, indicadores, operação por
  teclado, transição curta e respeito à preferência de movimento reduzido.
- Estado vazio explícito quando não há depoimentos reais autorizados. Não há
  avaliações publicadas, empresa ou resultado financeiro inventado.
- Botão “Deixar Avaliação” desabilitado, acompanhado da informação de que o envio
  ainda não está disponível. Não encaminha ao login prometendo formulário inexistente.
- Contrato de apresentação opcional `landing_reviews`: o template considera
  `approved` e `publication_consent` e escapa `quote`, `author` e `company`.
  A rota atual não fornece uma coleção real de avaliações.

Essa filtragem de template não substitui controles de autorização ou consentimento
no backend futuro. Nenhum dado privado deverá chegar ao contexto da landing.
Os exemplos utilizados nos testes existem apenas durante a execução dos testes.
Alternatintas é uma possibilidade de case mencionada pelo proprietário, sem
conteúdo ou autorização verificável para publicação nesta entrega.

## Fluxo a implementar na COM-002

1. Cliente autenticado e elegível recebe solicitação de avaliação após 60 dias
   de uso ativo. A notificação deve permitir fechar ou adiar e não bloquear o portal.
2. Formulário acessível contém nota obrigatória de 1 a 5 estrelas, comentário
   destinado à publicação e campo separado de sugestão privada.
3. Explicar antes do envio quais dados poderão ser públicos, quem acessará a
   sugestão privada e qual será a finalidade do tratamento. Não prometer anonimato
   se houver associação identificável à conta ou empresa.
4. Consentimento de publicação explícito e separado, sem caixa pré-marcada nem
   condicionamento do serviço. Identificação do autor/empresa, marca e eventual
   citação de resultados exigem autorização correspondente e verificável.
5. Avaliação enviada permanece privada e pendente. A equipe autorizada visualiza,
   aprova ou rejeita a publicação. Aprovação não substitui consentimento.
6. Somente conteúdo aprovado, com consentimento válido e sem revogação, integra
   o carrossel público. Não publicar automaticamente por atingir nota mínima.
7. Sugestão privada fica disponível à equipe autorizada em área integrada ao
   suporte. Nunca deve ser copiada automaticamente para comentário público.

## Definição de “60 dias de uso ativo” pendente

A COM-002 deve definir e documentar a regra antes da implementação: evento inicial,
contagem de atividade, períodos de suspensão/cancelamento ou lixeira, fuso horário,
elegibilidade por usuário ou empresa e intervalo entre novos pedidos.
`criado_em`, ausência de login ou permanência de um cookie não comprovam, por si,
60 dias de uso ativo. Não inferir histórico inexistente nem habilitar o gatilho
para todos os clientes legados sem uma política aprovada.

A regra precisa ser persistente e idempotente, funcionar após reinício e impedir
solicitações duplicadas em abas, processos e requisições concorrentes. Adiamento,
recusa, envio e revogação de consentimento devem ter tratamento explícito.

## Administração e moderação

- Acesso restrito ao papel administrativo já autorizado, com verificação no
  servidor em cada operação de consulta, aprovação, rejeição e retirada.
- Listas separadas de pendentes, aprovadas/publicadas e rejeitadas/retiradas;
  visualizar nota, comentário e consentimento sem expor sugestões no conteúdo público.
- Não alterar silenciosamente o sentido de uma avaliação. Mudança material de
  texto ou identificação exige nova revisão e, quando aplicável, nova autorização.
- Registrar de forma proporcional a autoria administrativa, decisão e data para
  auditoria. Não armazenar tokens, credenciais ou conteúdo privado em logs públicos.
- Aprovação, retirada e alteração de consentimento devem ser transacionais;
  uma publicação concorrente não pode restaurar conteúdo já retirado.
- Definir limites de tamanho, frequência e duplicidade. Renderizar texto com
  escape, sem HTML/JavaScript fornecido pelo usuário e sem links ativos arbitrários.

## Privacidade, consentimento e LGPD

Documentos e avisos deverão ser revisados pelo responsável antes de disponibilizar
o fluxo real. Este planejamento não constitui política jurídica publicada.

- Minimizar dados: não pedir documentos, dados financeiros de clientes ou dados
  sensíveis para deixar uma avaliação. Orientar o cliente a não incluí-los no texto.
- Separar autorização de publicar nome, empresa, marca e comentário do acesso ao
  serviço. Não usar a sugestão privada como consentimento de publicidade.
- Registrar evidência suficiente da versão do aviso, finalidade, manifestação,
  data e escopo do consentimento, com acesso restrito e retenção definida.
- Oferecer canal funcional para retirar autorização e corrigir identificação.
  A revogação deve retirar a publicação e invalidar caches que a exibam, conforme
  procedimento e prazo aprovados; não afirmar remoção de cópias de terceiros.
- Definir retenção e descarte de avaliações rejeitadas, sugestões e evidências,
  inclusive tratamento em backups, exportação e exclusão de empresa/usuário.
- Revisar o uso de nomes, marcas e resultados: consentimento não comprova a
  veracidade de uma alegação financeira. Não criar promessa de resultado garantido.

## Isolamento entre empresas e segurança

- Cliente pode consultar ou modificar somente registros permitidos da própria
  empresa. Derivar a empresa da sessão/usuário no banco, sem confiar em IDs enviados
  pelo navegador; testar troca de IDs e acesso direto a endpoints.
- Autenticação, sessões revogadas, primeiro acesso e empresa na lixeira devem
  continuar sujeitos às SEC-002/003/004. Não criar exceção de autorização para avaliar.
- Todas as operações de alteração exigem método apropriado, CSRF válido e validação
  no servidor. GET não deve enviar, aprovar ou retirar avaliações.
- Sugestões privadas permanecem no suporte autenticado; não enviar em contexto
  público, APIs públicas, salas Socket.IO compartilhadas, métricas ou logs.
- Reutilizar autorização pelo banco e salas privadas existentes em eventual
  notificação. Não permitir leitura cruzada entre empresas ou contas revogadas.
- Aplicar limites de entrada e frequência compatíveis com os mecanismos existentes;
  validar concorrência e evitar cópias não autorizadas em buscas e exportações.

## Integração futura com a landing

O backend da COM-002 deverá construir um DTO público mínimo e verificado para
`landing_reviews`, contendo somente texto e identificação cuja publicação seja
permitida. Excluir sugestões, e-mail, IDs internos e metadados de moderação.
A seleção deve consultar aprovação e consentimento vigentes no banco; o template
é defesa complementar. Definir política de cache e retirada antes de publicar.

Ativar “Deixar Avaliação” apenas depois de existir um destino funcional autenticado.
Após autenticar, preservar a política de redirecionamento seguro e verificar
a elegibilidade no servidor. Não permitir que parâmetros de retorno causem
redirecionamento aberto ou contornem a autorização.

## Critérios de aceitação da COM-002

- Testes de elegibilidade nos limites de 59/60/61 dias com relógio controlado,
  contas legadas, períodos inativos e regra aprovada de uso ativo.
- Estrelas operáveis por teclado e leitor de tela, rótulos e erros acessíveis,
  foco controlado no pop-up e opção de fechar sem prejudicar uso do portal.
- Nota limitada a 1–5 e campos limitados/validados; textos potencialmente maliciosos
  nunca executados no portal, administração ou landing.
- Testes de autorização, CSRF, sessões antigas, empresas distintas e permissões
  administrativas em todas as operações; sugestões ausentes de respostas públicas.
- Consentimento ausente ou revogado impede publicação, mesmo após aprovação;
  rejeição e retirada permanecem efetivas sob concorrência e cache.
- Nenhuma empresa, nome, logo ou depoimento publicado sem conteúdo e autorização
  verificáveis. Testes sintéticos não devem abastecer o ambiente real.
- Migração futura, se necessária, revisada e validada em bancos descartáveis,
  sem assumir autorização para executar em Supabase de produção.
- Publicação em branch e PR próprias, regressão completa e GitHub Actions verificado,
  sem merge/deploy automático. Liberação depende de revisão específica do proprietário.

## Dependências de conteúdo e decisão

Permanecem pendentes: regra de uso ativo; avisos e documentos jurídicos revisados;
responsáveis pela moderação/suporte; política de retenção e retirada; canal para
solicitações de privacidade; primeiros depoimentos autorizados e evidência de
consentimento. Nenhuma dessas pendências foi preenchida com dados fictícios.
