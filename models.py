from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone  # MELHORIA: timezone importado para substituir utcnow depreciado

db = SQLAlchemy()

# ─────────────────────────────────────────────────────────────
# TABELA ASSOCIATIVA: Pedido <-> Produto (muitos-para-muitos)
# ─────────────────────────────────────────────────────────────
pedido_produto = db.Table('pedido_produto',
    db.Column('pedido_id',      db.Integer, db.ForeignKey('pedido.id'),  primary_key=True),
    db.Column('produto_id',     db.Integer, db.ForeignKey('produto.id'), primary_key=True),
    db.Column('quantidade',     db.Integer, nullable=False, default=1),
    db.Column('preco_unitario', db.Float,   nullable=False)
)


class Categoria(db.Model):
    __tablename__ = 'categoria'

    id    = db.Column(db.Integer,     primary_key=True)
    nome  = db.Column(db.String(50),  unique=True, nullable=False)
    slug  = db.Column(db.String(50),  unique=True, nullable=False)
    icone = db.Column(db.String(10),  nullable=False)   # Emoji ou ícone
    ativo = db.Column(db.Boolean,     default=True)

    produtos = db.relationship('Produto', backref='categoria', lazy=True)

    def to_dict(self):
        return {
            'id':    self.id,
            'nome':  self.nome,
            'slug':  self.slug,
            'icone': self.icone
        }


class Produto(db.Model):
    __tablename__ = 'produto'

    id           = db.Column(db.Integer,      primary_key=True)
    nome         = db.Column(db.String(100),  nullable=False)
    descricao    = db.Column(db.String(300))
    preco        = db.Column(db.Float,        nullable=False)
    emoji        = db.Column(db.String(10),   nullable=False)
    tag          = db.Column(db.String(50))   # Ex: "Exclusivo", "Mais Vendido"
    estoque      = db.Column(db.Integer,      default=99)
    ativo        = db.Column(db.Boolean,      default=True)
    categoria_id = db.Column(db.Integer,      db.ForeignKey('categoria.id'), nullable=False)

    # Relacionamento com pedidos via tabela associativa
    pedidos = db.relationship('Pedido', secondary=pedido_produto, backref='itens')

    def to_dict(self):
        return {
            'id':             self.id,
            'nome':           self.nome,
            'descricao':      self.descricao,
            'preco':          self.preco,
            'emoji':          self.emoji,
            'tag':            self.tag,
            'categoria_id':   self.categoria_id,
            'categoria_nome': self.categoria.nome if self.categoria else None
        }


class Cliente(db.Model):
    __tablename__ = 'cliente'

    id         = db.Column(db.Integer,     primary_key=True)
    nome       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(100))
    telefone   = db.Column(db.String(20),  nullable=False, unique=True)  # MELHORIA: unique para evitar duplicatas
    criado_em  = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))  # BUG FIX: utcnow depreciado

    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)

    def to_dict(self):
        return {
            'id':       self.id,
            'nome':     self.nome,
            'email':    self.email,
            'telefone': self.telefone
        }


class LocalEntrega(db.Model):
    __tablename__ = 'local_entrega'

    id          = db.Column(db.Integer,      primary_key=True)
    logradouro  = db.Column(db.String(200),  nullable=False)
    numero      = db.Column(db.String(20),   nullable=False)
    complemento = db.Column(db.String(100))
    bairro      = db.Column(db.String(100),  nullable=False)
    cidade      = db.Column(db.String(100),  nullable=False, default='Franca')
    estado      = db.Column(db.String(2),    nullable=False, default='SP')
    cep         = db.Column(db.String(9),    nullable=False)
    referencia  = db.Column(db.String(200))

    pedidos = db.relationship('Pedido', backref='local_entrega', lazy=True)

    def to_dict(self):
        return {
            'id':           self.id,
            'logradouro':   self.logradouro,
            'numero':       self.numero,
            'complemento':  self.complemento,
            'bairro':       self.bairro,
            'cidade':       self.cidade,
            'estado':       self.estado,
            'cep':          self.cep,
            'referencia':   self.referencia
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

    id               = db.Column(db.Integer,     primary_key=True)
    codigo           = db.Column(db.String(20),  unique=True, nullable=False)
    status           = db.Column(db.String(30),  default='Pendente')
    # Status possíveis: Pendente | Confirmado | Preparando | Saiu para Entrega | Entregue | Cancelado
    subtotal         = db.Column(db.Float,        nullable=False, default=0.0)
    taxa_entrega     = db.Column(db.Float,        nullable=False, default=0.0)
    total            = db.Column(db.Float,        nullable=False, default=0.0)
    observacao       = db.Column(db.Text)
    mensagem_cartao  = db.Column(db.String(300))
    data_pedido      = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))  # BUG FIX: utcnow depreciado
    data_entrega     = db.Column(db.DateTime)

    cliente_id       = db.Column(db.Integer, db.ForeignKey('cliente.id'),       nullable=False)
    local_entrega_id = db.Column(db.Integer, db.ForeignKey('local_entrega.id'), nullable=False)

    def to_dict(self):
        # BUG FIX: versão anterior usava next() em self.itens (lista de Produto) para buscar
        # quantidade — o que nunca funcionaria. Agora faz a consulta correta na tabela associativa.
        produtos_list = []
        for produto in self.itens:
            row = db.session.execute(
                pedido_produto.select().where(
                    pedido_produto.c.pedido_id  == self.id,
                    pedido_produto.c.produto_id == produto.id
                )
            ).first()
            quantidade     = row.quantidade      if row else 1
            preco_unitario = row.preco_unitario  if row else produto.preco

            produtos_list.append({
                'produto':        produto.to_dict(),
                'quantidade':     quantidade,
                'preco_unitario': preco_unitario,
                'subtotal_item':  round(preco_unitario * quantidade, 2)  # MELHORIA: campo extra útil
            })

        return {
            'id':              self.id,
            'codigo':          self.codigo,
            'status':          self.status,
            'subtotal':        self.subtotal,
            'taxa_entrega':    self.taxa_entrega,
            'total':           self.total,
            'observacao':      self.observacao,
            'mensagem_cartao': self.mensagem_cartao,
            'data_pedido':     self.data_pedido.isoformat() if self.data_pedido else None,
            'cliente':         self.cliente.to_dict()       if self.cliente       else None,
            'local_entrega':   self.local_entrega.to_dict() if self.local_entrega else None,
            'produtos':        produtos_list
        }

    def calcular_total(self):
        """Recalcula e persiste o total do pedido."""
        self.total = round(self.subtotal + self.taxa_entrega, 2)
        return self.total
