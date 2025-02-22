from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from database import SessionLocal
from model import User
from passlib.context import CryptContext  # Parolanın şifrelenmesi için gerekli kütüphane.
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer  # "token" endpointinde sadece username ve password kısmını kullanmamızı sağlar.
from jose import jwt, JWTError   # JWT tokenları için gerekli kütüphane
from datetime import timedelta, datetime, timezone


router=APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)   #  router ile birden fazla "app=FastAPI()" oluşmasını önleyerek farklı paketlerdeki tüm endpointlerin aynı app'te olmasını sağlarız.

SECRET_KEY="5pjk39a8m3bt0nmsgbzl332u80d8wfuwp1ymn9b0dtjvvar9g7u5ta12p5g1okry" # Secret key için 64 karakterlik random string oluşturduk.
ALGORITHM="HS256" # JWT için kullanılacak algoritma

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session,Depends(get_db)]


bcrypt_context=CryptContext(schemes=["bcrypt"],deprecated="auto")    # Şifreleme için gerekli kod. user create ederken (post) kullanılır.
oauth2_bearer= OAuth2PasswordBearer(tokenUrl="/auth/token")  # token url'mizi yazacağız (prefix'i de dahil ederek). Burası "get_current_user" fonk. için kullanılır.
# token endpointine istek atıldığında response (cevap) olarak bir token döndürülecek.


class CreateUserRequest(BaseModel):
    username:str
    email:str
    first_name:str
    last_name:str
    password:str
    role:str
    phone_number:str
    # "is_active" i almadık çünkü zaten model'da default olarak true verilmişti

class Token(BaseModel):   # Token için bir class oluşturmalıyız.
    access_token:str
    token_type:str

def create_access_token(username:str, user_id:int, role:str, expires_delta: timedelta):   # JWT token oluşturan fonksiyon. "expires_delta" : token ne kadar sürede geçersiz olacak?
    # Bu fonk.u token endpointinde kullanıyoruz.
    payload= {'sub':username,'id':user_id,'role':role}   # isteseydik e-mail'i de koyabilirdik. payload kısmı verilerin tutulduğu kısımdır. JSON formatında olmalıdır.
    expires=datetime.now(timezone.utc) + expires_delta    # çalıştığı andan itibaren ne kadar geçerli olacak onu dışardan biz giriyoruz.
    payload.update({'exp':expires})  # sözlüğe veri ekledik.
    return jwt.encode(payload, SECRET_KEY, algorithm= ALGORITHM)

def authenticate_user(username:str, password:str,db):   # Kullanıcı girişinin kontrol edildiği fonksiyon. "token" endpointinde kullanılır.
    user_record=db.query(User).filter(User.username==username).first()  # "User" isimli class'taki tablonun username'i ile parametre olarak girilen (kullanıcının girdiği) username'in eşleştiği kayıtları getirir.
    if not user_record:  # Eşleşen kayıt yok ise
        return False
    if not bcrypt_context.verify(password, user_record.hashed_password):  # Parametre olarak girilen parola (kullanıcının girdiği) ile verilen kayıttaki parola eşleşmiyorsa.
        return False
    return user_record

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):     # token çalıştırıldığında yapılacak işlemler. (decode işlemi)
    # Bu fonk.u todo'nun içinde (dependency olarak) kullanacağız. Atılan isteklerin kullanıcı tarafından atılıp atılmadığını teşhis etmiş olucaz.
    # Bu kod, kullanıcının gönderdiği token'ı alıp, içindeki bilgileri çözüyor (decode ediyor).
    # Amaç: Kullanıcının gerçekte kim olduğunu ve yetkilerini kontrol etmek. Yani bilgiler hangi kullanıcıdan gelmiş onu anlamaya çalışıyoruz.
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get('sub')
        user_id = payload.get('id')
        user_role = payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username or ID is invalid")
        return {'username': username, 'id': user_id, 'user_role': user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token is invalid")

@router.post("/create_user",status_code=status.HTTP_201_CREATED)
async def create_user(db:db_dependency,create_user_request:CreateUserRequest):
    user=User(
        email= create_user_request.email,
        username = create_user_request.username,
        first_name = create_user_request.first_name,
        last_name = create_user_request.last_name,
        hashed_password =bcrypt_context.hash(create_user_request.password),  # Parola şifrelenir.
        is_active = True,
        role = create_user_request.role,
        phone_number=create_user_request.phone_number

    )     # Normalde parantez içini "**create_user_request.dict()" şeklinde yazıyorduk fakat parola şifreleneceği için her biri tek tek yazıldı.
    db.add(user)
    db.commit()

@router.post("/token", response_model=Token)   # Bir kullanıcının sadece kendi todo'larıyla ilgili işlem yapabilmesini token ile sağlarız.
# "response_model=Token" ifadesi, endpoint'in döndüreceği yanıtın (response) veri modelini Token olarak belirtmek için kullanılır
async def login_for_access_token(form_data:Annotated[OAuth2PasswordRequestForm,Depends()],db:db_dependency):
    user=authenticate_user(form_data.username, form_data.password,db)
    # Kullanıcı doğrulama fonk.u ile dönen kayıttan username ve password'ü aldık. Bunun için "fastapi" nin bize "form" yapısını
    # sağladığı kütüphaneyi kullandık. Ayrıca Kullanıcı doğrulama fonk.nda db'de olduğu için bunu şuanki fonk.umuzun parametresine dependency olarak yazdık.
    if not user:  # Kullanıcı yoksa, uyuşmuyorsa.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password")
    token=create_access_token(user.username, user.id, user.role, timedelta(minutes=60))# Kullanıcı var ise, eşleşiyorsa bir token oluşturulur.
    # Doğrulanan, bulunan kullanıcı (user) ile veritabanı tablosundaki "user,id,role" kısımlarını parametre olarak girdik. Token'ın geçerlilik süresinin 60 dk olmasını sağladık. Süre dolunca kullanıcı yeniden giriş yapmak zorunda!
    return {"access_token":token,"token_type":"bearer"}











