import random
import string
from datetime import datetime, timezone
from models import db, Pedido, ItemPedido, Cliente, LocalEntrega, Produto
from config import Config

def gerar_codigo_pedido():
    for _ in range(10):
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not Pedido.query.filter_by(codigo=codigo).first():
            return codigo
    raise RuntimeError("Não foi possível gerar código único.")

def calcular_taxa_entrega(subtotal):
    return 0.0 if subtotal >= Config.ENTREGA_GRATIS_ACIMA else Config.ENTREGA_TAXA

def criar_pedido(cliente_data, endereco_data, produtos_data, observacao=None, mensagem_cartao=None):
    # Cliente
    cliente = Cliente.query.filter_by(telefone=cliente_data['telefone']).first()
    if not cliente:
        cliente = Cliente(
            nome=cliente_data['nome'],
            email=cliente_data.get('email'),
            telefone=cliente_data['telefone']
        )
        db.session.add(cliente)
        db.session.flush()

    # Endereço
    local = LocalEntrega(
        logradouro=endereco_data['logradouro'],
        numero=endereco_data.get('numero', 'S/N'),
        complemento=endereco_data.get('complemento'),
        bairro=endereco_data['bairro'],
        cidade=endereco_data.get('cidade', 'Franca'),
        estado=endereco_data.get('estado', 'SP'),
        cep=endereco_data.get('cep', ''),
        referencia=endereco_data.get('referencia')
    )
    db.session.add(local)
    db.session.flush()

    # Validar e calcular itens
    subtotal = 0.0
    itens_validos = []
    for item in produtos_data:
        produto = Produto.query.get(item.get('produto_id'))
        if produto and produto.ativo:
            qtd = max(int(item.get('quantidade', 1)), 1)
            subtotal += produto.preco * qtd
            itens_validos.append({'produto': produto, 'quantidade': qtd})

    if not itens_validos:
        raise ValueError("Nenhum produto válido.")

    taxa_entrega = calcular_taxa_entrega(subtotal)

    pedido = Pedido(
        codigo=gerar_codigo_pedido(),
        status='Pendente',
        subtotal=subtotal,
        taxa_entrega=taxa_entrega,
        total=subtotal + taxa_entrega,
        observacao=observacao,
        mensagem_cartao=mensagem_cartao,
        cliente_id=cliente.id,
        local_entrega_id=local.id
    )
    db.session.add(pedido)
    db.session.flush()

    # Itens
    for item in itens_validos:
        item_pedido = ItemPedido(
            pedido_id=pedido.id,
            produto_id=item['produto'].id,
            quantidade=item['quantidade'],
            preco_unitario=item['produto'].preco
        )
        db.session.add(item_pedido)

    db.session.commit()
    return pedido

def gerar_mensagem_whatsapp(pedido):
    """
    Gera mensagem formatada para WhatsApp com os dados completos do pedido.
    """
    msg = "🌸 *FLORES BRASIL - NOVO PEDIDO* 🌸\n\n"
    msg += f"*Código:* #{pedido.codigo}\n"
    msg += f"*Status:* {pedido.status}\n\n"

    msg += "*📦 ITENS DO PEDIDO:*\n"
    for item in pedido.itens:
        produto = item.produto
        msg += f"{produto.emoji} *{produto.nome}* × {item.quantidade} — R$ {item.preco_unitario * item.quantidade:.2f}\n"

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