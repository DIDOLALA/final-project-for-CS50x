from app import create_app
from database import db

app = create_app()

with app.app_context():
    db.drop_all()   
    db.create_all()
    print("数据库和表已创建成功！")
