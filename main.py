from fastapi import FastAPI
from model import Base, Todo
from database import engine
from routers.auth import router as auth_router   # auth routerını main app'ine aktarma.
from routers.todo import router as todo_router



app=FastAPI()       # Fastapi' uyg.nı başlatır
app.include_router(auth_router)     # Bu app'e "auth" router'ını ekledik.
app.include_router(todo_router)


Base.metadata.create_all(bind=engine)  # Bu kod veritabanını oluşturur. Sol tarafa ilgili db dosyası gelir.















