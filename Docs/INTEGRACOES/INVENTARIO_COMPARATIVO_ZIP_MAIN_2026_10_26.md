# Inventário comparativo: ZIP local × `main` do GitHub (26/10/2026)

Anexo do [relatório da integração](RELATORIO_INTEGRACAO_GITHUB_ZIP_2026_10_26.md).

## Método

- **GitHub:** árvore da `main` em `94e9b6ae4e2fb3d6582301cdfc3dd4397b4fdbb2` (merge do PR #23), lida com `git ls-tree`/`git cat-file`.
- **ZIP:** `Nexo - Faturamento Inteligente(4).zip` recebido nesta sessão (19.189.840 bytes, SHA-256 `bfbd2dadc0e3cc1ac42ad6cf5b9161e11b7ea274d9a7b5253562cbae619436eb`), raiz `Nexo - Faturamento Inteligente/`, 272 arquivos, sem `.git`, sem caminhos absolutos ou com `..`. Extraído em diretório temporário isolado, fora do repositório.
- **Comparação de conteúdo** (não só de nomes): bytes iguais = IDÊNTICO; iguais depois de trocar CRLF por LF = DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL); demais = alterado.
- **Linha de base comum:** o ZIP coincide com o commit `ff8c2d8` da `main` (merge do PR #20) em 241 arquivos (167 idênticos e 74 só com EOL) e não tem nenhum arquivo ausente em relação a ele. Entre `ff8c2d8` e `94e9b6a` a `main` só ganhou `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md` (PR #23). Por isso os 17 arquivos alterados são "ALTERADO NO ZIP": nenhum deles mudou no GitHub depois da base, e não há arquivo "ALTERADO NAS DUAS LINHAS".
- **Outras branches:** só `feature/reestruturacao-comercial-nexo` e `feature/nexo-etapa-0-2-protecao-banco` (PR #22, mesmo conteúdo) não estão integradas à `main`. Elas alteram `.gitignore` e criam `Docs/REESTRUTURACAO_COMERCIAL/00_02_PROTECAO_BANCO_MIGRACOES.md`, o mesmo caminho de um arquivo do ZIP, com outro conteúdo. As demais 21 branches remotas estão contidas na `main`.

## Totais

| Classificação | Quantidade |
|---|---:|
| IDÊNTICO | 167 |
| DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL; em todos, `main` CRLF × ZIP LF) | 74 |
| ALTERADO NO ZIP | 17 (1 deles, `.gitignore`, também alterado no PR #22) |
| ALTERADO NO GITHUB (desde a base `ff8c2d8`) | 0 |
| ALTERADO NAS DUAS LINHAS DE DESENVOLVIMENTO | 0 |
| EXCLUSIVO DO ZIP | 14 (1 deles, o `00_02`, também existe no PR #22 com outro conteúdo) |
| EXCLUSIVO DO GITHUB (`main`) | 1 (`RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`) |
| EXCLUSIVO DE OUTRA BRANCH | 0 caminhos novos; o PR #22 só diverge no `00_02` e no `.gitignore` acima |
| **Total de caminhos distintos** | **273** |

Os números coincidem com a auditoria anterior de 26/10/2026 (167 / 74 / 17 / 14 / 1), agora recalculados sobre a `main` atual.

**Composição do ZIP por tipo** (272 arquivos): 66 Python da aplicação, 38 templates, 6 CSS/JS, 31 imagens e mídias, 47 documentos, 12 migrações, 46 testes, 16 scripts auxiliares (`scripts/`, `tools/`) e 10 de configuração ou outros (`.env.example` só com placeholders, `.gitignore`, `.github/workflows/nexo-security-ci.yml`, `render.yaml`, `requirements*.txt`, `LICENSE`, `uploads/.gitkeep` etc.). Não havia `.env`, banco SQLite, dump, log, ambiente virtual, `__pycache__` nem diretório `.git`.

## Inventário arquivo a arquivo

| # | Arquivo | Classificação | Decisão na integração |
|---|---|---|---|
| 1 | `.env.example` | IDÊNTICO | Mantido (sem alteração) |
| 2 | `.github/workflows/nexo-security-ci.yml` | IDÊNTICO | Mantido (sem alteração) |
| 3 | `.gitignore` | ALTERADO NO ZIP + ALTERADO EM OUTRA BRANCH (PR #22) | Integrado: união das regras do ZIP (SQLite WAL) e do PR #22 (dumps/chaves) |
| 4 | `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md` | EXCLUSIVO DO ZIP | Integrado e atualizado (metodologia, situação por ambiente; caminhos anonimizados) |
| 5 | `Docs/AJUSTES_NEXO_2026/NEXO_AJ_00_BASELINE.md` | EXCLUSIVO DO ZIP | Integrado com nota de integração; caminhos anonimizados |
| 6 | `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` | EXCLUSIVO DO ZIP | Integrado com nota de integração; caminhos anonimizados |
| 7 | `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_06_1_PARA_CHATGPT.md` | EXCLUSIVO DO ZIP | Integrado com nota de integração |
| 8 | `Docs/ARQUIVOS_PUBLICACAO.txt` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 9 | `Docs/ARQUIVOS_REMOVIDOS_RENDER.json` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 10 | `Docs/AUDITORIA_DEPENDENCIAS_SEC006.md` | IDÊNTICO | Mantido (sem alteração) |
| 11 | `Docs/AUDITORIA_RENDER.md` | IDÊNTICO | Mantido (sem alteração) |
| 12 | `Docs/CI_SEGURANCA.md` | IDÊNTICO | Mantido (sem alteração) |
| 13 | `Docs/DER_NEXO_MVP_V4_Completo_Com_Roadmap.docx` | IDÊNTICO | Mantido (sem alteração) |
| 14 | `Docs/EVIDENCIAS_RENDER.json` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 15 | `Docs/HOMOLOGACAO_SEC002_POSTGRES_EMAIL.md` | IDÊNTICO | Mantido (sem alteração) |
| 16 | `Docs/INVENTARIO_ANTES_RENDER.json` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 17 | `Docs/NEXOBOT_ADVANCED.md` | IDÊNTICO | Mantido (sem alteração) |
| 18 | `Docs/OPERACAO_BACKUP_RESTAURACAO.md` | ALTERADO NO ZIP | Integrado (Grupo B, Etapa 0.2A) |
| 19 | `Docs/PENDENCIAS_NEXO_COM002_AVALIACOES.md` | IDÊNTICO | Mantido (sem alteração) |
| 20 | `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md` | IDÊNTICO | Mantido (sem alteração) |
| 21 | `Docs/PLANO_ACAO_COMERCIAL_LANDING_NEXO.md` | IDÊNTICO | Mantido (sem alteração) |
| 22 | `Docs/PLANO_PUBLICACAO_SEGURA.md` | ALTERADO NO ZIP | Integrado (Grupo B, Etapa 0.2A) |
| 23 | `Docs/PREPARACAO_RENDER.md` | ALTERADO NO ZIP | Integrado (Grupo B, Etapa 0.2A) |
| 24 | `Docs/REESTRUTURACAO_COMERCIAL/00_01_BASELINE_GITHUB.md` | IDÊNTICO | Mantido (sem alteração) |
| 25 | `Docs/REESTRUTURACAO_COMERCIAL/00_02_PROTECAO_BANCO_MIGRACOES.md` | EXCLUSIVO DO ZIP + EXCLUSIVO DE OUTRA BRANCH (PR #22, conteúdo diferente) | Integrado: versão 0.2A (ZIP) no caminho canônico; versão do PR #22 preservada em 00_02_PROTECAO_BANCO_MIGRACOES_ETAPA_0_2_PR22.md |
| 26 | `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/01_logo_cubo_sem_texto.png` | EXCLUSIVO DO ZIP | Integrado (Grupo C) |
| 27 | `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/02_logo_cubo_com_texto.jpg` | EXCLUSIVO DO ZIP | Integrado (Grupo C) |
| 28 | `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/03_telas_atuais_marca_portal_admin_login.png` | EXCLUSIVO DO ZIP | NÃO versionado: publicada versão redigida 03_..._redigida.png (dados de empresa, valores, totais do ADMIN e URL) |
| 29 | `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/04_regras_contrato_status_planos_logo.png` | EXCLUSIVO DO ZIP | Integrado (Grupo C) |
| 30 | `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/05_regras_aviso_renovacao_lgpd_dns.png` | EXCLUSIVO DO ZIP | Integrado (Grupo C) |
| 31 | `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/README.md` | EXCLUSIVO DO ZIP | Integrado com nota de integração (arquivo 03 redigido; estado pós-AJ-06.1) |
| 32 | `Docs/RELATORIO_COBERTURA_ETL.md` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 33 | `Docs/RELATORIO_CONCLUSAO_PENDENCIAS_SEGURANCA.md` | IDÊNTICO | Mantido (sem alteração) |
| 34 | `Docs/RELATORIO_NEXO_COM001_LANDING_COMERCIAL.md` | IDÊNTICO | Mantido (sem alteração) |
| 35 | `Docs/RELATORIO_NEXO_SEC004_RESTAURACAO_SEGURA.md` | IDÊNTICO | Mantido (sem alteração) |
| 36 | `Docs/RELATORIO_NEXO_SEC005_ETL_SEGURO.md` | IDÊNTICO | Mantido (sem alteração) |
| 37 | `Docs/RELATORIO_NEXO_SEC006B_DEPENDENCIAS.md` | IDÊNTICO | Mantido (sem alteração) |
| 38 | `Docs/RELATORIO_NEXO_SEC006_DEPENDENCIAS.md` | IDÊNTICO | Mantido (sem alteração) |
| 39 | `Docs/RELATORIO_TECNICO.md` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 40 | `Docs/SEGURANCA_REVOGACAO_SESSOES.md` | IDÊNTICO | Mantido (sem alteração) |
| 41 | `Docs/SEGURANCA_TOKENS_SENHA.md` | IDÊNTICO | Mantido (sem alteração) |
| 42 | `Docs/VALIDACAO_RENDER.txt` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 43 | `Docs/VALIDACAO_VIDEO_RENDER.md` | IDÊNTICO | Mantido (sem alteração) |
| 44 | `Docs/nexobot/evidencias/README.md` | IDÊNTICO | Mantido (sem alteração) |
| 45 | `Docs/nexobot/evidencias/antes/1440_aberto.png` | IDÊNTICO | Mantido (sem alteração) |
| 46 | `Docs/nexobot/evidencias/antes/1440_ajuda.png` | IDÊNTICO | Mantido (sem alteração) |
| 47 | `Docs/nexobot/evidencias/antes/1440_como_funciona.png` | IDÊNTICO | Mantido (sem alteração) |
| 48 | `Docs/nexobot/evidencias/antes/320_aberto.png` | IDÊNTICO | Mantido (sem alteração) |
| 49 | `Docs/nexobot/evidencias/antes/320_ajuda.png` | IDÊNTICO | Mantido (sem alteração) |
| 50 | `Docs/nexobot/evidencias/antes/320_como_funciona.png` | IDÊNTICO | Mantido (sem alteração) |
| 51 | `Docs/nexobot/evidencias/antes/390_aberto.png` | IDÊNTICO | Mantido (sem alteração) |
| 52 | `Docs/nexobot/evidencias/antes/390_ajuda.png` | IDÊNTICO | Mantido (sem alteração) |
| 53 | `Docs/nexobot/evidencias/antes/390_como_funciona.png` | IDÊNTICO | Mantido (sem alteração) |
| 54 | `Docs/nexobot/evidencias/depois/1440_aberto.png` | IDÊNTICO | Mantido (sem alteração) |
| 55 | `Docs/nexobot/evidencias/depois/1440_ajuda.png` | IDÊNTICO | Mantido (sem alteração) |
| 56 | `Docs/nexobot/evidencias/depois/1440_como_funciona.png` | IDÊNTICO | Mantido (sem alteração) |
| 57 | `Docs/nexobot/evidencias/depois/1440_pressao_estoque.png` | IDÊNTICO | Mantido (sem alteração) |
| 58 | `Docs/nexobot/evidencias/depois/320_aberto.png` | IDÊNTICO | Mantido (sem alteração) |
| 59 | `Docs/nexobot/evidencias/depois/320_ajuda.png` | IDÊNTICO | Mantido (sem alteração) |
| 60 | `Docs/nexobot/evidencias/depois/320_como_funciona.png` | IDÊNTICO | Mantido (sem alteração) |
| 61 | `Docs/nexobot/evidencias/depois/320_pressao_estoque.png` | IDÊNTICO | Mantido (sem alteração) |
| 62 | `Docs/nexobot/evidencias/depois/390_aberto.png` | IDÊNTICO | Mantido (sem alteração) |
| 63 | `Docs/nexobot/evidencias/depois/390_ajuda.png` | IDÊNTICO | Mantido (sem alteração) |
| 64 | `Docs/nexobot/evidencias/depois/390_como_funciona.png` | IDÊNTICO | Mantido (sem alteração) |
| 65 | `Docs/nexobot/evidencias/depois/390_pressao_estoque.png` | IDÊNTICO | Mantido (sem alteração) |
| 66 | `Docs/schema_nexo_mvp_v4 (1).sql` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 67 | `LICENSE` | IDÊNTICO | Mantido (sem alteração) |
| 68 | `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md` | EXCLUSIVO DO ZIP | Integrado byte a byte (SHA-256 b59e9d72…) |
| 69 | `NEXO_RENDER_PROGRESS.md` | IDÊNTICO | Mantido (sem alteração) |
| 70 | `README.md` | IDÊNTICO | Mantido (sem alteração) |
| 71 | `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md` | EXCLUSIVO DO GITHUB | Preservado (PR #23; incidente HTTP 500 não resolvido) |
| 72 | `RELATORIO_FINAL_PARA_CHATGPT.md` | IDÊNTICO | Mantido (sem alteração) |
| 73 | `ai_devolutiva.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 74 | `app.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 75 | `blueprints/__init__.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 76 | `blueprints/admin.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 77 | `blueprints/api.py` | IDÊNTICO | Mantido (sem alteração) |
| 78 | `blueprints/auth.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 79 | `blueprints/cliente.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 80 | `blueprints/notificacoes.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 81 | `company_security.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 82 | `config.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 83 | `criar_cliente_demo.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 84 | `emails.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 85 | `etl_inputs.py` | IDÊNTICO | Mantido (sem alteração) |
| 86 | `etl_limits.py` | IDÊNTICO | Mantido (sem alteração) |
| 87 | `etl_processor.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 88 | `etl_runtime.py` | IDÊNTICO | Mantido (sem alteração) |
| 89 | `etl_uploads.py` | IDÊNTICO | Mantido (sem alteração) |
| 90 | `etl_worker.py` | IDÊNTICO | Mantido (sem alteração) |
| 91 | `extensions.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 92 | `init_db.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 93 | `insights.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 94 | `log_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 95 | `migrar_arquivos_para_db.py` | IDÊNTICO | Mantido (sem alteração) |
| 96 | `migrations/README` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 97 | `migrations/alembic.ini` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 98 | `migrations/env.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 99 | `migrations/script.py.mako` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 100 | `migrations/versions/91a2ecf56a41_primeiro_acesso_em_usuario.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 101 | `migrations/versions/a3f1c9b27d04_soft_delete_lixeira_empresa.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 102 | `migrations/versions/b7c4e2a9f031_arquivo_armazenado_storage_no_banco.py` | IDÊNTICO | Mantido (sem alteração) |
| 103 | `migrations/versions/c7189696a9cd_periodo_base_em_indicador_analise.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 104 | `migrations/versions/d61b5e68082c_guia_topico_cms_base_de_conhecimento.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 105 | `migrations/versions/d87a6fbc2fbe_schema_inicial_nexo_sqlite_para_.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 106 | `migrations/versions/e4c004a26b01_company_authorization_generation.py` | IDÊNTICO | Mantido (sem alteração) |
| 107 | `migrations/versions/f958d38a7f19_gerado_por_ia_em_relatorio_analise.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 108 | `models.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 109 | `nexobot/__init__.py` | IDÊNTICO | Mantido (sem alteração) |
| 110 | `nexobot/classificacao.py` | IDÊNTICO | Mantido (sem alteração) |
| 111 | `nexobot/conhecimento.py` | IDÊNTICO | Mantido (sem alteração) |
| 112 | `nexobot/contexto.py` | IDÊNTICO | Mantido (sem alteração) |
| 113 | `nexobot/higiene.py` | IDÊNTICO | Mantido (sem alteração) |
| 114 | `nexobot/intencoes.py` | IDÊNTICO | Mantido (sem alteração) |
| 115 | `nexobot/lexico.py` | IDÊNTICO | Mantido (sem alteração) |
| 116 | `nexobot/navegacao.py` | IDÊNTICO | Mantido (sem alteração) |
| 117 | `nexobot/normalizacao.py` | IDÊNTICO | Mantido (sem alteração) |
| 118 | `nexobot/portal.py` | IDÊNTICO | Mantido (sem alteração) |
| 119 | `nexobot/providers.py` | IDÊNTICO | Mantido (sem alteração) |
| 120 | `nexobot/respostas.py` | IDÊNTICO | Mantido (sem alteração) |
| 121 | `nexobot/saber/__init__.py` | IDÊNTICO | Mantido (sem alteração) |
| 122 | `nexobot/saber/acesso.py` | IDÊNTICO | Mantido (sem alteração) |
| 123 | `nexobot/saber/administracao.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 124 | `nexobot/saber/analises.py` | IDÊNTICO | Mantido (sem alteração) |
| 125 | `nexobot/saber/dashboard.py` | IDÊNTICO | Mantido (sem alteração) |
| 126 | `nexobot/saber/devolutivas_historico.py` | IDÊNTICO | Mantido (sem alteração) |
| 127 | `nexobot/saber/empresas_planos.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 128 | `nexobot/saber/glossario.py` | IDÊNTICO | Mantido (sem alteração) |
| 129 | `nexobot/saber/indicadores.py` | IDÊNTICO | Mantido (sem alteração) |
| 130 | `nexobot/saber/modelo.py` | IDÊNTICO | Mantido (sem alteração) |
| 131 | `nexobot/saber/notificacoes.py` | IDÊNTICO | Mantido (sem alteração) |
| 132 | `nexobot/saber/primeiros_passos.py` | IDÊNTICO | Mantido (sem alteração) |
| 133 | `nexobot/saber/processamento.py` | IDÊNTICO | Mantido (sem alteração) |
| 134 | `nexobot/saber/suporte_guia.py` | IDÊNTICO | Mantido (sem alteração) |
| 135 | `nexobot/saber/tecnologia.py` | IDÊNTICO | Mantido (sem alteração) |
| 136 | `nexobot/saber/uploads.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 137 | `nexobot/saber/visao_geral.py` | IDÊNTICO | Mantido (sem alteração) |
| 138 | `nexobot/seguranca.py` | IDÊNTICO | Mantido (sem alteração) |
| 139 | `nexobot/servico.py` | IDÊNTICO | Mantido (sem alteração) |
| 140 | `nexobot/similaridade.py` | IDÊNTICO | Mantido (sem alteração) |
| 141 | `notifications.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 142 | `pdf_export.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 143 | `realtime.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 144 | `render.yaml` | IDÊNTICO | Mantido (sem alteração) |
| 145 | `requirements-dev.txt` | IDÊNTICO | Mantido (sem alteração) |
| 146 | `requirements.txt` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 147 | `schema_nexo_mvp_v4.sql` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 148 | `scripts/verificar_prontidao_backup.py` | ALTERADO NO ZIP | Integrado (Grupo B, Etapa 0.2A) |
| 149 | `seed.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 150 | `seed_guia.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 151 | `session_security.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 152 | `static/.gitkeep` | IDÊNTICO | Mantido (sem alteração) |
| 153 | `static/css/landing.css` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 154 | `static/css/nexo.css` | IDÊNTICO | Mantido (sem alteração) |
| 155 | `static/img/nexo-logo.jpeg` | IDÊNTICO | Mantido (sem alteração) |
| 156 | `static/js/landing-video.js` | IDÊNTICO | Mantido (sem alteração) |
| 157 | `static/js/landing.js` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 158 | `static/js/nexo.js` | IDÊNTICO | Mantido (sem alteração) |
| 159 | `static/js/nexobot.js` | IDÊNTICO | Mantido (sem alteração) |
| 160 | `static/uploads/guia/.gitkeep` | IDÊNTICO | Mantido (sem alteração) |
| 161 | `static/video/nexo_demo_motion.mp4` | IDÊNTICO | Mantido (sem alteração) |
| 162 | `static/video/nexo_demo_poster.jpg` | IDÊNTICO | Mantido (sem alteração) |
| 163 | `static/video/nexo_demo_poster.png` | IDÊNTICO | Mantido (sem alteração) |
| 164 | `static/video/nexo_demo_preview.gif` | IDÊNTICO | Mantido (sem alteração) |
| 165 | `storage.py` | IDÊNTICO | Mantido (sem alteração) |
| 166 | `suporte_bot.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 167 | `templates/_auditoria.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 168 | `templates/_chat.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 169 | `templates/_macros.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 170 | `templates/admin/analise_form.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 171 | `templates/admin/analises.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 172 | `templates/admin/dashboard.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 173 | `templates/admin/empresa_form.html` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 174 | `templates/admin/empresas.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 175 | `templates/admin/guia.html` | IDÊNTICO | Mantido (sem alteração) |
| 176 | `templates/admin/guia_form.html` | IDÊNTICO | Mantido (sem alteração) |
| 177 | `templates/admin/lixeira.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 178 | `templates/admin/processar_resultado.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 179 | `templates/admin/relatorio_editor.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 180 | `templates/admin/ticket_detalhe.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 181 | `templates/admin/tickets.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 182 | `templates/admin/upload.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 183 | `templates/auth/_layout.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 184 | `templates/auth/login.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 185 | `templates/auth/primeiro_acesso.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 186 | `templates/auth/primeiro_acesso_token.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 187 | `templates/auth/recuperar_senha.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 188 | `templates/auth/resetar_senha.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 189 | `templates/base.html` | IDÊNTICO | Mantido (sem alteração) |
| 190 | `templates/cliente/analise.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 191 | `templates/cliente/dashboard.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 192 | `templates/cliente/guia.html` | IDÊNTICO | Mantido (sem alteração) |
| 193 | `templates/cliente/historico.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 194 | `templates/cliente/ticket_detalhe.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 195 | `templates/cliente/tickets.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 196 | `templates/cliente/upload.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 197 | `templates/como_aderir.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 198 | `templates/emails/_base.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 199 | `templates/emails/analise_publicada.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 200 | `templates/emails/boas_vindas.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 201 | `templates/emails/recuperacao_senha.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 202 | `templates/emails/ticket_resolvido.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 203 | `templates/erro_simples.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 204 | `templates/landing.html` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 205 | `test_etl.py` | DIFERENÇA SOMENTE DE FORMATAÇÃO (EOL) (main CRLF, ZIP LF) | Mantido como na main (EOL do repositório preservado) |
| 206 | `tests/__init__.py` | IDÊNTICO | Mantido (sem alteração) |
| 207 | `tests/deploy_support.py` | IDÊNTICO | Mantido (sem alteração) |
| 208 | `tests/etl_equivalence_support.py` | IDÊNTICO | Mantido (sem alteração) |
| 209 | `tests/fixtures/sec005_financial_expected.json` | IDÊNTICO | Mantido (sem alteração) |
| 210 | `tests/nexobot_corpus.py` | IDÊNTICO | Mantido (sem alteração) |
| 211 | `tests/postgresql_auth_tokens.py` | IDÊNTICO | Mantido (sem alteração) |
| 212 | `tests/postgresql_company_restore_migration.py` | IDÊNTICO | Mantido (sem alteração) |
| 213 | `tests/postgresql_company_restore_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 214 | `tests/postgresql_etl_resource_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 215 | `tests/postgresql_session_revocation.py` | IDÊNTICO | Mantido (sem alteração) |
| 216 | `tests/postgresql_support.py` | IDÊNTICO | Mantido (sem alteração) |
| 217 | `tests/test_auth_email_flows.py` | IDÊNTICO | Mantido (sem alteração) |
| 218 | `tests/test_auth_tokens_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 219 | `tests/test_backup_readiness.py` | ALTERADO NO ZIP | Integrado (Grupo B, Etapa 0.2A) |
| 220 | `tests/test_backup_restore.py` | ALTERADO NO ZIP | Integrado (Grupo B, Etapa 0.2A) |
| 221 | `tests/test_cancelled_company_postgresql.py` | EXCLUSIVO DO ZIP | Integrado (Grupo A, AJ-06.1) |
| 222 | `tests/test_cancelled_company_security.py` | EXCLUSIVO DO ZIP | Integrado (Grupo A, AJ-06.1) |
| 223 | `tests/test_company_restore_migration.py` | IDÊNTICO | Mantido (sem alteração) |
| 224 | `tests/test_company_restore_security.py` | ALTERADO NO ZIP | Integrado (Grupo A, AJ-06.1) |
| 225 | `tests/test_configuration_deploy.py` | IDÊNTICO | Mantido (sem alteração) |
| 226 | `tests/test_dependency_security_compat.py` | IDÊNTICO | Mantido (sem alteração) |
| 227 | `tests/test_dependency_wsgi_runtime.py` | IDÊNTICO | Mantido (sem alteração) |
| 228 | `tests/test_deploy.py` | IDÊNTICO | Mantido (sem alteração) |
| 229 | `tests/test_dotenv_security_compat.py` | IDÊNTICO | Mantido (sem alteração) |
| 230 | `tests/test_email_logging.py` | IDÊNTICO | Mantido (sem alteração) |
| 231 | `tests/test_etl_financial_equivalence.py` | IDÊNTICO | Mantido (sem alteração) |
| 232 | `tests/test_etl_resource_limits.py` | IDÊNTICO | Mantido (sem alteração) |
| 233 | `tests/test_etl_runtime_limits.py` | IDÊNTICO | Mantido (sem alteração) |
| 234 | `tests/test_etl_upload_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 235 | `tests/test_landing_commercial.py` | IDÊNTICO | Mantido (sem alteração) |
| 236 | `tests/test_landing_video_commercial.py` | IDÊNTICO | Mantido (sem alteração) |
| 237 | `tests/test_maintenance.py` | IDÊNTICO | Mantido (sem alteração) |
| 238 | `tests/test_nexobot_api.py` | IDÊNTICO | Mantido (sem alteração) |
| 239 | `tests/test_nexobot_conhecimento.py` | IDÊNTICO | Mantido (sem alteração) |
| 240 | `tests/test_nexobot_desempenho.py` | IDÊNTICO | Mantido (sem alteração) |
| 241 | `tests/test_nexobot_interface.py` | IDÊNTICO | Mantido (sem alteração) |
| 242 | `tests/test_nexobot_linguagem.py` | IDÊNTICO | Mantido (sem alteração) |
| 243 | `tests/test_nexobot_navegador.py` | IDÊNTICO | Mantido (sem alteração) |
| 244 | `tests/test_nexobot_regressao_original.py` | IDÊNTICO | Mantido (sem alteração) |
| 245 | `tests/test_nexobot_robustez.py` | IDÊNTICO | Mantido (sem alteração) |
| 246 | `tests/test_nexobot_saber.py` | IDÊNTICO | Mantido (sem alteração) |
| 247 | `tests/test_pdf_export_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 248 | `tests/test_security_deploy.py` | IDÊNTICO | Mantido (sem alteração) |
| 249 | `tests/test_sensitive_http_logs.py` | IDÊNTICO | Mantido (sem alteração) |
| 250 | `tests/test_session_revocation_security.py` | IDÊNTICO | Mantido (sem alteração) |
| 251 | `tests/test_supply_chain_install.py` | IDÊNTICO | Mantido (sem alteração) |
| 252 | `tools/auditar_guia.py` | IDÊNTICO | Mantido (sem alteração) |
| 253 | `tools/install_dependencies.py` | IDÊNTICO | Mantido (sem alteração) |
| 254 | `tools/measure_etl_resources.py` | IDÊNTICO | Mantido (sem alteração) |
| 255 | `tools/nexo-motion/.gitignore` | IDÊNTICO | Mantido (sem alteração) |
| 256 | `tools/nexo-motion/.npmrc` | IDÊNTICO | Mantido (sem alteração) |
| 257 | `tools/nexo-motion/README.md` | IDÊNTICO | Mantido (sem alteração) |
| 258 | `tools/nexo-motion/VALIDATION.md` | IDÊNTICO | Mantido (sem alteração) |
| 259 | `tools/nexo-motion/package-lock.json` | IDÊNTICO | Mantido (sem alteração) |
| 260 | `tools/nexo-motion/package.json` | IDÊNTICO | Mantido (sem alteração) |
| 261 | `tools/nexo-motion/scripts/audio.py` | IDÊNTICO | Mantido (sem alteração) |
| 262 | `tools/nexo-motion/scripts/export.mjs` | IDÊNTICO | Mantido (sem alteração) |
| 263 | `tools/nexo-motion/scripts/render.mjs` | IDÊNTICO | Mantido (sem alteração) |
| 264 | `tools/nexo-motion/scripts/verify.mjs` | IDÊNTICO | Mantido (sem alteração) |
| 265 | `tools/nexo-motion/src/NexoFilm.tsx` | IDÊNTICO | Mantido (sem alteração) |
| 266 | `tools/nexo-motion/src/index.tsx` | IDÊNTICO | Mantido (sem alteração) |
| 267 | `tools/nexo-motion/src/scenes/Brand.tsx` | IDÊNTICO | Mantido (sem alteração) |
| 268 | `tools/nexo-motion/src/scenes/Dashboard.tsx` | IDÊNTICO | Mantido (sem alteração) |
| 269 | `tools/nexo-motion/src/scenes/Intelligence.tsx` | IDÊNTICO | Mantido (sem alteração) |
| 270 | `tools/nexo-motion/src/visual.tsx` | IDÊNTICO | Mantido (sem alteração) |
| 271 | `tools/nexo-motion/tsconfig.json` | IDÊNTICO | Mantido (sem alteração) |
| 272 | `uploads/.gitkeep` | IDÊNTICO | Mantido (sem alteração) |
| 273 | `wsgi.py` | IDÊNTICO | Mantido (sem alteração) |
