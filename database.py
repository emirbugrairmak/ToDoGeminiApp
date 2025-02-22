# Burada veritabanı ile ilgili bağlantı işlemlerini yapacağız.
# Önce buradan başlıyoruz. Kendimiz almadık hazır yapıştırdık.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./todoai_app.db"  # Bu URL şuna bakar : todoai_app.db isimli dosya projede (sol tarafta var mı?)

engine= create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args= {"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()