from loguru import logger
from sqlalchemy import select, update, insert, delete
from sqlalchemy.orm import *
from sqlalchemy.exc import OperationalError

from core.database.modelBOT import *

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4")
Session = sessionmaker(bind=engine)


async def get_barcodes_for_add(cash_number: str):
    with Session() as session:
        barcodes = session.execute(
            select(Barcodes).where((Barcodes.cash_number == cash_number) & (Barcodes.status == 'add') & (Barcodes.succes == False))).scalars().all()
        return barcodes


async def get_barcodes_for_price(cash_number: str):
    with Session() as session:
        barcodes = session.execute(
            select(Barcodes).where((Barcodes.cash_number == cash_number) & (Barcodes.status == 'setprice') & (Barcodes.succes == False))).scalars().all()
        return barcodes


async def update_status_barcode(id: str, state: bool):
    with Session() as session:
        session.execute(update(Barcodes).where(Barcodes.id == id).values(succes=state))
        session.commit()


def get_unique_cashnumbers_from_barcodes():
    with Session() as session:
        return session.execute(select(Barcodes.cash_number.distinct()).where(Barcodes.succes == False)).scalars().all()


async def update_client_info(**kwargs):
    with Session() as session:
        logger.info(kwargs)
        chat_id = str(kwargs["chat_id"])
        SN = session.query(Clients).filter(Clients.chat_id == chat_id).first()
        if SN is None:
            SN = Clients(**kwargs)
            session.add(SN)
        else:
            session.query(Clients).filter(Clients.chat_id == chat_id).update(kwargs, synchronize_session='fetch')
        session.commit()


async def get_client_info(**kwargs):
    try:
        with Session() as session:
            client = session.query(Clients).filter(Clients.chat_id == str(kwargs["chat_id"])).first()
            if client is None:
                return False
            return client
    except OperationalError as ex:
        await get_client_info(**kwargs)


async def add_client_cashNumber(**kwargs):
    with Session() as session:
        chat_id = str(kwargs["chat_id"])
        cash = str(kwargs["cash"])
        client = session.query(Clients).filter(Clients.chat_id == chat_id).first()
        if client.cash is None:
            session.query(Clients).filter(Clients.chat_id == chat_id).update(kwargs, synchronize_session='fetch')
        else:
            cashes = client.cash.split(',')
            if not cash in cashes:
                cashes = f'{cash},{client.cash}'
                session.query(Clients).filter(Clients.chat_id == chat_id).update({
                    'chat_id': chat_id,
                    'cash': cashes
                }, synchronize_session='fetch')
        session.commit()


async def check_cashNumber(chat_id: str, cash: str):
    with Session() as session:
        client = session.query(Clients).filter(Clients.chat_id == chat_id).first()
        if client.cash is None:
            return False
        else:
            cashes = client.cash.split(',')
            if not cash in cashes:
                return False
        return True


def create_barcode(**kwargs):
    with Session() as session:
        session.add(Barcodes(**kwargs))
        session.commit()


async def check_cash_in_whitelist(cash_number: str):
    """Проверка номера компьютера в белом списке для приёма ТТН"""
    with Session() as session:
        return session.execute(select(Whitelist).where(Whitelist.cash_number == cash_number)).first()


async def get_cash_in_whitelist():
    """Отадёт номера компьютеров белого списка для приёма ТТН"""
    with Session() as session:
        return session.execute(select(Whitelist)).scalars().all()

async def add_cash_in_whitelist(cash_number: str, inn: str):
    """Добавляет номер компьютера в белый список для приёма ТТН"""
    with Session() as session:
        session.execute(insert(Whitelist).values(cash_number=cash_number, inn=inn))
        session.commit()
async def delete_cash_from_whitelist(cash_number: str):
    """Удалить номер компьютера из белого списка приёма ТТН"""
    with Session() as session:
        session.execute(delete(Whitelist).where(Whitelist.cash_number == cash_number))
        session.commit()


async def check_inn_in_blacklist(inn: str):
    """Проверка ИНН в черном списке для приёма ТТН"""
    with Session() as session:
        return session.execute(select(BlackInnList).where(BlackInnList.inn == inn)).first()


async def get_whitelist_admins():
    """Забираю админом которые могут добавлять компы в белый список"""
    with Session() as session:
        return session.execute(select(Clients).where(Clients.whitelist_admin)).scalars().all()
