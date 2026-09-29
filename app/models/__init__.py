from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .models import Resume, JobRole, JobMatch, Recommendation

__all__ = ["db", "Resume", "JobRole", "JobMatch", "Recommendation"]
