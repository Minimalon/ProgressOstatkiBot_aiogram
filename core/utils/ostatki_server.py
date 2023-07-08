import asyncio
import os
from datetime import datetime as dt
import config
from core.database.query_PROGRESS import get_cash_info


async def get_last_file(inn: str, fsrar: str):
    """
    Получает инн и фсрар точки
    Возвращает путь к файлу и его в формате '%d-%m-%Y %H:%m'
    """
    dir_path = os.path.join(config.server_path, 'ostatki', inn, fsrar, 'xls')
    files = [os.path.join(dir_path, file) for file in os.listdir(dir_path)]
    if not files:
        return False

    ostatki = [file for file in files if os.path.isfile(file)]
    last_file = max(ostatki, key=os.path.getctime)
    date = last_file.split(os.sep)[-1].split('.')[0]
    date_file = dt.strptime(date, '%Y_%m_%d__%H_%M').strftime('%d-%m-%Y %H:%M')
    print(date, date_file)
    return last_file, date_file


async def get_last_files(inn: str, fsrar: str):
    """
    Получает инн и фсрар точки
    Возвращает список [[путь к файлу, date('%d-%m-%Y %H:%m)],...]
    """
    dir_path = os.path.join(config.server_path, 'ostatki', inn, fsrar, 'xls')
    files = [os.path.join(dir_path, file) for file in os.listdir(dir_path)]
    if not files:
        return False

    ostatki = [file for file in files if os.path.isfile(file)]
    ostatki = sorted(ostatki, key=os.path.getctime)
    ostatki.reverse()
    result = []
    for file in ostatki[:6]:
        ostatki_file_path = file.split(os.sep)[-1]
        date = ostatki_file_path.split('.')[0]
        date_file = dt.strptime(date, '%Y_%m_%d__%H_%M').strftime('%d-%m-%Y %H:%M')
        result.append([ostatki_file_path, date_file])
    return result


if __name__ == '__main__':
    cash_info = get_cash_info('123')
    asyncio.run(get_last_files(cash_info.inn, cash_info.fsrar))
