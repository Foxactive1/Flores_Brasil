from flask import request, jsonify, session
from models import db, Categoria, Produto, Cliente, LocalEntrega, Pedido, pedido_produto  # BUG FIX: pedido_produto adicionado ao import
from config import Config
import random
import string
from datetime import datetime


def register_routes(app):

    # ─────────────────────────────────────────────
    # UTILITÁRIOS INTERNOS
    # ─────────────────────────────────────────────

    def gerar_codigo_pedido():
        """Gera código único de 8 caracteres, verificando unicidade no banco."""
        # BUG FIX: versão anterior não verificava unicidade — colisão possível
        for _ in range(10):  # máximo 10 tentativas
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Pedido.query.filter_by(codigo=codigo).first():
                return codigo
        raise RuntimeError("Não foi possível gerar um código único para o pedido.")

    def calcular_taxa_entrega(subtotal):
        """Retorna 0 se subtotal atingir o limite de frete grátis, senão a taxa configurada."""
        if subtotal >= Config.ENTREGA_GRATIS_ACIMA:
            return 0.0
        return Config.ENTREGA_TAXA

    def gerar_mensagem_whatsapp(pedido):
        """Gera mensagem formatada para WhatsApp com os dados completos do pedido."""
        msg = "🌸 *FLORES BRASIL - NOVO PEDIDO* 🌸\n\n"
        msg += f"*Código:* #{pedido.codigo}\n"
        msg += f"*Status:* {pedido.status}\n\n"

        msg += "*📦 ITENS DO PEDIDO:*\n"
        for item in pedido.itens:
            # Buscar a quantidade na tabela associativa
            row = db.session.execute(
                pedido_produto.select().where(
                    pedido_produto.c.pedido_id == pedido.id,
                    pedido_produto.c.produto_id == item.id
                )
            ).first()
            quantidade = row.quantidade if row else 1
            preco_unit = row.preco_unitario if row else item.preco
            msg += f"{item.emoji} *{item.nome}* × {quantidade} — R$ {preco_unit * quantidade:.2f}\n"

        msg += "\n*💰 Resumo:*\n"
        msg += f"Subtotal: R$ {pedido.subtotal:.2f}\n"
        if pedido.taxa_entrega > 0:
            msg += f"Taxa de entrega: R$ {pedido.taxa_entrega:.2f}\n"
        else:
            msg += f"Entrega: *GRÁTIS* (acima de R$ {Config.ENTREGA_GRATIS_ACIMA:.2f})\n"
        msg += f"*TOTAL: R$ {pedido.total:.2f}*\n"

        if pedido.mensagem_cartao:
            msg += f"\n💌 *Mensagem no cartão:*\n\"{pedido.mensagem_cartao}\"\n"

        if pedido.observacao:
            msg += f"\n📝 *Observações:* {pedido.observacao}\n"

        if pedido.local_entrega:
            msg += f"\n📍 *Endereço de entrega:*\n{pedido.local_entrega.endereco_completo}\n"

        if pedido.cliente:
            msg += f"\n👤 *Cliente:* {pedido.cliente.nome}\n"
            msg += f"📞 *Telefone:* {pedido.cliente.telefone}\n"

        return msg

    # ─────────────────────────────────────────────
    # ROTAS — CATEGORIAS
    # ─────────────────────────────────────────────

    @app.route('/api/categorias', methods=['GET'])
    def get_categorias():
        """Retorna todas as categorias ativas."""
        categorias = Categoria.query.filter_by(ativo=True).all()
        return jsonify([c.to_dict() for c in categorias])

    # ─────────────────────────────────────────────
    # ROTAS — PRODUTOS
    # ─────────────────────────────────────────────

    @app.route('/api/produtos', methods=['GET'])
    def get_produtos():
        """Retorna produtos ativos, opcionalmente filtrados por slug de categoria."""
        categoria_slug = request.args.get('categoria')
        query = Produto.query.filter_by(ativo=True)

        if categoria_slug:
            categoria = Categoria.query.filter_by(slug=categoria_slug).first()
            if categoria:
                query = query.filter_by(categoria_id=categoria.id)

        produtos = query.all()
        return jsonify([p.to_dict() for p in produtos])

    @app.route('/api/produto/<int:id>', methods=['GET'])
    def get_produto(id):
        """Retorna um produto pelo ID ou 404."""
        produto = db.get_or_404(Produto, id)  # MELHORIA: get_or_404 atualizado para Flask-SQLAlchemy 3.x
        return jsonify(produto.to_dict())

    # ─────────────────────────────────────────────
    # ROTAS — CLIENTE
    # ─────────────────────────────────────────────

    @app.route('/api/cliente', methods=['POST'])
    def criar_cliente():
        """Cria ou recupera um cliente pelo telefone. Armazena ID na sessão."""
        data = request.get_json(silent=True) or {}

        # Validação básica
        if not data.get('nome') or not data.get('telefone'):
            return jsonify({'error': 'nome e telefone são obrigatórios'}), 400

        cliente = Cliente.query.filter_by(telefone=data['telefone']).first()

        if not cliente:
            cliente = Cliente(
                nome=data['nome'],
                email=data.get('email'),
                telefone=data['telefone']
            )
            db.session.add(cliente)
            db.session.commit()

        session['cliente_id'] = cliente.id
        return jsonify(cliente.to_dict())

    # ─────────────────────────────────────────────
    # ROTAS — LOCAL DE ENTREGA
    # ─────────────────────────────────────────────

    @app.route('/api/local-entrega', methods=['POST'])
    def criar_local_entrega():
        """Cria um local de entrega e armazena ID na sessão."""
        data = request.get_json(silent=True) or {}

        # Validação básica
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

    # ─────────────────────────────────────────────
    # ROTAS — PEDIDOS
    # ─────────────────────────────────────────────

    @app.route('/api/pedido', methods=['POST'])
    def criar_pedido():
        """Cria um novo pedido com cliente, endereço e produtos."""
        data = request.get_json(silent=True) or {}

        # ── 1. Resolver cliente ──────────────────
        cliente_id = session.get('cliente_id')
        if not cliente_id:
            cliente_data = data.get('cliente', {})
            if not cliente_data.get('nome') or not cliente_data.get('telefone'):
                return jsonify({'error': 'Dados do cliente (nome e telefone) são obrigatórios'}), 400

            # Reusar cliente existente pelo telefone para evitar duplicatas
            cliente = Cliente.query.filter_by(telefone=cliente_data['telefone']).first()
            if not cliente:
                cliente = Cliente(
                    nome=cliente_data['nome'],
                    telefone=cliente_data['telefone'],
                    email=cliente_data.get('email')
                )
                db.session.add(cliente)
                db.session.commit()
            cliente_id = cliente.id

        # ── 2. Resolver endereço ─────────────────
        local_entrega_id = session.get('local_entrega_id')
        if not local_entrega_id:
            end_data = data.get('local_entrega')
            if not end_data:
                return jsonify({'error': 'Endereço de entrega é obrigatório'}), 400

            # BUG FIX: versão anterior usava **end_data sem filtrar campos — risco de injeção de colunas inválidas
            local = LocalEntrega(
                logradouro=end_data.get('logradouro', ''),
                numero=end_data.get('numero', 'S/N'),
                complemento=end_data.get('complemento'),
                bairro=end_data.get('bairro', ''),
                cidade=end_data.get('cidade', 'Franca'),
                estado=end_data.get('estado', 'SP'),
                cep=end_data.get('cep', ''),
                referencia=end_data.get('referencia')
            )
            db.session.add(local)
            db.session.commit()
            local_entrega_id = local.id

        # ── 3. Validar produtos ──────────────────
        produtos_payload = data.get('produtos', [])
        if not produtos_payload:
            return jsonify({'error': 'O pedido deve conter ao menos um produto'}), 400

        # ── 4. Calcular subtotal ─────────────────
        subtotal = 0.0
        itens_validos = []
        for item in produtos_payload:
            produto = Produto.query.get(item.get('produto_id'))
            if produto and produto.ativo:
                qtd = max(int(item.get('quantidade', 1)), 1)
                subtotal += produto.preco * qtd
                itens_validos.append({'produto': produto, 'quantidade': qtd})

        if not itens_validos:
            return jsonify({'error': 'Nenhum produto válido encontrado no pedido'}), 400

        taxa_entrega = calcular_taxa_entrega(subtotal)

        # ── 5. Criar o pedido ────────────────────
        pedido = Pedido(
            codigo=gerar_codigo_pedido(),
            status='Pendente',
            subtotal=subtotal,
            taxa_entrega=taxa_entrega,
            total=subtotal + taxa_entrega,
            observacao=data.get('observacao'),
            mensagem_cartao=data.get('mensagem_cartao'),
            cliente_id=cliente_id,
            local_entrega_id=local_entrega_id
        )
        db.session.add(pedido)
        db.session.flush()  # obtém pedido.id antes do commit

        # ── 6. Inserir itens na tabela associativa ──
        for item in itens_validos:
            db.session.execute(
                pedido_produto.insert().values(
                    pedido_id=pedido.id,
                    produto_id=item['produto'].id,
                    quantidade=item['quantidade'],
                    preco_unitario=item['produto'].preco
                )
            )

        db.session.commit()

        # ── 7. Limpar sessão ─────────────────────
        session.pop('cliente_id', None)
        session.pop('local_entrega_id', None)

        return jsonify({
            'success': True,
            'pedido': pedido.to_dict(),
            'whatsapp_number': Config.WHATSAPP_NUMBER,       # MELHORIA: exposto para o frontend
            'whatsapp_message': gerar_mensagem_whatsapp(pedido)
        }), 201

    @app.route('/api/pedido/<codigo>', methods=['GET'])
    def get_pedido(codigo):
        """Retorna um pedido pelo código amigável."""
        pedido = Pedido.query.filter_by(codigo=codigo).first_or_404()
        return jsonify(pedido.to_dict())

    @app.route('/api/pedidos/cliente/<int:cliente_id>', methods=['GET'])
    def get_pedidos_cliente(cliente_id):
        """Retorna todos os pedidos de um cliente, do mais recente ao mais antigo."""
        pedidos = Pedido.query.filter_by(cliente_id=cliente_id)\
                              .order_by(Pedido.data_pedido.desc()).all()
        return jsonify([p.to_dict() for p in pedidos])

    @app.route('/api/pedido/<int:id>/status', methods=['PUT'])
    def atualizar_status(id):
        """Atualiza o status de um pedido pelo ID."""
        pedido = db.get_or_404(Pedido, id)
        data = request.get_json(silent=True) or {}
        novo_status = data.get('status')

        STATUS_VALIDOS = ['Pendente', 'Confirmado', 'Preparando', 'Saiu para Entrega', 'Entregue', 'Cancelado']

        if novo_status not in STATUS_VALIDOS:
            return jsonify({
                'error': 'Status inválido',
                'validos': STATUS_VALIDOS
            }), 400

        pedido.status = novo_status
        db.session.commit()
        return jsonify({'success': True, 'status': pedido.status})

    # ─────────────────────────────────────────────
    # HEALTH CHECK
    # ─────────────────────────────────────────────

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Endpoint de verificação de saúde da API."""
        return jsonify({'status': 'ok', 'message': 'Flores Brasil API está funcionando!'})
