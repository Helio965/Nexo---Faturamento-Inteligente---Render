# E-mails transacionais do NEXO — funcionamento, configuração e diagnóstico

Guia operacional dos e-mails de **ativação de conta (boas-vindas)**, **recuperação
de senha**, **aviso de senha alterada**, **análise publicada** e **chamado
resolvido**. Código: `emails.py` (envio), `contas_email.py` (busca de contas por
e-mail), `blueprints/auth.py` e `blueprints/admin.py` (gatilhos), templates em
`templates/emails/`.

## 1. Como o NEXO envia e-mails

1. Um evento de negócio é **confirmado no banco** (cadastro, publicação, chamado
   resolvido, troca de senha). O e-mail só é solicitado depois do `COMMIT`.
2. O gatilho monta o link sensível a partir da **origem pública canônica**
   (`NEXO_PUBLIC_URL` ou, sem ela, `RENDER_EXTERNAL_URL`) — nunca do cabeçalho
   `Host` da requisição (`origem_publica.py`).
3. `emails.enviar_email` renderiza o template, cria a versão em texto simples e
   entrega a mensagem ao transporte:
   - **API HTTPS do Brevo** (porta 443) quando `BREVO_API_KEY` está definida;
   - **SMTP do Flask-Mail** quando há apenas `MAIL_USERNAME`/`MAIL_PASSWORD`;
   - **nenhum** (envio desativado) quando não há credenciais.
4. Cada solicitação devolve um `EnvioEmail` com um **estado operacional**:

| Estado | Significado | O que NÃO significa |
| --- | --- | --- |
| `DESATIVADO` | Não há transporte configurado; nada saiu. | — |
| `SEM_DESTINATARIO` | Não há destinatário elegível (ex.: empresa cancelada). | — |
| `AGENDADO` | Thread de envio iniciada; resultado ainda desconhecido. | Não significa enviado. |
| `ACEITO_PELO_PROVEDOR` | A API do Brevo (HTTP 201) ou o servidor SMTP aceitou a mensagem. | Não comprova chegada à caixa de entrada. |
| `FALHA_NO_ENVIO` | Falhou no preparo, no agendamento ou foi recusada pelo provedor; vem com uma **categoria**. | — |

5. **Modos de envio**
   - *Assíncrono* (thread): recuperação de senha, aviso de senha alterada,
     análise publicada e chamado resolvido. Na recuperação, isso mantém a
     resposta pública genérica e com tempo independente do provedor (proteção
     contra enumeração de contas).
   - *Síncrono*, com prazo: cadastro de empresa, reenvio de ativação e envio de
     teste (ações do administrador), para mostrar na hora se o provedor aceitou.
6. **Confiabilidade**: cada tentativa tem prazo (`NEXO_EMAIL_TIMEOUT`, padrão
   15 s, também aplicado ao SMTP, que o Flask-Mail abria sem prazo). Uma única
   nova tentativa é feita quando o pedido comprovadamente não foi processado
   (HTTP 429 dentro do `Retry-After`, 500/503 ou falha de conexão antes do
   envio). Prazo esgotado, conexão caída **depois** do envio e 502/504 de
   gateway não são repetidos (evita e-mail duplicado): ficam como falha de
   resultado incerto (`tempo_esgotado`, `conexao_interrompida`,
   `gateway_sem_resposta`), e o admin lê "pode não ter sido enviado". A chave
   da API nunca acompanha um redirecionamento, e uma resposta que não seja a do
   envio (201/202) não conta como aceite. No encerramento do processo
   (deploy/reinício), envios em andamento são aguardados por até ~20 s; os que
   não terminarem ficam registrados em log como **interrompidos**.
7. Falha de e-mail **nunca desfaz** o cadastro, a publicação, a resolução do
   chamado nem a troca de senha.

### Por que não há fila persistente

Avaliamos uma fila em banco (outbox) e ela **não foi introduzida**: as causas
encontradas eram de configuração/normalização, não de perda de threads; todos
os fluxos têm reenvio pelo usuário ou pelo admin (recuperação de senha, botão
"Reenviar link de ativação"); análise e chamado também avisam pelo sininho
(persistido). Uma outbox exigiria migração de esquema e um processo de
reenvio contínuo, que o Render Free (instância que hiberna) não sustenta bem.
Se o volume crescer ou houver exigência de garantia de entrega, a evolução
natural é uma tabela de envios pendentes com reprocessamento periódico.

## 2. Transporte em produção (Render Free)

O **Render Free bloqueia a saída SMTP nas portas 25, 465 e 587** desde
26/09/2025 ([changelog do Render](https://render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports)).
Em produção no Render use **somente a API HTTPS do Brevo** (porta 443). Se a
aplicação subir com SMTP no Render, o log de inicialização e o painel do admin
mostram uma pendência que **bloqueia o envio**.

## 3. Variáveis de ambiente

| Variável | Obrigatória no Render | Descrição |
| --- | --- | --- |
| `BREVO_API_KEY` | **Sim** | Chave **de API** do Brevo (começa com `xkeysib-`). A chave **SMTP** (`xsmtpsib-`) não funciona na API e é recusada com HTTP 401. Espaços/quebra de linha nas pontas são ignorados; valor vazio = ausente. |
| `MAIL_DEFAULT_SENDER` | **Sim** | Remetente **verificado** no Brevo, no formato `Nome <email@dominio>`. Vazio cai no padrão do projeto. |
| `NEXO_PUBLIC_URL` | Recomendada | Origem `https://` dos links nos e-mails. Sem ela, vale `RENDER_EXTERNAL_URL` (injetada pelo Render). Produção exige `https`. |
| `BREVO_API_URL` | Não | Padrão `https://api.brevo.com/v3/smtp/email`. Precisa ser `https` (a chave nunca é enviada sem TLS). |
| `NEXO_EMAIL_TIMEOUT` | Não | Prazo, em segundos, de cada tentativa (1 a 60; padrão 15). |
| `NEXO_EMAIL_ALERTA_ADMIN` | Não | `1` (padrão em produção) cria aviso no sininho dos administradores quando o provedor não aceita um e-mail; `0` desliga. No máximo um aviso por categoria a cada 30 minutos. O envio desativado não gera aviso (aparece no dashboard). |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD` | Não (só fora do Render Free) | Alternativa SMTP. O certificado TLS do servidor SMTP é verificado. |

> Uma variável declarada no `render.yaml` com `sync: false` **não** tem valor
> até alguém preenchê-la no painel. Confira em *Render → serviço → Environment*.

## 4. Configuração no Brevo (procedimento manual)

Estes passos dependem do painel do Brevo e não podem ser feitos pelo código.

1. **Chave de API**: *SMTP e API → Chaves de API → Gerar nova chave*. Copie o
   valor inteiro **no momento da criação** (depois o Brevo só mostra a chave
   mascarada) e cole em `BREVO_API_KEY` no Render. Não use a aba *SMTP*.
2. **Remetente**: *Remetentes, domínios e IPs dedicados → Remetentes → Adicionar
   remetente* com o mesmo endereço de `MAIL_DEFAULT_SENDER` e confirme o código
   de 6 dígitos enviado a esse endereço. Remetente não verificado é recusado
   (categoria `remetente_nao_autorizado`).
3. **Domínio (recomendado)**: o remetente atual do projeto é um endereço
   `@gmail.com`. Domínios gratuitos **não podem ser autenticados** no Brevo; o
   Brevo reescreve o remetente para um domínio próprio dele, o que favorece a
   caixa de spam. Para entregabilidade, use um domínio próprio e autentique-o
   em *Remetentes, domínios e IPs dedicados → Domínios* (registros DNS do
   Brevo: código de verificação, DKIM e DMARC); depois troque
   `MAIL_DEFAULT_SENDER` para um endereço desse domínio.
4. **IPs autorizados**: contas criadas a partir de 16/05/2024 bloqueiam por
   padrão chamadas de API vindas de IPs desconhecidos (resposta HTTP 401;
   categoria `ip_nao_autorizado`). No Render, copie as faixas de saída em
   *serviço → Connect → Outbound* e cadastre-as no Brevo em *Configurações →
   Segurança → IPs autorizados* (aceita CIDR). Se o Brevo enviar ao dono da
   conta um e-mail "Validate your IP address", confirme por ele. Desativar o
   bloqueio funciona, mas reduz a segurança da chave.
5. **Conta**: uma conta em validação ou sem créditos é recusada (categorias
   `conta_em_validacao`, `creditos_insuficientes`, `conta_sem_permissao`).

## 5. Como identificar falhas

- **Painel do admin → Dashboard**: faixa vermelha quando a configuração impede
  qualquer envio, com link para o diagnóstico.
- **Admin → Diagnóstico de e-mail** (`/admin/diagnostico-email`): transporte
  ativo, remetente, formato da chave (só pelo prefixo; o valor nunca é exibido),
  endpoint, origem dos links, pendências e os **envios recentes** deste processo
  (estado, categoria, HTTP/código do provedor, correlação). A lista fica em
  memória: reinício do servidor (inclusive a hibernação do plano gratuito) a
  zera — logs e avisos do sininho permanecem.
- **Sininho dos administradores** (produção): aviso persistido quando o provedor
  não aceita um e-mail, com a categoria e a referência (`Ref.`). O aviso é gravado
  pela thread de envio (ou pela ação do admin), nunca pela requisição pública de
  recuperação — assim o tempo de resposta não revela se a conta existe.
- **Mensagens do cadastro de empresa e do reenvio**: dizem se o e-mail foi
  aceito pelo serviço de envio, se o serviço está desativado ou qual foi a
  falha, sempre com a referência.
- **Logs do Render** (*serviço → Logs*): uma linha por desfecho, por exemplo

```text
E-mail transacional não enviado (falha) | tipo=recuperacao_senha transporte=brevo estado=FALHA_NO_ENVIO categoria=ip_nao_autorizado http=401 codigo=unauthorized erro=RuntimeError tentativas=1 correlacao=3fa9c1d2e4b5 referencia=usuario:12 id_mensagem=- instante=2026-10-31T23:59:59+00:00
```

  Procure por `correlacao=<Ref.>` para ligar a mensagem do admin, o aviso do
  sininho e o log. Na inicialização há um resumo (`Configuração de e-mail |
  transporte=...`) e cada pendência aparece como WARNING. Uma linha
  `estado=AGENDADO` sem linha final da mesma correlação indica envio
  interrompido. Nunca são registrados destinatário, assunto, corpo, link,
  token, senha, chave nem a mensagem de erro do provedor.

| Categoria | Causa provável | Ação |
| --- | --- | --- |
| `transporte_desativado` | `BREVO_API_KEY` ausente/vazia | Preencher no Render e reiniciar o serviço |
| `credencial_rejeitada` | Chave inválida, revogada, mascarada ou chave SMTP | Gerar chave de API (`xkeysib-`) |
| `ip_nao_autorizado` | IP de saída do Render não autorizado no Brevo | Seção 4, passo 4 |
| `remetente_nao_autorizado` / `remetente_invalido` | Remetente não verificado ou mal escrito | Seção 4, passo 2 |
| `conta_em_validacao` / `creditos_insuficientes` / `conta_sem_permissao` | Situação da conta Brevo | Painel/suporte do Brevo |
| `limite_excedido` | Cota diária (plano gratuito: 300/dia) ou rajada | Aguardar; revisar o plano |
| `provedor_indisponivel` / `rede` | Instabilidade do Brevo ou da rede (pedido não processado) | Conferir status do Brevo; reenviar depois |
| `tempo_esgotado` / `conexao_interrompida` / `gateway_sem_resposta` | Resposta perdida depois do envio: **o e-mail pode ter sido aceito** | Conferir o evento no Brevo antes de reenviar |
| `configuracao_invalida` | `BREVO_API_URL` errada, sem https ou redirecionada | Voltar ao padrão `https://api.brevo.com/v3/smtp/email` |
| `smtp_conexao` | SMTP bloqueado (Render Free) ou servidor fora | Usar o Brevo |
| `destinatario_invalido` / `sem_destinatario` | E-mail cadastrado inválido ou ninguém elegível | Corrigir o cadastro |

## 6. Aceite × entrega

`ACEITO_PELO_PROVEDOR` quer dizer que o Brevo recebeu a mensagem e devolveu um
`messageId` (registrado em `id_mensagem=`). A entrega depende do provedor do
destinatário. Para confirmar:

1. Brevo → *Transacional → Logs* (ou *Estatísticas → Logs* conforme a versão do
   painel): filtre pela etiqueta `nexo-<tipo>` (por exemplo
   `nexo-recuperacao_senha`, `nexo-boas_vindas`, `nexo-teste`) e confira o
   evento: *Entregue*, *Adiado*, *Soft bounce*, *Hard bounce*, *Bloqueado*,
   *Spam*, *Inválido* ou *Erro*. Cada mensagem também leva o cabeçalho
   `X-Nexo-Correlacao` com a correlação do log.
2. A API `GET https://api.brevo.com/v3/smtp/statistics/events?messageId=<id>`
   devolve os mesmos eventos (uso administrativo, com a chave de API).
3. Caixa de entrada **e pasta de spam** do destinatário.

## 7. Testes controlados

Automatizados (sem rede e sem envio real): `python -B -m unittest
tests.test_emails_transacionais tests.test_auth_email_flows
tests.test_email_logging -v`.

Teste real (somente com autorização e destinatário controlado):

1. **Configuração**: Admin → Diagnóstico de e-mail sem pendências bloqueantes.
2. **Envio de teste**: botão "Enviar e-mail de teste para mim" (vai apenas para
   o e-mail do administrador logado; limite de 5 por hora). A mensagem mostra o
   resultado do provedor e a referência.
3. **Recuperação de senha**: com uma conta de teste controlada, use "Esqueci
   minha senha" uma única vez; confira nos logs a linha `tipo=recuperacao_senha`
   (`estado=ACEITO_PELO_PROVEDOR`), no Brevo o evento da etiqueta
   `nexo-recuperacao_senha`, a caixa de entrada e o spam; abra o link (válido por
   15 minutos e de uso único) e defina a nova senha.
4. **Cadastro de empresa**: cadastre uma empresa de teste com e-mail controlado;
   a mensagem do cadastro informa o aceite; confira a etiqueta
   `nexo-boas_vindas` no Brevo e conclua a ativação pelo link.
5. Registre a data, a referência (`Ref.`), o `messageId` e o evento final do
   Brevo.

## 8. Quando o Brevo estiver indisponível

- Nada é perdido no banco: cadastros, publicações e chamados continuam
  confirmados; o sininho segue funcionando.
- Clientes pendentes de ativação recebem novo link por *Detalhes da empresa →
  Acesso ao portal → Reenviar link de ativação* ou pelo "Esqueci minha senha".
- Recuperação de senha: o cliente repete o pedido depois (os links antigos
  expiram em 15 minutos).
- Avisos de análise publicada/chamado resolvido que falharam não são
  reenviados automaticamente (o cliente vê o aviso no sininho).

## 9. E-mails com maiúsculas e minúsculas

Cadastros novos gravam o e-mail em minúsculas e recusam um endereço que já
exista com outra combinação de maiúsculas. Login e recuperação procuram o texto
exato e, se não houver, a conta única que coincide sem diferenciar maiúsculas.
**Nenhum registro existente é alterado.** Para conferir conflitos legados
(somente leitura, no SQL Editor do Supabase):

```sql
SELECT lower(email) AS email_normalizado, count(*) AS contas
FROM usuario GROUP BY lower(email) HAVING count(*) > 1;
```

Se houver resultado, decida manualmente qual conta manter: enquanto o conflito
existir, o pedido de recuperação com uma grafia diferente das gravadas não
envia nada (e registra um aviso no log).
