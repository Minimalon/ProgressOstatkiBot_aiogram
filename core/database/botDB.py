import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import *
from core.database.model import Clients
import config
from loguru import logger

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4", pool_pre_ping=True)
Session = sessionmaker(bind=engine)


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
    with Session() as session:
        client = session.query(Clients).filter(Clients.chat_id == str(kwargs["chat_id"])).first()
        if client is None:
            return False
        return client


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
