import sqlalchemy.orm
from sqlalchemy import create_engine, String, Column, DateTime, Boolean, BigInteger, Integer
import config
from sqlalchemy.sql import func

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4")
Base = sqlalchemy.orm.declarative_base()


class Clients(Base):
    __tablename__ = 'clients'
    date = Column(DateTime(timezone=True), server_default=func.now())
    phone_number = Column(String(50), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    user_id = Column(String(50), nullable=False, primary_key=True)
    chat_id = Column(String(50), nullable=False)
    cash = Column(String(250))
    admin = Column(Boolean, default=False)


class CashInfo(Base):
    __tablename__ = 'cash_info'
    id = Column(BigInteger, nullable=False, primary_key=True)
    name = Column(String(255), nullable=False)
    inn = Column(String(255), nullable=False)
    kpp = Column(String(255), nullable=False)
    fsrar = Column(String(255))
    fsrar2 = Column(String(255))
    address = Column(String(255), nullable=False)
    ooo_name = Column(String(255))
    ip_name = Column(String(255))
    ip_inn = Column(String(255))
    ip = Column(String(255))


class Shippers(Base):
    __tablename__ = 'shippers'
    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String(255), nullable=False, )
    inn = Column(String(255), nullable=False)
    fsrar = Column(String(255), nullable=False)


Base.metadata.create_all(engine)
