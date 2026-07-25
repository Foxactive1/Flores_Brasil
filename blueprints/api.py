from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy import func
from models import db, Categoria, Produto, Cliente, LocalEntrega, Pedido, ItemPedido
from ai_service import parsear_mensagem, GROQ_MODEL, logger
from config import Config
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ──────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES (movidas de services.pedido_service)
# ──────────────────────────────────────────────────────────────

def gerar_mensagem_whatsapp(pedido):
    """Gera mensagem formatada para WhatsApp com os dados completos do pedido."""
    msg = "🌸 *FLORES BRASIL - NOVO PEDIDO* 🌸\n\n"
    msg += f"*Código:* #{pedido.codigo}\n"
    msg += f"*Status:* {pedido.status}\n\n"

    msg += "*📦 ITENS DO PEDIDO:*\n"
    for item in pedido.itens:  # item é um ItemPedido
        produto = item.produto
        subtotal = item.preco_unitario * item.quantidade
        msg += f"{produto.emoji} *{produto.nome}* × {item.quantidade} — R$ {subtotal:.2f}\n"

    msg += "\n*💰 Resumo:*\n"
    msg += f"Subtotal: R$ {pedido.subtotal:.2f}\n"
    if pedido.taxa_entrega > 0:
        msg += f"Taxa de entrega: R$ {pedido.taxa_entrega:.2f}\n"
    else:
        msg += f"Entrega: *GRÁTIS* (acima de R$ {Config.ENTREGA_GRATIS_ACIMA:.2f})\n"
    msg += f"*TOTAL: R$ {pedido.total:.2f}*\n"

    if pedido.mensagem_cartao:
        msg += f'\n💌 *Mensagem no cartão:*\n"{pedido.mensagem_cartao}"\n'

    if pedido.observacao:
        msg += f"\n📝 *Observações:* {pedido.observacao}\n"

    if pedido.local_entrega:
        msg += f"\n📍 *Endereço de entrega:*\n{pedido.local_entrega.endereco_completo}\n"

    if pedido.cliente:
        msg += f"\n👤 *Cliente:* {pedido.cliente.nome}\n"
        msg += f"📞 *Telefone:* {pedido.cliente.telefone}\n"

    return msg


def criar_pedido(cliente_data, endereco_data, produtos_data, observacao=None, mensagem_cartao=None):
    """
    Cria um novo pedido com validações e cálculo de valores.
    Retorna o objeto Pedido salvo.
    """
    from config import Config

    # 1. Validações básicas
    if not produtos_data:
        raise ValueError("Nenhum produto informado")

    # 2. Processar cliente (cria ou busca)
    telefone = cliente_data.get('telefone')
    cliente = Cliente.query.filter_by(telefone=telefone).first()
    if not cliente:
        cliente = Cliente(
            nome=cliente_data.get('nome'),
            email=cliente_data.get('email'),
            telefone=telefone
        )
        db.session.add(cliente)
        db.session.flush()

    # 3. Processar endereço de entrega
    local = LocalEntrega(
        logradouro=endereco_data.get('logradouro'),
        numero=endereco_data.get('numero', 'S/N'),
        complemento=endereco_data.get('complemento'),
        bairro=endereco_data.get('bairro'),
        cidade=endereco_data.get('cidade', 'Franca'),
        estado=endereco_data.get('estado', 'SP'),
        cep=endereco_data.get('cep'),
        referencia=endereco_data.get('referencia')
    )
    db.session.add(local)
    db.session.flush()

    # 4. Validar produtos e calcular subtotal
    itens_validos = []
    subtotal = 0.0
    for item_data in produtos_data:
        produto_id = item_data.get('produto_id')
        quantidade = item_data.get('quantidade', 1)
        if not produto_id:
            continue
        produto = Produto.query.get(produto_id)
        if not produto or not produto.ativo:
            raise ValueError(f"Produto ID {produto_id} não encontrado ou inativo")
        if produto.estoque is not None and produto.estoque < quantidade:
            raise ValueError(f"Estoque insuficiente para {produto.nome}")
        preco = produto.preco
        subtotal += preco * quantidade
        itens_validos.append({
            'produto': produto,
            'quantidade': quantidade,
            'preco_unitario': preco
        })

    # 5. Calcular taxa de entrega
    taxa_entrega = Config.TAXA_ENTREGA_PADRAO
    if subtotal >= Config.ENTREGA_GRATIS_ACIMA:
        taxa_entrega = 0.0

    total = subtotal + taxa_entrega

    # 6. Criar pedido
    pedido = Pedido(
        cliente_id=cliente.id,
        local_entrega_id=local.id,
        subtotal=subtotal,
        taxa_entrega=taxa_entrega,
        total=total,
        observacao=observacao,
        mensagem_cartao=mensagem_cartao,
        status='Pendente'
    )
    db.session.add(pedido)
    db.session.flush()  # para obter o id

    # 7. Criar itens do pedido usando ItemPedido
    for item in itens_validos:
        item_pedido = ItemPedido(
            pedido_id=pedido.id,
            produto_id=item['produto'].id,
            quantidade=item['quantidade'],
            preco_unitario=item['preco_unitario']
        )
        db.session.add(item_pedido)

    # 8. Atualizar estoque (se controlado)
    for item in itens_validos:
        if item['produto'].estoque is not None:
            item['produto'].estoque -= item['quantidade']

    db.session.commit()
    return pedido


# ──────────────────────────────────────────────────────────────
# ROTAS EXISTENTES (com correções)
# ──────────────────────────────────────────────────────────────

@api_bp.route('/categorias', methods=['GET'])
def get_categorias():
    categorias = Categoria.query.filter_by(ativo=True).all()
    return jsonify([c.to_dict() for c in categorias])


@api_bp.route('/produtos', methods=['GET'])
def get_produtos():
    categoria_slug = request.args.get('categoria')
    query = Produto.query.filter_by(ativo=True)
    if categoria_slug:
        categoria = Categoria.query.filter_by(slug=categoria_slug).first()
        if categoria:
            query = query.filter_by(categoria_id=categoria.id)
    produtos = query.all()
    return jsonify([p.to_dict() for p in produtos])


@api_bp.route('/produto/<int:id>', methods=['GET'])
def get_produto(id):
    produto = db.get_or_404(Produto, id)
    return jsonify(produto.to_dict())


@api_bp.route('/cliente', methods=['POST'])
def criar_cliente():
    data = request.get_json(silent=True) or {}
    if not data.get('nome') or not data.get('telefone'):
        return jsonify({'error': 'nome e telefone são obrigatórios'}), 400
    cliente = Cliente.query.filter_by(telefone=data['telefone']).first()
    if not cliente:
        cliente = Cliente(nome=data['nome'], email=data.get('email'), telefone=data['telefone'])
        db.session.add(cliente)
        db.session.commit()
    session['cliente_id'] = cliente.id
    return jsonify(cliente.to_dict())


@api_bp.route('/local-entrega', methods=['POST'])
def criar_local_entrega():
    data = request.get_json(silent=True) or {}
    if not data.get('logradouro') or not data.get('bairro') or not data.get('cep'):
        return jsonify({'error': 'logradouro, bairro e cep são obrigatórios'}), 400
    local = LocalEntrega(
        logradouro=data['logradouro'],
        numero=data.get('numero', 'S/N'),
        complemento=data.get('complemento'),
        bairro=data['bairro'],
        cidade=data.get('cidade', 'Franca'),
        estado=data.get('estado', 'SP'),
        cep=data['cep'],
        referencia=data.get('referencia')
    )
    db.session.add(local)
    db.session.commit()
    session['local_entrega_id'] = local.id
    return jsonify(local.to_dict())


@api_bp.route('/pedido', methods=['POST'])
def criar_pedido_endpoint():
    data = request.get_json(silent=True) or {}
    cliente_data = data.get('cliente')
    endereco_data = data.get('local_entrega')
    produtos_data = data.get('produtos')
    if not cliente_data or not endereco_data or not produtos_data:
        return jsonify({'error': 'Dados incompletos'}), 400

    try:
        pedido = criar_pedido(
            cliente_data=cliente_data,
            endereco_data=endereco_data,
            produtos_data=produtos_data,
            observacao=data.get('observacao'),
            mensagem_cartao=data.get('mensagem_cartao')
        )
        mensagem = gerar_mensagem_whatsapp(pedido)
        return jsonify({
            'success': True,
            'pedido': pedido.to_dict(),
            'whatsapp_number': Config.WHATSAPP_NUMBER,
            'whatsapp_message': mensagem
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_bp.route('/pedido/<codigo>', methods=['GET'])
def get_pedido(codigo):
    pedido = Pedido.query.filter_by(codigo=codigo).first_or_404()
    return jsonify(pedido.to_dict())


@api_bp.route('/pedidos/cliente/<int:cliente_id>', methods=['GET'])
def get_pedidos_cliente(cliente_id):
    pedidos = Pedido.query.filter_by(cliente_id=cliente_id).order_by(Pedido.data_pedido.desc()).all()
    return jsonify([p.to_dict() for p in pedidos])


@api_bp.route('/pedido/<int:id>/status', methods=['PUT'])
def atualizar_status(id):
    pedido = db.get_or_404(Pedido, id)
    data = request.get_json(silent=True) or {}
    novo_status = data.get('status')
    STATUS_VALIDOS = ['Pendente', 'Confirmado', 'Preparando', 'Saiu para Entrega', 'Entregue', 'Cancelado']
    if novo_status not in STATUS_VALIDOS:
        return jsonify({'error': 'Status inválido', 'validos': STATUS_VALIDOS}), 400
    pedido.status = novo_status
    db.session.commit()
    return jsonify({'success': True, 'status': pedido.status})


@api_bp.route('/parse-mensagem', methods=['POST'])
def parse_mensagem():
    data = request.get_json()
    mensagem = data.get('mensagem', '').strip()
    if not mensagem:
        return jsonify({'success': False, 'error': 'Mensagem vazia'}), 400
    if len(mensagem) > 5000:
        return jsonify({'success': False, 'error': 'Mensagem muito longa'}), 400
    try:
        resultado = parsear_mensagem(mensagem)
        return jsonify({
            'success': True,
            'pedido': resultado,
            'meta': {
                'modelo_usado': GROQ_MODEL,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Erro ao parsear: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'API funcionando'})


# ──────────────────────────────────────────────────────────────
# NOVAS ROTAS ADICIONADAS
# ──────────────────────────────────────────────────────────────

@api_bp.route('/pedidos', methods=['GET'])
def listar_pedidos():
    """
    Lista pedidos com paginação e filtros.
    Uso: /api/pedidos?status=Pendente&pagina=1&por_pagina=20
    """
    status = request.args.get('status')
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = request.args.get('por_pagina', 20, type=int)

    query = Pedido.query.order_by(Pedido.data_pedido.desc())

    if status:
        query = query.filter_by(status=status)

    paginacao = query.paginate(
        page=pagina,
        per_page=min(por_pagina, 100),
        error_out=False
    )

    return jsonify({
        'success': True,
        'pedidos': [p.to_dict() for p in paginacao.items],
        'paginacao': {
            'pagina_atual': paginacao.page,
            'total_paginas': paginacao.pages,
            'total_itens': paginacao.total,
            'por_pagina': por_pagina
        }
    })


@api_bp.route('/estatisticas', methods=['GET'])
def estatisticas():
    """
    Estatísticas agregadas da loja (últimos 30 dias).
    """
    trinta_dias_atras = datetime.utcnow() - timedelta(days=30)

    total_pedidos = Pedido.query.filter(
        Pedido.data_pedido >= trinta_dias_atras
    ).count()

    faturamento = db.session.query(
        func.sum(Pedido.total)
    ).filter(
        Pedido.data_pedido >= trinta_dias_atras,
        Pedido.status != 'Cancelado'
    ).scalar() or 0.0

    pedidos_por_status = db.session.query(
        Pedido.status,
        func.count(Pedido.id)
    ).filter(
        Pedido.data_pedido >= trinta_dias_atras
    ).group_by(Pedido.status).all()

    total_clientes = Cliente.query.count()

    return jsonify({
        'success': True,
        'periodo': 'últimos 30 dias',
        'total_pedidos': total_pedidos,
        'faturamento': round(faturamento, 2),
        'total_clientes': total_clientes,
        'pedidos_por_status': {
            status: count for status, count in pedidos_por_status
        }
    })


@api_bp.route('/pedido/<codigo>/cancelar', methods=['POST'])
def cancelar_pedido(codigo):
    """
    Permite ao cliente cancelar um pedido Pendente.
    Requer código do pedido + telefone para verificação.
    """
    data = request.get_json(silent=True) or {}
    telefone = data.get('telefone', '').strip()

    if not telefone:
        return jsonify({
            'success': False,
            'error': 'Telefone é obrigatório para cancelar o pedido'
        }), 400

    pedido = Pedido.query.filter_by(codigo=codigo).first()
    if not pedido:
        return jsonify({
            'success': False,
            'error': 'Pedido não encontrado'
        }), 404

    if not pedido.cliente or pedido.cliente.telefone != telefone:
        return jsonify({
            'success': False,
            'error': 'Telefone não corresponde ao cliente do pedido'
        }), 403

    if pedido.status != 'Pendente':
        return jsonify({
            'success': False,
            'error': f'Pedido com status "{pedido.status}" não pode ser cancelado'
        }), 400

    pedido.status = 'Cancelado'
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Pedido cancelado com sucesso',
        'pedido': pedido.to_dict()
    })


@api_bp.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    """
    Recebe notificações de pagamento do Mercado Pago.
    Atualiza status do pedido automaticamente.
    """
    logger = logging.getLogger(__name__)
    data = request.get_json(silent=True) or {}
    logger.info(f"[Webhook MP] Recebido: {data}")

    action = data.get('action')
    payment_data = data.get('data', {})
    payment_id = payment_data.get('id')

    if action not in ('payment.updated', 'payment.created'):
        return jsonify({'status': 'ignored'}), 200

    logger.info(f"[Webhook MP] Payment ID: {payment_id}")
    # TODO: Implementar consulta à API do MP e atualização do pedido

    return jsonify({'status': 'received'}), 200


@api_bp.route('/rastrear/<codigo>', methods=['GET'])
def rastrear_pedido(codigo):
    """
    Endpoint público para cliente rastrear seu pedido.
    Retorna status atual e histórico.
    """
    pedido = Pedido.query.filter_by(codigo=codigo).first()
    if not pedido:
        return jsonify({
            'success': False,
            'error': 'Pedido não encontrado'
        }), 404

    timeline = [
        {
            'status': 'Pendente',
            'descricao': 'Pedido recebido e aguardando pagamento',
            'data': pedido.data_pedido.isoformat(),
            'ativo': pedido.status == 'Pendente'
        }
    ]

    status_ordem = ['Pendente', 'Confirmado', 'Preparando', 'Saiu para Entrega', 'Entregue']
    if pedido.status in status_ordem:
        idx = status_ordem.index(pedido.status)
        if idx >= 1:
            timeline.append({
                'status': 'Confirmado',
                'descricao': 'Pagamento confirmado',
                'ativo': pedido.status == 'Confirmado'
            })
        if idx >= 2:
            timeline.append({
                'status': 'Preparando',
                'descricao': 'Seu pedido está sendo preparado com carinho 🌸',
                'ativo': pedido.status == 'Preparando'
            })
        if idx >= 3:
            timeline.append({
                'status': 'Saiu para Entrega',
                'descricao': 'Pedido saiu para entrega',
                'ativo': pedido.status == 'Saiu para Entrega'
            })
        if idx >= 4:
            timeline.append({
                'status': 'Entregue',
                'descricao': 'Pedido entregue com sucesso! 🎉',
                'ativo': True
            })

    return jsonify({
        'success': True,
        'pedido': {
            'codigo': pedido.codigo,
            'status': pedido.status,
            'total': pedido.total,
            'data_pedido': pedido.data_pedido.isoformat()
        },
        'timeline': timeline
    })


@api_bp.route('/ia/metrics', methods=['GET'])
def ia_metrics():
    """
    Retorna métricas do parser de IA.
    Em produção, proteger com JWT.
    """
    try:
        from metrics import metrics_collector
        resumo = metrics_collector.obter_resumo()
        return jsonify({
            'success': True,
            'metrics': resumo
        })
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Módulo de métricas não disponível'
        }), 503