import sqlalchemy.orm
from sqlalchemy import create_engine, String, Column, DateTime, Boolean, Integer, BigInteger
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
    cash = Column(String(10000))
    admin = Column(Boolean, default=False)
    whitelist_admin = Column(Boolean, default=False)


class Barcodes(Base):
    __tablename__ = 'barcodes'
    id = Column(BigInteger, nullable=False, primary_key=True)
    cash_number = Column(String(50), nullable=False)
    bcode = Column(String(50), nullable=False)
    name = Column(String(300))
    op_mode = Column(Integer())
    measure = Column(Integer())
    dcode = Column(Integer())
    tmctype = Column(Integer())
    price = Column(String(20))
    status = Column(String(50), nullable=False)
    comment = Column(String(200))
    succes = Column(Boolean(), default=False)


class Whitelist(Base):
    __tablename__ = 'cash_whitelist'
    id = Column(BigInteger, nullable=False, primary_key=True)
    cash_number = Column(String(50), nullable=False)
    inn = Column(String(50), nullable=False)


class BlackInnList(Base):
    __tablename__ = 'black_inn_list'
    id = Column(BigInteger, nullable=False, primary_key=True)
    inn = Column(String(50), nullable=False)


Base.metadata.create_all(engine)
