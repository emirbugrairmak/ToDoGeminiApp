from fastapi import APIRouter, Depends, Path, HTTPException, Request
from pydantic import BaseModel, Field
from starlette import status
from starlette.responses import RedirectResponse     # login-page'e yönlendirme yapabilmek için kullanılır.
from ..model import Base, Todo
from ..database import engine, SessionLocal     # "SessionLocal" sayesinde veritabanı ile bağlantı kurulur.
# Her bir get, post vb. işlem için bağlantı kurmaya ihtiyacımız vardır. Yani bir bağımlılık (dependency)
# oluşur.
from typing import Annotated          # Dependency'de kullanılan Annotated.
from sqlalchemy.orm import Session, defer  # Dependency'de kullanılan Session.
from ..routers.auth import get_current_user    # Bu fonk.da token için decode işlemi yapılıyor. Bu sayede hangi token kime (hangi user'a) ait onu öğrenmiş oluyoruz.
from fastapi.templating import Jinja2Templates    # "templates" klasörünü backend'e bağlayabilmek için gerekli kütüphane
from dotenv import load_dotenv # Buradan itibaren AI için gerekli kütüphaneler var.
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import markdown
from bs4 import BeautifulSoup       # html'i parse eden (işleyen bir kütüphane)


# NOT : todo'nun içinde sadece todo'ya özel şeyler bulunmalı. Genel şeyler "main" in içinde olmalı.

router=APIRouter(
    prefix="/todo",      # Aşağıdaki bütün endpointlerin başına koyulur.
    tags=["Todo"]        # Bu tag ile docs'ta farklı routerların endpointlerini daha rahat bir şekilde görebilirsin.
)      # Fastapi' uyg.nı başlatır. Bu router sayesinde main'deki app'e erişilebilir.

templates=Jinja2Templates(directory="app/templates")  # frontend'deki templates klasörünü auth işlemlerine entegre etme.


class ToDoRequest(BaseModel):     # Request kısmı post(veri ekleme) ve put(veri güncelleme) işlemleri için oluşturulur.
    # async fonk.larına dışardan uzun uzun bu parametreleri girmek yerine request class'ına yazıyoruz. Request tam olarak bu işe yarıyor.
    title:str = Field(min_length=3)
    description:str = Field(max_length=1500)
    priority:int = Field(gt=0,lt=6)
    complete:bool


def get_db():         # Veritabanı ile bağlantı kurulmasını sağlayan fonksiyon. Her endpointte bu fonk. çalıştırılacağı için bu fonksiyona bağımlı olacaklar (dependency)
    db=SessionLocal()   # SessionLocal() sınıfından bir nesne oluşturduk. Yani "SessionLocal()" ı çalıştırdık
    try:
        yield db     # return gibidir. Farkı birden fazla şeyi return edebilmektir.
    finally:
        db.close()       # Session'ı kapattık.

db_dependency = Annotated[Session,Depends(get_db)]      # Dependency işlemini burada sağladık. artık "db_dependency"
# değişkeni ile bağımlılık çok kolay bir şekilde yönetilecek.
user_dependency= Annotated[dict, Depends(get_current_user)]   # "get_current_user" fonk.u dict return eder.

def redirect_to_login():      # Yönlendirme yapan bir fonksiyon yazdık.
    redirect_response=RedirectResponse(url="/auth/login-page", status_code=status.HTTP_302_FOUND)   # Belirtilen sayfaya yönlendirme yapılır.
    redirect_response.delete_cookie("access_token")  # Bu sayede kullanıcı otomatik giriş yapamaz. Tekrar giriş yapması gerekir. (önlem amaçlı yazılmış bir satır kod.)
    return redirect_response


@router.get("/todo-page")     # Bir kullanıcı "todo-page" e girerse "todo.html" i görmesi sağlanır. (backend ile frontendi bağlama)
async def render_todo_page(request:Request,db: db_dependency):
    try:
        user=await get_current_user(request.cookies.get('access_token'))    # Buradaki kısımları yapmazsak kullanıcı "/todo-page" yazarak direkt olarak login yapmadan bu sayfaya girebilir. Bunu önlüyoruz.
        # request.cookies.get('access_token') → Kullanıcının giriş yapıp yapmadığını kontrol ediyor.
        # get_current_user(...) → Eğer token varsa, giriş yapan kullanıcıyı çekiyor.
        if user is  None:  # Kullanıcı yok ise.
            return redirect_to_login() # Kullanıcı login sayfasına yönlendirilir.
        else:  # Kullanıcı var ise.
            todos = db.query(Todo).filter(Todo.owner_id == user.get('id')).all()  # Giriş yapan kullanıcının todolarının todo.html sayfasında görüntülenmesini sağlamalıyız.
        return templates.TemplateResponse("todo.html", {"request": request, "todos": todos, "user": user})
    except:
        return redirect_to_login()     # user'ı hiçbir şekilde alamazsa login'e yönlendirme yapsın.

@router.get("/add-todo-page")   # Kullanıcının todo page eklemesini sağlayan kısım.
async def render_add_todo_page(request: Request):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login()
        return templates.TemplateResponse("add-todo.html", {"request": request, "user": user})
    except:
        return redirect_to_login()

@router.get("/edit-todo-page/{todo_id}")    # Kullanıcının todo editlemesini sağlayan kısım
# değiştireceğimiz todo'nun id'sini path parametresi olarak vermeliyiz.
async def render_todo_page(request: Request, todo_id: int, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login()

        todo = db.query(Todo).filter(Todo.id == todo_id).first()    # Bu sefer tek bir todo ile uğraşıyoruz.
        return templates.TemplateResponse("edit-todo.html", {"request": request, "todo": todo, "user": user})
    except:
        return redirect_to_login()



@router.get("/")          # Bütün kayıtları getirdik.
async def read_all(user:user_dependency, db:db_dependency):      # Bağımlılığı parametre olarak aldık. # Bu fonk.un çalışması için bir user'a ihtiyacı var dedik. Bu da bağımlılıktır.
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return db.query(Todo).filter(Todo.owner_id==user.get('id')).all()       # model'daki tablomuzun bulunduğu "Todo" class'ını yazdık.
    # user kimse onun todolarını görüntülemeyi sağladık. "owner_id" "create_todo" endpointi çalıştırıldıktan sonra gelecek.

@router.get("/todo/{id}", status_code=status.HTTP_200_OK)     # id'ye göre kayıt. Bu yüzden filter kullanılır.
async def read_by_id(user:user_dependency,db:db_dependency,id:int=Path(gt=0)):

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return_record=db.query(Todo).filter(Todo.id == id).filter(Todo.owner_id == user.get('id')).first()   # Fonksiyona girilen parametre ile veritabanındaki "id" sütununun eşleştiği kayıtlar getirilecek.
    # Burada "first()" ile ilk eşleşen kayıt döndürülecek. Aslında zaten "id" ile çalıştığımız için bir tane "id" ile eşleşecek.
    # Eğer hiç eşleşen kayıt yoksa, first()'ten None döner.
    # "Todo.id == id" Kullanıcının istekte bulunduğu id değerine sahip todo'yu seçiyoruz.
    # "Todo.owner_id == user.get('id')" Bu sayede herkes kendi todo'larını görebilecek. Başkalarının todo'larını göremeyiz.
    # "owner_id" todo'yu oluşturan kişinin kimliğidir.
    # user.get('id') → O an API'yi çağıran kullanıcının kimliğidir.

    if return_record is not None:     # Eğer eşleşen kayıt varsa :
        return return_record         # Eşleşen kayıt dönecek.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Todo not found!")

@router.post("/todo",status_code=status.HTTP_201_CREATED)
async def create_todo(user:user_dependency,db:db_dependency,todorequest:ToDoRequest): # "user_dependency" kısmını da ekledik çünkü create işlemi yapıldığında bu hangi user tarafından yapılmış olacak onu anlamaya çalışıyoruz.

    if user is None:     # Kullanıcı yoksa hata fırlatılacak.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    todo=Todo(**todorequest.dict(), owner_id=user.get('id'))     # Todo adlı veritabanı class'ımızdan bir nesne oluşturduk.
    # "owner_id" kısmı : token'dan (user'dan) gelen id owner_id'ye eşitlenir. "owner_id" todo'yu oluşturan kişinin kimliğidir.
    # title=todorequest.title, ...  gibi tek tek yazmak yerine "**todorequest.dict()" yapısını kullandık.
    todo.description = create_todo_with_gemini(todo.description)  # description kısmında gemini'yi kullandık.
    db.add(todo)  # Todo isimli veritabanı class'ına (todo nesnesini yazdık) yeni veriyi ekledik.
    db.commit()   # İşlemin işleneceği, yapılacağı anlamına gelir.

@router.put("/todo/{id}",status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user:user_dependency,db:db_dependency,todorequest:ToDoRequest,id:int=Path(gt=0)):
    # "id" request kısmında olmadığı için ayrı bir parametre olarak eklendi.

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    record=db.query(Todo).filter(Todo.id==id).filter(Todo.owner_id==user.get('id')).first()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Todo not found!")

    record.title=todorequest.title        # id hariç güncelleme işlemleri. Çünkü zaten eşleşen id değerindeki verilerin sütunlarını (priortiy vb.) güncelleyeceğiz.
    record.complete=todorequest.complete  # gelen kayıttaki, veritabanındaki (record) verileri dışardan gelen parametre (request) ile güncelleme.
    record.priority=todorequest.priority
    record.description=todorequest.description

    db.add(record)        # Güncelleme işlemi yapılır.
    db.commit()           # işlem işlenir.

@router.delete("/todo/{id}",status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user:user_dependency,db:db_dependency,id:int=Path(gt=0)):

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    record=db.query(Todo).filter(Todo.id==id).filter(Todo.owner_id==user.get('id')).first()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Todo not found!")

    db.delete(record)
    db.commit()


def markdown_to_text(markdown_string):       #  Amaç markdown formatındaki (**) bir metni düz metne çevirmek. Geminiden markdown formatında cevap dönme ihtimali var.
        html = markdown.markdown(markdown_string)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()
        return text


def create_todo_with_gemini(todo_string: str):    # description kısmı için Gemini'den yararlanmak.
        load_dotenv()   # Burası .env dosyasından API anahtarını almak için kullanılıyor.
        genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")   # Gemini AI'nin sohbet modelini oluşturuyor.
        response = llm.invoke(    # Gemini modeline iki mesaj gönderilir.
            [
                HumanMessage(content="I will provide you a todo item to add my to do list. What i want you to do is to create a longer and more comprehensive description of that todo item, my next message will be my todo:"),
                # İlk mesaj prompttur.
                HumanMessage(content=todo_string),   # Bu mesaj kullanıcının girdiği descrp metnidir.
            ]
        )
        return markdown_to_text(response.content)    # Gemini'nin cevabını Markdown'dan düz metne çeviriyor ve döndürüyor.










