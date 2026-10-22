# NEXO-SEC-002 — ativação e recuperação de senha

## Diagnóstico e escopo

Na base `a557af2a1eeed1658b71189b3ae6f00eed435a70`, o token v1 continha
somente o e-mail, com um único salt e validade de 900 segundos. Ativação e
recuperação aceitavam o mesmo token. Alterar a senha não mudava sua validade;
duas requisições podiam validar antes de qualquer delas confirmar a alteração.

Esta correção preserva o schema, os hashes Werkzeug, os formulários, CSRF,
rate limiting e o envio de e-mails. Não altera políticas de empresas,
revogação de sessões, WebSocket, PDF, infraestrutura ou dependências.

## Formato e emissão

Os tokens v2 são assinados por `URLSafeTimedSerializer`, com HMAC-SHA256,
namespaces distintos para `activation` e `recovery` e prazo de 900 segundos.
O payload contém versão, identificador do usuário, finalidade e uma impressão
HMAC-SHA256 da credencial atual, vinculada ao identificador e à `senha_hash`.
A chave existente `SECRET_KEY` é usada com separação de contexto criptográfico.

Assinatura não fornece sigilo. O payload não contém e-mail, senha, hash completo,
chave secreta ou dados comerciais. O token inteiro é uma credencial sensível:
não deve ser registrado nem disponibilizado na resposta pública.

- Cadastro administrativo: emite ativação usando o usuário já persistido.
- Ativação: exige CLIENTE ativo e `primeiro_acesso=True`.
- Recuperação: exige conta ativa sem ativação de cliente pendente.
- ADMIN com a flag legada `primeiro_acesso=True` continua elegível à recuperação.
- Formulário de recuperação: reenvia ativação ao CLIENTE pendente; envia reset
  aos demais elegíveis. A resposta pública permanece genérica, inclusive em DEBUG.
- GET valida e mostra o formulário; POST revalida antes de tentar a alteração.

## Consumo único e transação

A validação recarrega o usuário do banco, confere elegibilidade e impressão em
tempo constante, e captura um snapshot imutável da credencial. Nenhum atributo
ORM é alterado antes da atualização condicional, evitando autoflush prematuro.

O consumo usa uma única instrução `UPDATE usuario`, condicionada a:

- Identificador e `senha_hash` esperados;
- Conta ainda ativa;
- Papel e estado de primeiro acesso iguais aos validados.

Só `rowcount == 1` permite commit e resposta de sucesso. A instrução define o
novo hash, encerra o primeiro acesso e registra a data de atualização. Mesmo
escolhendo a mesma senha, o salt aleatório do novo hash invalida os tokens
anteriores. Todos os tokens emitidos para a credencial anterior deixam de valer.
O primeiro acesso autenticado usa a mesma atualização condicional para não
sobrescrever um consumo concorrente de link.

No PostgreSQL com READ COMMITTED, o segundo UPDATE espera a transação concorrente
e reavalia o predicado após o primeiro commit: o hash esperado já não coincide.
Sob isolamentos mais fortes pode haver erro de serialização; erros SQL e de
commit são tratados com rollback e falha genérica, sem anunciar sucesso.
SQLite tem comportamento de locks distinto; não confundir testes SQLite com
execução em PostgreSQL/Supabase.

Zero linhas afetadas provoca rollback e rejeição. Senha inválida ou confirmação
divergente não consome token. Uma falha com rollback confirmado mantém a
credencial anterior e permite nova tentativa enquanto o token for válido.
Logs da aplicação registram somente o tipo de erro, sem SQL, parâmetros ou token.

## Compatibilidade e publicação futura

Não há migração, tabela nova, nova variável ou alteração no Supabase.
Os namespaces v1 são rejeitados sem fallback: links emitidos antes da mudança
devem ser solicitados novamente pelo formulário existente. O prazo curto limita
o impacto, mas clientes precisam ter o transporte de e-mail funcionando.

Na implantação autorizada futura, retire workers antigos para que não continuem
aceitando v1 durante a transição. Rollback para o código v1 reintroduz a falha e
não aceita links v2; prefira correção adiante. Não aplicar mudanças no banco.
Homologue emissão/consumo, e-mails e concorrência no PostgreSQL de teste antes
de liberar produção. Mascaramento de caminhos com tokens em logs do proxy/servidor
deve ser conferido operacionalmente, sem registrar valores em diagnósticos.

Esta etapa não revoga cookies HTTP nem conexões Socket.IO anteriores à troca de
senha. Esse risco permanece para a NEXO-SEC-003 e não deve ser confundido com
reutilização do token, que é rejeitada pela credencial alterada.

## Verificação

Da raiz, com dependências já instaladas:

```bash
.venv/bin/python -B -m unittest tests.test_auth_tokens_security -v
.venv/bin/python -B -m unittest discover -s tests -t .
```

Usar apenas os bancos e usuários sintéticos dos testes. A suíte específica deve
forçar duas solicitações a chegar ao UPDATE depois de validar o mesmo token,
exigir somente uma alteração confirmada e distinguir os resultados de cada
backend. Não usar banco de produção para executar esses comandos.

### Evidências desta revisão

| Execução | Total | Aprovados | Ignorados | Falhas |
| --- | ---: | ---: | ---: | ---: |
| Base `a557af2` antes da alteração | 223 | 211 | 12 | 0 |
| Suíte completa após a alteração | 259 | 247 | 12 | 0 |

Os 36 testes novos passaram, incluindo três corridas reais: recuperação,
ativação e primeiro acesso autenticado. Duas sessões independentes validam o
mesmo estado e encontram uma barreira antes do UPDATE. Cada corrida exige
`rowcounts [0, 1]`, exatamente um commit, redirecionamentos seguros para ambos
os resultados e hash final correspondente à senha da requisição vencedora.
Erro de lock não é aceito como prova de consumo único.

Os 12 testes ignorados já estavam na linha de base: um backup/restore que exige
binários PostgreSQL locais e 11 testes opcionais de navegador que exigem
Playwright e habilitação explícita. Os testes de segurança PDF da NEXO-SEC-001
passaram. As corridas desta revisão usaram SQLite temporário e dados sintéticos;
nenhum teste foi conectado ao Supabase. PostgreSQL real e navegador continuam
como verificações pendentes de homologação.
