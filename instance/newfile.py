# seed.py
from app import app
from models import db, Categoria, Produto

def seed_database():
    with app.app_context():
        print("🚀 Iniciando seed do banco...")

        # Evitar duplicação
        if Categoria.query.first():
            print("⚠️ Banco já populado. Seed ignorado.")
            return

        # 1. Criar categorias
        categorias_data = [
            {'nome': 'Flores', 'slug': 'flores', 'icone': '🌷'},
            {'nome': 'Chocolates', 'slug': 'chocolates', 'icone': '🍫'},
            {'nome': 'Presentes', 'slug': 'presentes', 'icone': '🎁'},
            {'nome': 'Cartões', 'slug': 'cartoes', 'icone': '💌'}
        ]

        categorias = []
        for data in categorias_data:
            cat = Categoria(**data)
            db.session.add(cat)
            categorias.append(cat)

        db.session.commit()  # Confirma para obter os IDs

        # Mapear slug -> ID
        slug_to_id = {cat.slug: cat.id for cat in categorias}

        print("✅ Categorias criadas")

        # 2. Produtos (usando os IDs reais)
        produtos = [
            # Flores (slug: flores)
            Produto(nome='Buquê de Rosas',
                    descricao='12 rosas vermelhas com acabamento premium',
                    preco=89.00, emoji='🌹', categoria_id=slug_to_id['flores']),

            Produto(nome='Girassóis do Campo',
                    descricao='Arranjo com girassóis e folhagens naturais',
                    preco=79.00, emoji='🌻', categoria_id=slug_to_id['flores']),

            Produto(nome='Orquídea Premium',
                    descricao='Orquídea branca em vaso decorativo',
                    preco=129.00, emoji='🌸', tag='Exclusivo', categoria_id=slug_to_id['flores']),

            # Chocolates
            Produto(nome='Caixa de Trufas',
                    descricao='12 trufas artesanais',
                    preco=49.00, emoji='🍫', categoria_id=slug_to_id['chocolates']),

            Produto(nome='Cesta Gourmet',
                    descricao='Mix de chocolates premium',
                    preco=89.00, emoji='🎁', tag='Mais Vendido', categoria_id=slug_to_id['chocolates']),

            # Presentes
            Produto(nome='Urso Teddy',
                    descricao='Pelúcia 35cm',
                    preco=69.00, emoji='🧸', categoria_id=slug_to_id['presentes']),

            Produto(nome='Kit Velas Aromáticas',
                    descricao='Lavanda, baunilha e jasmim',
                    preco=59.00, emoji='🕯️', categoria_id=slug_to_id['presentes']),

            # Cartões
            Produto(nome='Cartão Personalizado',
                    descricao='Mensagem escrita à mão',
                    preco=15.00, emoji='💌', categoria_id=slug_to_id['cartoes']),

            Produto(nome='Cartão Musical',
                    descricao='Cartão com som ao abrir',
                    preco=25.00, emoji='🎶', categoria_id=slug_to_id['cartoes']),
        ]

        db.session.add_all(produtos)
        db.session.commit()

        print("✅ Produtos criados")
        print("🎯 Seed finalizado com sucesso!")

if __name__ == "__main__":
    seed_database()