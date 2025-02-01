from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'  # اگر کاربر لاگین نباشد، به این روت هدایت می‌شود
