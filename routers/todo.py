from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel, Field
from starlette import status
from model import Base, Todo
from database import engine, SessionLocal     # "SessionLocal" sayesinde veritabanı ile bağlantı kurulur.
# Her bir get, post vb. işlem için bağlantı kurmaya ihtiyacımız vardır. Yani bir bağımlılık (dependency)
# oluşur.
from typing import Annotated          # Dependency'de kullanılan Annotated.
from sqlalchemy.orm import Session, defer  # Dependency'de kullanılan Session.
from routers.auth import get_current_user    # Bu fonk.da token için decode işlemi yapılıyor. Bu sayede hangi token kime (hangi user'a) ait onu öğrenmiş oluyoruz.



# NOT : todo'nun içinde sadece todo'ya özel şeyler bulunmalı. Genel şeyler "main" in içinde olmalı.

router=APIRouter(
    prefix="/todo",      # Aşağıdaki bütün endpointlerin başına koyulur.
    tags=["Todo"]        # Bu tag ile docs'ta farklı routerların endpointlerini daha rahat bir şekilde görebilirsin.
)      # Fastapi' uyg.nı başlatır. Bu router sayesinde main'deki app'e erişilebilir.


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













