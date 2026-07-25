"""
Rotas de Frontend — Flores Brasil
Blueprint principal para renderização de páginas HTML.
"""

from flask import Blueprint, render_template, redirect, url_for, request, session, current_app, jsonify
from functools import wraps
from models import db, Pedido

main_bp = Blueprint('main', __name__)


# ═══════════════════════════════════════════════════════════
# DECORATOR DE AUTENTICAÇÃO SIMPLES (Admin via Senha)
# ═══════════════════════════════════════════════════════════

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logado'):
            return redirect(url_for('main.admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════
# ROTAS PÚBLICAS
# ═══════════════════════════════════════════════════════════

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/parser')
def parser():
    return render_template('brasil_parser.html')

@main_bp.route('/checkout')
def checkout():
    codigo = request.args.get('codigo')
    if not codigo:
        return redirect(url_for('main.index'))
    pedido = Pedido.query.filter_by(codigo=codigo).first()
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('checkout.html', pedido=pedido)

@main_bp.route('/pedido/<codigo>')
def ver_pedido(codigo):
    pedido = Pedido.query.filter_by(codigo=codigo).first()
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('pedido.html', pedido=pedido)

@main_bp.route('/sucesso')
def sucesso():
    codigo = request.args.get('codigo')
    return render_template('sucesso.html', codigo=codigo)

@main_bp.route('/rastreio')
def rastreio():
    return render_template('rastreio.html')

# ─── ROTA PARA FAVICON ───
@main_bp.route('/favicon.ico')
def favicon():
    """Retorna 204 No Content para evitar erro 404."""
    return '', 204


# ═══════════════════════════════════════════════════════════
# ROTAS ADMINISTRATIVAS
# ═══════════════════════════════════════════════════════════

@main_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        senha = request.form.get('password', '')
        from config import Config
        if senha == Config.ADMIN_PASSWORD:
            session['admin_logado'] = True
            session.permanent = True
            next_url = request.args.get('next') or url_for('main.admin_dashboard')
            return redirect(next_url)
        else:
            return render_template('admin_login.html', erro='Senha incorreta.')
    if session.get('admin_logado'):
        return redirect(url_for('main.admin_dashboard'))
    return render_template('admin_login.html')

@main_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logado', None)
    return redirect(url_for('main.admin_login'))

@main_bp.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@main_bp.route('/admin/pedidos')
@admin_required
def admin_pedidos():
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 20
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return render_template('admin_pedidos.html', pedidos=pedidos)

@main_bp.route('/admin/pedido/<codigo>')
@admin_required
def admin_pedido_detalhe(codigo):
    pedido = Pedido.query.filter_by(codigo=codigo).first()
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('admin_pedido_detalhe.html', pedido=pedido)

@main_bp.route('/admin/ia-metrics')
@admin_required
def admin_ia_metrics():
    try:
        from metrics import metrics_collector
        resumo = metrics_collector.obter_resumo()
    except ImportError:
        resumo = {'error': 'Módulo de métricas não disponível'}
    return render_template('admin_ia_metrics.html', metrics=resumo)


# ═══════════════════════════════════════════════════════════
# ROTAS DE ERRO PERSONALIZADAS (com fallback)
# ═══════════════════════════════════════════════════════════

@main_bp.app_errorhandler(404)
def page_not_found(e):
    try:
        return render_template('404.html', mensagem='Página não encontrada'), 404
    except:
        return jsonify({'erro': 'Página não encontrada'}), 404

@main_bp.app_errorhandler(500)
def internal_error(e):
    try:
        return render_template('500.html'), 500
    except:
        return jsonify({'erro': 'Erro interno do servidor'}), 500