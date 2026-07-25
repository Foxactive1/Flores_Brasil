from flask import Flask
from config import Config
from models import db
from blueprints.api import api_bp
from routes import main_bp   # agora usamos routes.py como blueprint principal
import logging
from logging.handlers import RotatingFileHandler
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Configuração de logging (se não estiver em modo debug)
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/flores_brasil.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Flores Brasil startup')

    # Registro dos blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)  # rotas raiz (/, /admin, etc.)

    return app

app = create_app()

def init_db():
    """
    Inicializa o banco de dados e insere dados iniciais (seed),
    se a tabela de categorias estiver vazia.
    """
    with app.app_context():
        db.create_all()

        # Seed de categorias e produtos (exemplo)
        from models import Categoria, Produto
        if Categoria.query.count() == 0:
            categorias = [
                {'nome': 'Flores', 'slug': 'flores', 'icone': '🌸'},
                {'nome': 'Chocolates', 'slug': 'chocolates', 'icone': '🍫'},
                {'nome': 'Presentes', 'slug': 'presentes', 'icone': '🎁'},
                {'nome': 'Cartões', 'slug': 'cartoes', 'icone': '💌'},
            ]
            for cat in categorias:
                c = Categoria(**cat)
                db.session.add(c)
            db.session.commit()

            # Produtos de exemplo
            produtos = [
                {'nome': 'Buquê de Rosas', 'descricao': 'Clássico buquê de rosas vermelhas', 'preco': 89.00, 'emoji': '🌹', 'categoria_slug': 'flores'},
                {'nome': 'Girassóis do Campo', 'descricao': 'Buquê vibrante de girassóis', 'preco': 79.00, 'emoji': '🌻', 'categoria_slug': 'flores'},
                {'nome': 'Orquídea Phalaenopsis', 'descricao': 'Orquídea branca em vaso', 'preco': 129.00, 'emoji': '🌸', 'categoria_slug': 'flores'},
                {'nome': 'Trufas Selecionadas', 'descricao': 'Caixa com 12 trufas artesanais', 'preco': 49.00, 'emoji': '🍫', 'categoria_slug': 'chocolates'},
                {'nome': 'Cesta de Chocolates', 'descricao': 'Cesta com variedade de chocolates', 'preco': 79.00, 'emoji': '🧺', 'categoria_slug': 'chocolates'},
                {'nome': 'Urso Teddy Rosa', 'descricao': 'Urso de pelúcia rosa 30cm', 'preco': 69.00, 'emoji': '🧸', 'categoria_slug': 'presentes'},
                {'nome': 'Kit Velas Aromáticas', 'descricao': 'Kit com 3 velas perfumadas', 'preco': 59.00, 'emoji': '🕯️', 'categoria_slug': 'presentes'},
                {'nome': 'Cartão Personalizado', 'descricao': 'Cartão com mensagem personalizada', 'preco': 15.00, 'emoji': '💌', 'categoria_slug': 'cartoes'},
            ]
            for p in produtos:
                cat = Categoria.query.filter_by(slug=p.pop('categoria_slug')).first()
                if cat:
                    prod = Produto(categoria_id=cat.id, **p)
                    db.session.add(prod)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)