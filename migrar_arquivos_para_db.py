"""
NEXO - Migra arquivos do disco local para o banco (tabela arquivo_armazenado)
=============================================================================
Uploads feitos antes do storage no banco guardam em `caminho_arquivo` um path
do filesystem local — que NÃO existe no servidor de produção (Render tem disco
efêmero e os uploads nem vão para o Git). Este script lê cada arquivo legado
nesta máquina, grava os bytes no banco e troca a referência para 'db:<nome>'.
Vale para planilhas (upload_relatorio) e imagens do Guia (guia_topico).

Idempotente: referências já no formato 'db:' são ignoradas. Confere o SHA-256
de cada planilha contra o hash gravado no upload antes de migrar.

Uso (na máquina que tem a pasta uploads/ original):
    python migrar_arquivos_para_db.py            # simula, sem gravar
    python migrar_arquivos_para_db.py --dry-run  # simulação explícita
    python migrar_arquivos_para_db.py --apply    # migra e comita

Confira DATABASE_URL e FLASK_ENV antes da execução. Se qualquer arquivo faltar
ou divergir do hash, nenhuma migração é commitada. Os arquivos de origem são
preservados em todos os modos.
"""
import argparse
import sys

import hashlib
import os

from sqlalchemy import select

from app import create_app
from extensions import db
from models import UploadRelatorio, GuiaTopico
import storage


def _nome(caminho: str) -> str:
    return os.path.basename(caminho.replace("\\", "/"))


def main(dry_run: bool = True) -> int:
    app = create_app()
    app.config["SQLALCHEMY_ECHO"] = False
    migrados, faltando, ignorados = 0, 0, 0
    with app.app_context():
        db.engine.echo = False

        uploads = db.session.execute(select(UploadRelatorio)).scalars().all()
        for up in uploads:
            if up.caminho_arquivo.startswith(storage.PREFIXO_DB):
                ignorados += 1
                continue
            caminho = storage.resolver(up.caminho_arquivo)
            if not os.path.exists(caminho):
                print(f"❌ upload {up.id_upload}: arquivo não encontrado ({caminho})")
                faltando += 1
                continue
            with open(caminho, "rb") as arquivo:
                conteudo = arquivo.read()
            if up.hash_arquivo and hashlib.sha256(conteudo).hexdigest() != up.hash_arquivo:
                print(f"❌ upload {up.id_upload}: SHA-256 diverge do registrado — não migrado")
                faltando += 1
                continue
            nome = _nome(up.caminho_arquivo)
            print(f"✅ upload {up.id_upload}: {nome} ({len(conteudo)} bytes)")
            if not dry_run:
                up.caminho_arquivo = storage.salvar(conteudo, nome)
            migrados += 1

        pasta_static = app.static_folder
        topicos = db.session.execute(
            select(GuiaTopico).where(GuiaTopico.imagem_url.is_not(None))
        ).scalars().all()
        for t in topicos:
            if t.imagem_url.startswith(storage.PREFIXO_DB):
                ignorados += 1
                continue
            caminho = os.path.join(pasta_static, t.imagem_url)
            if not os.path.exists(caminho):
                print(f"❌ guia {t.id}: imagem não encontrada ({caminho})")
                faltando += 1
                continue
            with open(caminho, "rb") as arquivo:
                conteudo = arquivo.read()
            nome = f"guia/{_nome(t.imagem_url)}"
            print(f"✅ guia {t.id}: {nome} ({len(conteudo)} bytes)")
            if not dry_run:
                t.imagem_url = storage.salvar(conteudo, nome)
            migrados += 1

        if dry_run or faltando:
            db.session.rollback()
        else:
            db.session.commit()

    if dry_run:
        modo = "SIMULAÇÃO (nada gravado)"
    elif faltando:
        modo = "CANCELADO (rollback; nada gravado)"
    else:
        modo = "gravado no banco"
    print(f"\n{migrados} apto(s) à migração, {ignorados} já no banco, {faltando} com problema — {modo}.")
    return 1 if faltando else 0


def cli(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--dry-run", action="store_true", help="Simula sem gravar (padrão).")
    modo.add_argument("--apply", action="store_true", help="Aplica somente se todos os arquivos forem válidos.")
    args = parser.parse_args(argv)
    return main(dry_run=not args.apply)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(cli())
