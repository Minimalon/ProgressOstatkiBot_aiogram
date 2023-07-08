import asyncio
import re

from sqlalchemy import text
from sqlalchemy.orm import *

from core.database.query_BOT import get_barcodes_for_add, update_status_barcode, get_unique_cashnumbers_from_barcodes, get_barcodes_for_price
from core.database.modelBOT import *
from core.database.query_PROGRESS import get_cash_info


async def add_barcodes_in_cash(ip, cash_number):
    engine = create_engine(f"mysql+pymysql://{config.cash_user}:{config.cash_password}@{ip}:{config.port}/{config.cash_database}?charset=utf8mb4")
    Session = sessionmaker(bind=engine)
    barcodes_for_add = await get_barcodes_for_add(cash_number)
    if len(barcodes_for_add) > 0:
        with Session() as s:
            for barcode in barcodes_for_add:
                s.execute(text(
                    f"INSERT IGNORE INTO tmc (bcode, vatcode1, vatcode2, vatcode3, vatcode4, vatcode5, dcode, name, articul, cquant, measure, pricetype, price, minprice, valcode, quantdefault, quantlimit, ostat, links, quant_mode, bcode_mode, op_mode, dept_mode, price_mode, tara_flag, tara_mode, tara_default, unit_weight, code, aspectschemecode, aspectvaluesetcode, aspectusecase, aspectselectionrule, extendetoptions, groupcode, remain, remaindate, documentquantlimit, age, alcoholpercent, inn, kpp, alctypecode, manufacturercountrycode, paymentobject, loyaltymode, minretailprice)VALUES({barcode.bcode},301,302,303,304,305,{barcode.dcode},'{barcode.name}','',1.000,{barcode.measure},0,{barcode.price},1.00,0,1.000,0.000,0,0,15,3,{barcode.op_mode},1,1,NULL,NULL,'0',NULL,{barcode.bcode},NULL,NULL,NULL,NULL,NULL,NULL,0.000,'2021-22-12 22:22:22',2.000,NULL,15.00,NULL,NULL,0,NULL,NULL,0,1.00);"))
                s.execute(text(
                    f"INSERT IGNORE INTO barcodes (code, barcode, name, price, cquant, measure, aspectvaluesetcode, quantdefault, packingmeasure, packingprice, minprice, minretailprice, customsdeclarationnumber, tmctype) VALUES ({barcode.bcode},{barcode.bcode},'{barcode.name}',{barcode.price},NULL,{barcode.measure},NULL,1.000,2,NULL,1.00,1.00,NULL,{barcode.tmctype});"))
                await update_status_barcode(barcode.id, True)
            s.commit()


async def update_price_in_cash(ip, cash):
    engine = create_engine(f"mysql+pymysql://{config.cash_user}:{config.cash_password}@{ip}:{config.port}/{config.cash_database}?charset=utf8mb4")
    Session = sessionmaker(bind=engine)
    barcodes_for_price = await get_barcodes_for_price(cash)
    if len(barcodes_for_price) > 0:
        with Session() as s:
            for barcode in barcodes_for_price:
                s.execute(text(
                    f"UPDATE barcodes JOIN tmc ON barcodes.code = tmc.code SET barcodes.price = {barcode.price}, tmc.price = {barcode.price} WHERE barcodes.code = '{barcode.bcode}';"))
                await update_status_barcode(barcode.id, True)
            s.commit()


if __name__ == '__main__':
    # asyncio.run(add_barcodes_in_cash('10.8.1.211', 'cash-123-1'))
    for cash_number in get_unique_cashnumbers_from_barcodes():
        cash_info = get_cash_info(cash_number.split('-')[1])
        if cash_info:
            try:
                asyncio.run(add_barcodes_in_cash(cash_info.ip, cash_number))
                asyncio.run(update_price_in_cash(cash_info.ip, cash_number))
            except sqlalchemy.exc.OperationalError as ex:
                if re.findall(r"Can't connect to MySQL server", str(ex)):
                    print(f'Не в сети {cash_info.ip}')
