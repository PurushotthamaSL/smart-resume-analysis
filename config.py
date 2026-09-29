import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _resolve_database_uri() -> str:
    """Resolve database URI, ensuring relative SQLite paths resolve to absolute project paths."""
    db_env = os.getenv("DATABASE_URI")
    instance_db = BASE_DIR / "instance" / "smart_resume.db"

    if not db_env:
        return f"sqlite:///{instance_db.as_posix()}"

    if db_env.startswith("sqlite:///"):
        raw_path = db_env[len("sqlite:///"):]
        p = Path(raw_path)
        if not p.is_absolute():
            # Check instance/ filename first, then base_dir
            if (BASE_DIR / "instance" / p.name).exists() or "instance" in raw_path:
                return f"sqlite:///{(BASE_DIR / 'instance' / p.name).as_posix()}"
            elif (BASE_DIR / p).exists():
                return f"sqlite:///{(BASE_DIR / p).as_posix()}"
            else:
                return f"sqlite:///{(BASE_DIR / 'instance' / p.name).as_posix()}"
        return f"sqlite:///{p.as_posix()}"

    return db_env


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-resume-analyzer-secret-key-default")
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CORS parameters
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    
    # Upload parameters
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB max
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
    
    # Data files
    DATA_DIR = BASE_DIR / "data"
    SKILLS_TAXONOMY_PATH = DATA_DIR / "skills_taxonomy.json"
    JOB_ROLES_PATH = DATA_DIR / "job_roles.json"
    LEARNING_RESOURCES_PATH = DATA_DIR / "learning_resources.json"



class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
