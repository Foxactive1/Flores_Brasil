import os
from dotenv import load_dotenv

load_dotenv('.env')


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-change-me"
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    # PostgreSQL em produção via DATABASE_URL; SQLite apenas como fallback local.
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL:
        # Alguns provedores ainda entregam postgres://; SQLAlchemy atual espera postgresql://.
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        DB_PATH = os.path.join(INSTANCE_DIR, "flores_brasil.db")
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # WhatsApp
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "5516993117529")

    # Entrega
    ENTREGA_TAXA = float(os.environ.get("ENTREGA_TAXA", 15.0))
    ENTREGA_GRATIS_ACIMA = float(os.environ.get("ENTREGA_GRATIS_ACIMA", 100.0))

    # Admin: obrigatória em produção; fallback somente para desenvolvimento local.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
