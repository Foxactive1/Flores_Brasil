from flask import Flask, render_template, session
from config import Config
from models import db
from routes import register_routes
import os

# ─────────────────────────────────────────────────────────────
# CRIAR APLICAÇÃO
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

# MELHORIA: SESSION_TYPE 'filesystem' removido — requer flask-session que não está
# no requirements padrão. A sessão padrão do Flask (cookie seguro) é suficiente aqui.
# Se quiser sessão server-side, instale: pip install flask-session  e descomente abaixo:
# app.config['SESSION_TYPE'] = 'filesystem'

# Inicializar banco de dados
db.init_app(app)

# Registrar rotas da API
register_routes(app)


# ─────────────────────────────────────────────────────────────
# ROTAS PRINCIPAIS
# ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve o frontend principal."""
    return render_template('index.html')


@app.route('/admin')
def admin():
    """Painel administrativo simples — exibe os últimos 20 pedidos."""
    # MELHORIA: imports movidos para o topo da função para clareza
    from models import Pedido
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).limit(20).all()
    return render_template('admin.html', pedidos=pedidos)


# ─────────────────────────────────────────────────────────────
# INICIALIZAÇÃO DO BANCO
# ─────────────────────────────────────────────────────────────

def init_db():
    """Cria as tabelas e popula os dados iniciais se o banco estiver vazio."""
    # BUG FIX: imports locais garantem que os modelos estejam disponíveis
    # independente de como init_db() é chamada (CLI, testes, __main__)
    from models import Categoria, Produto, Cliente, LocalEntrega, Pedido, pedido_produto

    with app.app_context():
        db.create_all()

        if Categoria.query.count() == 0:
            # Criar categorias
            categorias = [
                Categoria(nome='Flores',     slug='flores',     icone='🌷'),
                Categoria(nome='Chocolates', slug='chocolates', icone='🍫'),
                Categoria(nome='Presentes',  slug='presentes',  icone='🎁'),
                Categoria(nome='Cartões',    slug='cartoes',    icone='💌'),
            ]
            db.session.add_all(categorias)
            db.session.commit()

            # Recarregar para obter IDs
            flores_id     = Categoria.query.filter_by(slug='flores').first().id
            chocolates_id = Categoria.query.filter_by(slug='chocolates').first().id
            presentes_id  = Categoria.query.filter_by(slug='presentes').first().id
            cartoes_id    = Categoria.query.filter_by(slug='cartoes').first().id

            produtos = [
                # Flores
                Produto(nome='Buquê de Rosas',
                        descricao='12 rosas vermelhas, folhagens verdes e laço de cetim.',
                        preco=89.00, emoji='🌹', categoria_id=flores_id),
                Produto(nome='Girassóis do Campo',
                        descricao='5 girassóis com ramos de eucalipto, jarra de vidro inclusa.',
                        preco=79.00, emoji='🌻', categoria_id=flores_id),
                Produto(nome='Orquídea Phalaenopsis',
                        descricao='Vaso decorativo com orquídea branca, duração de 3 meses.',
                        preco=129.00, emoji='🌸', tag='Exclusivo', categoria_id=flores_id),
                Produto(nome='Arranjo Misto',
                        descricao='Lírios, margaridas e cravos em caixa elegante.',
                        preco=99.00, emoji='💐', categoria_id=flores_id),
                Produto(nome='Buquê Tropical',
                        descricao='Estrelícias, helicônias e folhagens exóticas.',
                        preco=119.00, emoji='🌺', tag='Exclusivo', categoria_id=flores_id),
                # Chocolates
                Produto(nome='Trufas Selecionadas',
                        descricao='Caixa com 12 trufas artesanais (chocolate belga).',
                        preco=49.00, emoji='🍫', categoria_id=chocolates_id),
                Produto(nome='Cesta de Chocolates',
                        descricao='Bombons variados + barra de chocolate 70% cacau.',
                        preco=79.00, emoji='🧺', categoria_id=chocolates_id),  # MELHORIA: emoji 🎄 substituído por 🧺
                # Presentes
                Produto(nome='Urso Teddy Rosa',
                        descricao='Urso de pelúcia 35cm com laço e cartão.',
                        preco=69.00, emoji='🧸', categoria_id=presentes_id),
                Produto(nome='Kit Velas Aromáticas',
                        descricao='3 velas perfumadas (lavanda, baunilha e jasmim).',
                        preco=59.00, emoji='🕯️', categoria_id=presentes_id),
                # Cartões
                Produto(nome='Cartão Personalizado',
                        descricao='Mensagem escrita à mão em cartão premium.',
                        preco=15.00, emoji='💌', categoria_id=cartoes_id),
                Produto(nome='Cartão Musical',
                        descricao='Toca "Parabéns pra Você" ao abrir.',
                        preco=25.00, emoji='🎵', categoria_id=cartoes_id),  # MELHORIA: emoji 🎨 → 🎵 (mais semântico)
            ]
            db.session.add_all(produtos)
            db.session.commit()
            print("✅ Banco de dados inicializado com categorias e produtos!")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
