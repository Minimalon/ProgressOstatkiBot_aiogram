import re

from funcy import str_join


def phone(client_phone):
    client_phone = str_join(sep="", seq=re.findall(r'[0-9]*', client_phone))
    if re.findall(r'^89', client_phone):
        return re.sub(r'^89', '79', client_phone)
    return client_phone


def ostatki_date(date):
    return f'Остатки <b><u>{date}</u></b>\n\nЧтобы получить более свежие остатки, обратитесь к нам в тех.поддержку'


def accept_text(boxs):
    text = '➖➖➖<b><u>Коробки для приёма</u></b>➖➖➖\n'
    text += 'Название | Обьем | Кол-во бутылок\n'
    text += '➖' * 15 + '\n'
    count = 0
    for box in boxs:
        if not box.scaned:
            text += f'{box.name} | {box.capacity[:4]}л | {box.count_bottles}шт\n'
        else:
            text += f'<s>{box.name} | {box.capacity[:4]}л | {box.count_bottles}шт</s>✅\n'
            count += 1
    text += '➖' * 15 + '\n'
    text += f'Принято <b><u>{count}</u></b> из <b><u>{len(boxs)}</u></b> коробок'
    return text

def divirgence_text(boxs):
    text = '<b><u>Ниже перечисленные коробки не будут потдверждены</u></b>\n'
    text += 'Название | Обьем | Кол-во бутылок | Номер коробки\n'
    text += '➖' * 15 + '\n'
    for box in boxs:
        if not box.scaned:
            text += f'{box.name} | {box.capacity[:4]}л | {box.count_bottles}шт | {box.boxnumber}\n'
    text += '➖' * 15 + '\n'
    return text


def beer_accept_text(bottles):
    text = '➖➖➖<b><u>Бутылки для приёма</u></b>➖➖➖\n'
    text += 'Название | Кол-во бутылок\n'
    text += '➖' * 15 + '\n'
    for bottle in bottles:
        text += f'{bottle.name} | {bottle.quantity}шт\n'
    return text


error_head = f"➖➖➖➖➖🚨ОШИБКА🚨➖➖➖➖➖\n"
error_cashNumber = error_head + f'Нужны только цифры. Например: <b><u>902</u></b>\n<b>Попробуйте снова</b>'
error_fake_client_phone = error_head + f'Вы отправили чужой сотовый'
error_duplicateCash = error_head + 'С данным номером компьютера зарегистрировано больше одной кассы\nОбратитесь в тех поддрежку.'
error_cash_not_found = error_head + 'Данная касса не найдена\nОбратитесь в тех поддрежку.'

menu = (f'<u><b>Остатки</b></u> - Получить остатки\n\n'
        f'<u><b>Накладные</b></u> - Операции с накладными')
need_registration = ('Нужно пройти регистрацию в боте.\n'
                     f'Нажмите на кнопку <u><b>Регистрация</b></u>\n')
succes_registration = 'Регистрация успешно пройдена'
WayBills = (f'<u><b>Подтвердить накладные</b></u> - Подтвердить не принятые накладные.\n\n'
            f'<u><b>Список</b></u> - Выведем информацию о последних десяти накладных.')
ostatki = (f'<u><b>Последние остатки</b></u> - Получить последние сгенерированные остатки\n\n'
           f'<u><b>Список по датам</b></u> - Выведем даты последних 6 сгенерированных остатков')
enter_cash_number = 'Напишите номер компьютера:\nНужны только цифры. Например: <b><u>902</u></b>'
list_ostatki = 'Выберите нужную дату остатков'
choose_entity = 'Выберите нужное юр.лицо'