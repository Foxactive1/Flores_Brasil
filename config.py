import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 🔐 Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # 📁 Base do projeto
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # 📦 Diretório do banco (garante existência)
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    # 🗄️ Banco de dados (FORÇADO SQLite para evitar erro no Pydroid)
    DB_PATH = os.path.join(INSTANCE_DIR, "flores_brasil.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ⚙️ Engine config (seguro para SQLite)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }

    # 📲 WhatsApp
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "5516993117529")

    # 🚚 Entrega
    ENTREGA_TAXA = float(os.environ.get("ENTREGA_TAXA", 15.0))
    ENTREGA_GRATIS_ACIMA = float(os.environ.get("ENTREGA_GRATIS_ACIMA", 100.0))