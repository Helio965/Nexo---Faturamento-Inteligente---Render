"""Relação de tópicos do Guia com sinais de conteúdo de teste (somente leitura).

Gera, para revisão administrativa, a lista dos tópicos ATIVOS de `guia_topico`
que o detector conservador de `nexobot/higiene.py` marca como prováveis
conteúdos de teste (prefixo "ZZTEST", marcação HTML na categoria, categoria
"teste", textos de preenchimento...).

O script NÃO altera nada no banco. A desativação ou exclusão dos tópicos é
feita pela equipe no CMS (Base de Conhecimento), mediante autorização.

Uso (na raiz do repositório, com as variáveis de ambiente do banco desejado):
    python tools/auditar_guia.py            # tabela legível
    python tools/auditar_guia.py --json     # saída JSON para anexar ao chamado/relatório
    python tools/auditar_guia.py --todos    # inclui tópicos inativos
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="imprime JSON em vez de tabela")
    parser.add_argument("--todos", action="store_true", help="inclui tópicos inativos")
    args = parser.parse_args()

    from sqlalchemy import select
    from app import create_app
    from extensions import db
    from models import GuiaTopico
    from nexobot.higiene import motivo_teste

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    app.config["SQLALCHEMY_ECHO"] = False
    with app.app_context():
        consulta = select(GuiaTopico).order_by(GuiaTopico.categoria, GuiaTopico.id)
        if not args.todos:
            consulta = consulta.where(GuiaTopico.ativo.is_(True))
        topicos = db.session.execute(consulta).scalars().all()
        suspeitos = []
        for t in topicos:
            motivo = motivo_teste(t.categoria, t.pergunta, t.resposta)
            if motivo:
                suspeitos.append({
                    "id": t.id, "ativo": bool(t.ativo), "categoria": t.categoria,
                    "pergunta": t.pergunta, "motivo": motivo,
                    "acao_sugerida": "desativar ou excluir pelo CMS (Base de Conhecimento)",
                })
        db.session.rollback()  # nada foi escrito; libera a transação de leitura

    if args.json:
        print(json.dumps({"total_analisado": len(topicos), "suspeitos": suspeitos}, ensure_ascii=False, indent=2))
    else:
        print(f"Tópicos analisados: {len(topicos)} | com sinais de teste: {len(suspeitos)}")
        for item in suspeitos:
            estado = "ativo" if item["ativo"] else "inativo"
            print(f"- id={item['id']} [{estado}] categoria={item['categoria']!r} pergunta={item['pergunta']!r}")
            print(f"    motivo: {item['motivo']} | ação sugerida: {item['acao_sugerida']}")
        if not suspeitos:
            print("Nenhum tópico com sinais de teste.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
