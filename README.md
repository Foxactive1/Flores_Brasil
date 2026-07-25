🌸 Flores Brasil

https://img.shields.io/badge/Python-3.11-blue.svg
https://img.shields.io/badge/Flask-2.3.x-lightgrey.svg
https://img.shields.io/badge/Groq-LLM-orange.svg
https://img.shields.io/badge/License-MIT-green.svg

Flores Brasil é uma plataforma completa para floricultura, que integra inteligência artificial para processar pedidos recebidos via WhatsApp, gerar mensagens automáticas e oferecer uma experiência de checkout simplificada. O sistema inclui painel administrativo, parser de mensagens com IA (Groq), geração de links de pagamento e rastreamento de pedidos.

---

🚀 Funcionalidades

· Parser de mensagens por IA – Extrai automaticamente dados de pedidos a partir de mensagens do WhatsApp, usando o modelo llama-3.3-70b-versatile da Groq.
· Catálogo de produtos – Exibição com filtros por categoria, emojis e preços.
· Carrinho de compras – Interface intuitiva no frontend com persistência em sessão.
· Pedidos – Criação de pedidos com cliente, endereço de entrega, produtos e mensagem no cartão.
· WhatsApp integrado – Geração de mensagem pronta para envio ao cliente, com resumo do pedido.
· Painel administrativo – Gerencie pedidos, atualize status e visualize métricas da IA.
· Rastreamento de pedidos – Página pública para clientes acompanharem o status do pedido.
· Pagamentos simulados – Opções PIX, Boleto e Link de pagamento (simulados para demonstração).

---

🏗️ Arquitetura

· Backend: Flask (Python) + SQLAlchemy (ORM)
· Banco de dados: SQLite (padrão) / PostgreSQL (opcional via DATABASE_URL)
· IA: Groq API (com fallback por regex)
· Frontend: HTML, CSS (estilo personalizado), JavaScript (fetch API)
· Deploy: Docker, GitHub Actions, Azure Web Apps

---

🛠️ Tecnologias

· Python 3.11+
· Flask 2.3.x
· Flask-SQLAlchemy
· Groq Python SDK
· Gunicorn
· Docker
· GitHub Actions (CI/CD)

---

📦 Pré-requisitos

· Python 3.11 ou superior
· Pip
· (Opcional) Docker e Docker Compose
· (Opcional) Conta no Groq para chave de API

---

🔧 Instalação Local

1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/flores-brasil.git
cd flores-brasil
```

2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instale as dependências

```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente

Crie um arquivo .env na raiz do projeto com:

```env
SECRET_KEY=sua-chave-secreta
GROQ_API_KEY=sua-chave-da-groq
ADMIN_PASSWORD=admin123
WHATSAPP_NUMBER=5516993117529
ENTREGA_TAXA=15.0
ENTREGA_GRATIS_ACIMA=100.0
```

5. Inicialize o banco de dados

```bash
python -c "from app import app, init_db; init_db()"
```

6. Execute a aplicação

```bash
python app.py
```

Acesse http://localhost:5000 no navegador.

---

🐳 Docker

Build da imagem

```bash
docker build -t flores-brasil .
```

Executar com Docker Compose

```bash
docker-compose up --build
```

A aplicação estará disponível em http://localhost:5000.

---

🔌 Endpoints da API

Método Endpoint Descrição
GET /api/produtos Lista produtos (com filtro por categoria)
GET /api/categorias Lista categorias ativas
POST /api/pedido Cria um novo pedido e retorna mensagem WhatsApp
POST /api/parse-mensagem Envia mensagem para IA e retorna estrutura do pedido
GET /api/rastrear/<codigo> Timeline de status de um pedido
PUT /api/pedido/<int:id>/status Atualiza status (adm)
GET /api/estatisticas Métricas dos últimos 30 dias (adm)
GET /api/ia/metrics Métricas de uso da IA (adm)

Nota: Rotas administrativas (com (adm)) exigem autenticação via sessão (login em /admin/login).

---

🧪 Uso do Parser de Pedidos

1. Acesse /parser.
2. Cole uma mensagem de pedido recebida no WhatsApp (ex: no formato gerado pelo sistema).
3. Clique em "Reconhecer Pedido".
4. A IA (ou fallback) extrairá todos os dados e exibirá o pedido estruturado.
5. As opções de pagamento simuladas (PIX, Boleto, Link) estarão disponíveis para demonstração.

---

📊 Painel Administrativo

· Acesse /admin/login com a senha definida em ADMIN_PASSWORD.
· Gerencie pedidos, atualize status e visualize métricas da IA.

---

🤝 Contribuição

1. Faça um fork do projeto.
2. Crie uma branch para sua feature (git checkout -b feature/nova-funcionalidade).
3. Commit suas alterações (git commit -m 'Adiciona nova funcionalidade').
4. Push para a branch (git push origin feature/nova-funcionalidade).
5. Abra um Pull Request.

---

📝 Licença

Este projeto está licenciado sob a licença MIT – veja o arquivo LICENSE para detalhes.

---

🙏 Agradecimentos

· Groq pela API de IA de alta performance.
· InNovaIdeia pelo apoio no desenvolvimento.

---

Desenvolvido com 💐 por InNovaIdeia & colaboradores.
