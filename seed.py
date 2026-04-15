# seed.py
from app import app
from models import db, Categoria, Produto

def seed_database():
    with app.app_context():
        print("🚀 Iniciando seed do banco...")

        # 🔎 Evitar duplicação
        if Categoria.query.first():
            print("⚠️ Banco já populado. Seed ignorado.")
            return

        # 📦 Categorias
        categorias = [
            Categoria(nome='Flores', slug='flores', icone='🌷'),
            Categoria(nome='Chocolates', slug='chocolates', icone='🍫'),
            Categoria(nome='Presentes', slug='presentes', icone='🎁'),
            Categoria(nome='Cartões', slug='cartoes', icone='💌')
        ]

        db.session.add_all(categorias)
        db.session.commit()

        print("✅ Categorias criadas")

        # 📦 Produtos
        produtos = [
            # Flores
            Produto(nome='Buquê de Rosas',
                    descricao='12 rosas vermelhas com acabamento premium',
                    preco=89.00, emoji='🌹', categoria_id=1),

            Produto(nome='Girassóis do Campo',
                    descricao='Arranjo com girassóis e folhagens naturais',
                    preco=79.00, emoji='🌻', categoria_id=1),

            Produto(nome='Orquídea Premium',
                    descricao='Orquídea branca em vaso decorativo',
                    preco=129.00, emoji='🌸', tag='Exclusivo', categoria_id=1),

            # Chocolates
            Produto(nome='Caixa de Trufas',
                    descricao='12 trufas artesanais',
                    preco=49.00, emoji='🍫', categoria_id=2),

            Produto(nome='Cesta Gourmet',
                    descricao='Mix de chocolates premium',
                    preco=89.00, emoji='🎁', tag='Mais Vendido', categoria_id=2),

            # Presentes
            Produto(nome='Urso Teddy',
                    descricao='Pelúcia 35cm',
                    preco=69.00, emoji='🧸', categoria_id=3),

            Produto(nome='Kit Velas Aromáticas',
                    descricao='Lavanda, baunilha e jasmim',
                    preco=59.00, emoji='🕯️', categoria_id=3),

            # Cartões
            Produto(nome='Cartão Personalizado',
                    descricao='Mensagem escrita à mão',
                    preco=15.00, emoji='💌', categoria_id=4),

            Produto(nome='Cartão Musical',
                    descricao='Cartão com som ao abrir',
                    preco=25.00, emoji='🎶', categoria_id=4),
        ]

        db.session.add_all(produtos)
        db.session.commit()

        print("✅ Produtos criados")
        print("🎯 Seed finalizado com sucesso!")

if __name__ == "__main__":
    seed_database()