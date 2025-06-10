class Config:
    SECRET_KEY = 'SECRET_KEY_FOR_FLASK_WTF'  # کلید مخفی برای سشن و CSRF
    SQLALCHEMY_DATABASE_URI = 'sqlite:///mydatabase.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # می‌توانید سایر تنظیمات دلخواه Flask را هم در اینجا اضافه کنید
