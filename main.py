from alembic.util import status
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from starlette import status
from .model import Base, Todo
from .database import engine
from .routers.auth import router as auth_router   # auth routerını main app'ine aktarma.
from .routers.todo import router as todo_router
import os


app=FastAPI()       # Fastapi' uyg.nı başlatır

script_dir=os.path.dirname(__file__)  # Şu an çalışmakta olan Python dosyasının (main.py gibi) bulunduğu dizini alır.
st_abs_file_path=os.path.join(script_dir, "static/")  # Yukarıda alınan dizine "static/" klasörünü ekleyerek mutlak (absolute) bir yol oluşturur.



app.mount("/static", StaticFiles(directory=st_abs_file_path), name="static")  # frontend'i bağlamak için ilk yapacağımız şey
# static dosyasını bağlamaktır. Bu satırı yazarken yukarıda "StaticFiles" ı import ettik.

@app.get("/")
def read_root(request:Request):    # Gelen tüm istekler "Request" sınıfından takip edilebilir.
    return RedirectResponse(url="/todo/todo-page",status_code=status.HTTP_302_FOUND) # Bir istek, kullanıcı gelirse onu bu sayfaya yönlendireceğiz.


app.include_router(auth_router)     # Bu app'e "auth" router'ını ekledik.
app.include_router(todo_router)


Base.metadata.create_all(bind=engine)  # Bu kod veritabanını oluşturur. Sol tarafa ilgili db dosyası gelir.















