from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from core.database.model import *
import config

engine = create_engine(f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.progress_database}?charset=utf8mb4")
Session = sessionmaker(bind=engine)

def get_cash_info(cash_number):
    with Session() as session:
        q = session.execute(select(CashInfo).filter(CashInfo.name.ilike(f'%cash-{cash_number}-%')))
        if q is None:
            return False
        return q.scalars().first()



def check_cash_info(cash_number):
    with Session() as session:
        q = session.execute(select(CashInfo).filter(CashInfo.name.ilike(f'%cash-{cash_number}-%')))
        if q is None:
            return False
        return len(q.fetchall())

def get_shipper_info(fsrar: str):
    with Session() as session:
        q = session.execute(select(Shippers).filter(Shippers.fsrar == fsrar))
        if q is None:
            return False
        return q.scalars().first()

