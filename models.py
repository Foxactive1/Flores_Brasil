from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Categoria(db.Model):
    __tablename__ = 'categoria'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    icone = db.Column(db.String(10), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    produtos = db.relationship('Produto', backref='categoria', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'slug': self.slug,
            'icone': self.icone
        }

class Produto(db.Model):
    __tablename__ = 'produto'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(300))
    preco = db.Column(db.Float, nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    tag = db.Column(db.String(50))
    estoque = db.Column(db.Integer, default=99)
    ativo = db.Column(db.Boolean, default=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'preco': self.preco,
            'emoji': self.emoji,
            'tag': self.tag,
            'categoria_id': self.categoria_id,
            'categoria_nome': self.categoria.nome if self.categoria else None
        }

class Cliente(db.Model):
    __tablename__ = 'cliente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'telefone': self.telefone
        }

class LocalEntrega(db.Model):
    __tablename__ = 'local_entrega'
    id = db.Column(db.Integer, primary_key=True)
    logradouro = db.Column(db.String(200), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False, default='Franca')
    estado = db.Column(db.String(2), nullable=False, default='SP')
    cep = db.Column(db.String(9), nullable=False)
    referencia = db.Column(db.String(200))
    pedidos = db.relationship('Pedido', backref='local_entrega', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'logradouro': self.logradouro,
            'numero': self.numero,
            'complemento': self.complemento,
            'bairro': self.bairro,
            'cidade': self.cidade,
            'estado': self.estado,
            'cep': self.cep,
            'referencia': self.referencia
        }

    @property
    def endereco_completo(self):
        end = f"{self.logradouro}, {self.numero}"
        if self.complemento:
            end += f", {self.complemento}"
        end += f" - {self.bairro}, {self.cidade} - {self.estado}, CEP: {self.cep}"
        if self.referencia:
            end += f" (Ref: {self.referencia})"
        return end

class Pedido(db.Model):
    __tablename__ = 'pedido'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(30), default='Pendente')
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    taxa_entrega = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    observacao = db.Column(db.Text)
    mensagem_cartao = db.Column(db.String(300))
    data_pedido = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    data_entrega = db.Column(db.DateTime)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    local_entrega_id = db.Column(db.Integer, db.ForeignKey('local_entrega.id'), nullable=False)

    itens = db.relationship('ItemPedido', backref='pedido', lazy='joined', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'status': self.status,
            'subtotal': self.subtotal,
            'taxa_entrega': self.taxa_entrega,
            'total': self.total,
            'observacao': self.observacao,
            'mensagem_cartao': self.mensagem_cartao,
            'data_pedido': self.data_pedido.isoformat() if self.data_pedido else None,
            'cliente': self.cliente.to_dict() if self.cliente else None,
            'local_entrega': self.local_entrega.to_dict() if self.local_entrega else None,
            'produtos': [item.to_dict() for item in self.itens]
        }

    def calcular_total(self):
        self.total = round(self.subtotal + self.taxa_entrega, 2)
        return self.total

class ItemPedido(db.Model):
    __tablename__ = 'item_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    preco_unitario = db.Column(db.Float, nullable=False)

    produto = db.relationship('Produto', lazy='joined')

    def to_dict(self):
        return {
            'produto': self.produto.to_dict() if self.produto else None,
            'quantidade': self.quantidade,
            'preco_unitario': self.preco_unitario,
            'subtotal_item': round(self.preco_unitario * self.quantidade, 2)
        }