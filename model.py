# Veritabanında tutacağımız tablolar burada olacak.
# database kısmından sonra 2. olarak bu kısımdan devam ediyoruz.

from .database import Base    # Model'ları oluştururken Base'yi kullanacağız.
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey


class Todo(Base):         # SQL'deki tablolarımız oluşturmaktan sorumlu sınıf
    __tablename__ = 'todos'        # Burası tamamen aynı olacak çünkü özel değişkendir.

    id= Column(Integer, primary_key=True, index=True)
    title= Column(String)
    description=Column(String)
    priority= Column(Integer)
    complete= Column(Boolean, default=False)     # default=False, yeni bir todo eklediğimizde complete sütununun varsayılan olarak False olmasını sağlar.
    owner_id= Column(Integer,ForeignKey('users.id'))  # Todo ve User tablosu arasında User tablosunun id'si açısından ilişki kurduk.
    # 1-N ilişki var. Bir kullanıcının birden fazla todo'su olabilirken her todo bir kullanıcıya özel olabilir.

class User(Base):
    __tablename__= 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)       # "unique" ile her email'in tek olduğunu bir başka örneğinin olamayışını sağladık.
    username= Column(String,unique=True)
    first_name= Column(String)
    last_name= Column(String)
    hashed_password= Column(String)
    is_active= Column(Boolean, default=True)  # Hesap aktif mi dondurulmuş mu onun için.
    role= Column(String)
    phone_number= Column(String)










