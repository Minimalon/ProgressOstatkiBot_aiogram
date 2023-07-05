# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

import httpx
import requests
from bs4 import BeautifulSoup
from loguru import logger

import config
from core.utils import CURL


class UTM:
    def __init__(self, port, ip="localhost"):
        self.port = port
        self.ip = ip

    # Возвращает в dict (status, message)
    def parse_ticket_result(self, ticket):
        Response = namedtuple('Response', 'status message')
        ticket = requests.get(ticket).text
        tree = ET.fromstring(ticket)
        try:
            status = tree.find('*/*/*/{http://fsrar.ru/WEGAIS/Ticket}OperationResult').text
            message = tree.find('*/*/*/{http://fsrar.ru/WEGAIS/Ticket}OperationComment').text.strip()
        except:
            status = tree.find('*/*/*/{http://fsrar.ru/WEGAIS/Ticket}Conclusion').text
            message = tree.find('*/*/*/{http://fsrar.ru/WEGAIS/Ticket}Comments').text.strip()
        return Response(status, message)

    async def wait_answer(self, replyId, timeout=15):
        max_time = 1500
        while max_time > 0:
            print("-- Ожидание ответа от: {}".format(replyId))
            async with httpx.AsyncClient() as client:
                answer = await client.get(f"http://{self.ip}:{self.port}/opt/out?replyId={replyId}")
                url = BeautifulSoup(answer.text, 'xml').findAll("url")
            if len(url) > 1:
                return url
            max_time -= timeout
            await asyncio.sleep(timeout)

    async def get_all_opt_URLS_text(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{self.ip}:{self.port}/opt/out")
            return [url.text for url in BeautifulSoup(response.text, 'xml').findAll("url")]

    async def get_all_opt_URLS_text_by_docType(self, docType):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{self.ip}:{self.port}/opt/out?docType={docType}")
            return [url.text for url in BeautifulSoup(response.text, 'xml').findAll("url")]

    async def get_Waybill_and_FORM2REGINFO(self):
        """Возвращает namedtuple('TTNS', 'id_f2r id_wb ttn_egais shipper_name date wbnumber')"""
        TTNS = namedtuple('TTNS', 'id_f2r id_wb ttn_egais shipper_name date wbnumber')
        urls_form = await self.get_all_opt_URLS_text_by_docType("FORM2REGINFO")
        urls_wb = await self.get_all_opt_URLS_text_by_docType("WayBill_v4")
        if len(urls_form) == 0 and len(urls_wb) == 0:
            print("\033[31m{}\033[0m".format("Нету накладных"))
            logger.error("Нету накладных")
            return False
        if len(urls_form) == 0:
            print("\033[31m{}\033[0m".format("Нету FORM2REGINFO"))
            logger.error("Нету FORM2REGINFO")
            return False
        if len(urls_wb) == 0:
            print("\033[31m{}\033[0m".format("Нету Waybill_v4"))
            logger.error("Нету Waybill_v4")
            return False
        ttns = []
        for url_form in urls_form:
            async with httpx.AsyncClient() as client:
                req = (await client.get(url_form)).text
            TTN = ET.fromstring(req).find('*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}WBRegId').text
            WBNUMBER = ET.fromstring(req).find('*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}WBNUMBER').text
            SHIPPER_NAME = ET.fromstring(req).find('*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Shipper/*/{http://fsrar.ru/WEGAIS/ClientRef_v2}ShortName').text
            # if "саман" in SHIPPER_NAME.lower():
            #     continue
            date = ET.fromstring(req).find('*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}WBDate').text
            for url_wb in urls_wb:
                async with httpx.AsyncClient() as client:
                    req = (await client.get(url_wb)).text
                NUMBER = ET.fromstring(req).find('*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}NUMBER').text
                if NUMBER == WBNUMBER:
                    ttns.append(TTNS(url_form.split('/')[-1], url_wb.split('/')[-1], TTN, SHIPPER_NAME, date, NUMBER))
        return ttns

    def send_QueryRestBCode(self, FB: str):
        files = {'xml_file': CURL.QueryRestBCode(self.get_fsrar(), FB)
                 }
        response = requests.post('http://' + self.ip + ':' + self.port + '/opt/in/QueryRestBCode', files=files)
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            logger.info(f"QueryFormB отправлен  request_id: {request_id}")
            return request_id
        else:
            logger.error("QueryFormB не отправлен")
            logger.error(f"HTTP code {str(response.status_code)} != 200")
            return False

    def send_QueryRests_v2(self):
        files = {
            'xml_file': CURL.QueryRests_v2(self.get_fsrar())
        }
        response = requests.post('http://' + self.ip + ':' + self.port + '/opt/in/QueryRests_v2', files=files)
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            print("\033[32m{}, request_id: {}\033[0m".format("QueryRests_v2 отправлен", request_id))
            return request_id
        else:
            print("\033[31m{}\033[0m".format("QueryRests_v2 не отправлен"))
            print("\033[31m{}\033[0m".format("HTTP code != 200 --- " + "status code = " + str(response.status_code)))
            exit(1)

    def send_QueryRestsShop_V2(self):
        files = {
            'xml_file': CURL.QueryRestsShop_V2(self.get_fsrar())
        }
        response = requests.post('http://' + self.ip + ':' + self.port + '/opt/in/QueryRestsShop_V2', files=files)
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            print("\033[32m{}, request_id: {}\033[0m".format("QueryRestsShop_V2 отправлен", request_id))
            return request_id
        else:
            print("\033[31m{}\033[0m".format("QueryRestsShop_V2 не отправлен"))
            print("\033[31m{}\033[0m".format("HTTP code != 200 --- " + "status code = " + str(response.status_code)))
            exit(1)

    def send_ActWriteOff_v3(self, QueryRests_v2_xml_string):
        if QueryRests_v2_xml_string:
            result = []
            products = ET.fromstring(QueryRests_v2_xml_string).findall("*/*/*/{http://fsrar.ru/WEGAIS/ReplyRests_v2}StockPosition")
            for identity, product in enumerate(products, 1):
                body = """                <awr:Position>
                    <awr:Identity>{}</awr:Identity>
                    <awr:Quantity>{}</awr:Quantity>
                    <awr:InformF1F2>
                        <awr:InformF2>
                            <pref:F2RegId>{}</pref:F2RegId>
                        </awr:InformF2>
                    </awr:InformF1F2>
                </awr:Position>\n""".format(str(identity), product.find("{http://fsrar.ru/WEGAIS/ReplyRests_v2}Quantity").text,
                                            product.find("{http://fsrar.ru/WEGAIS/ReplyRests_v2}InformF2RegId").text)
                result.append(body)

            files = {
                'xml_file': CURL.ActWriteOff_v3(self.get_fsrar(), result)
            }
            response = requests.post('http://' + self.ip + ':' + self.port + '/opt/in/ActWriteOff_v3', files=files)
            if response.status_code == 200:
                request_id = BeautifulSoup(response.text, "xml").find("url").text
                print("\033[32m{}, request_id: {}\033[0m".format("ActWriteOff_v3 отправлен", request_id))
                return request_id
            else:
                print("\033[31m{}\033[0m".format("ActWriteOff_v3 не отправлен"))
                print("\033[31m{}\033[0m".format("HTTP code != 200 --- " + "status code = " + str(response.status_code)))
                exit(1)
        else:
            print("\033[31m{}\033[0m".format("QueryRests_v2_xml_string not True"))
            exit(1)

    def send_ActWriteOffShop_v2(self, QueryRestsShop_V2_xml_string):
        if QueryRestsShop_V2_xml_string:
            result = []
            tree = ET.fromstring(QueryRestsShop_V2_xml_string)
            for count, el in enumerate(tree.findall('.//{http://fsrar.ru/WEGAIS/ReplyRestsShop_v2}ShopPosition'), 1):
                try:
                    Quantity = el.find('{http://fsrar.ru/WEGAIS/ReplyRestsShop_v2}Quantity').text
                    FullName = el.find('.//{http://fsrar.ru/WEGAIS/ProductRef_v2}FullName').text
                    AlcCode = el.find('.//{http://fsrar.ru/WEGAIS/ProductRef_v2}AlcCode').text
                    Capacity = el.find('.//{http://fsrar.ru/WEGAIS/ProductRef_v2}Capacity').text
                    UnitType = el.find('.//{http://fsrar.ru/WEGAIS/ProductRef_v2}UnitType').text
                    AlcVolume = el.find('.//{http://fsrar.ru/WEGAIS/ProductRef_v2}AlcVolume').text
                    ProductVCode = el.find('.//{http://fsrar.ru/WEGAIS/ProductRef_v2}ProductVCode').text
                    ClientRegId = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}ClientRegId').text
                    INN = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}INN').text
                    KPP = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}KPP').text
                    FullName_UL = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}FullName').text
                    ShortName = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}ShortName').text
                    Country = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}Country').text
                    RegionCode = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}RegionCode').text
                    description = el.find('.//{http://fsrar.ru/WEGAIS/ClientRef_v2}description').text

                    position = """
                            <awr:Position>
                      <awr:Identity>{0}</awr:Identity>
                      <awr:Quantity>{1}</awr:Quantity>
                      <awr:Product>
                        <pref:FullName>{2}</pref:FullName>
                        <pref:AlcCode>{3}</pref:AlcCode>
                        <pref:Capacity>{4}</pref:Capacity>
                        <pref:UnitType>{5}</pref:UnitType>
                        <pref:AlcVolume>{6}</pref:AlcVolume>
                        <pref:ProductVCode>{7}</pref:ProductVCode>
                        <pref:Producer>
                          <oref:UL>
                            <oref:ClientRegId>{8}</oref:ClientRegId>
                            <oref:FullName>{9}"</oref:FullName>
                            <oref:ShortName>{10}</oref:ShortName>
                            <oref:INN>{11}</oref:INN>
                            <oref:KPP>{12}</oref:KPP>
                            <oref:address>
                              <oref:Country>{13}</oref:Country>
                              <oref:RegionCode>{14}</oref:RegionCode>
                              <oref:description>{15}</oref:description>
                            </oref:address>
                          </oref:UL>
                        </pref:Producer>
                      </awr:Product>
                    </awr:Position>
                    """.format(count, Quantity, FullName, AlcCode, Capacity, UnitType, AlcVolume, ProductVCode, ClientRegId, INN, KPP, FullName_UL, ShortName, Country,
                               RegionCode, description)
                    result.append(position)
                except Exception as e:
                    print(e)
            with open('test.xml', 'w', encoding='utf-8') as f:
                f.write(CURL.ActWriteOffShop_v2(self.get_fsrar(), result))
                """
                ТЕСТЫ СПИСАНИЯ
                """
        #     files = {
        #         'xml_file': CURL.ActWriteOffShop_v2(self.get_fsrar(), result)
        #     }
        #     response = requests.post('http://' + self.ip + ':' + self.port + '/opt/in/ActWriteOffShop_v2', files=files)
        #     if response.status_code == 200:
        #         request_id = BeautifulSoup(response.text, "xml").find("url").text
        #         print("\033[32m{}, request_id: {}\033[0m".format("ActWriteOffShop_v2 отправлен", request_id))
        #         return request_id
        #     else:
        #         print("\033[31m{}\033[0m".format("ActWriteOffShop_v2 не отправлен"))
        #         print("\033[31m{}\033[0m".format("HTTP code != 200 --- " + "status code = " + str(response.status_code)))
        #         exit(1)
        # else:
        #     print("\033[31m{}\033[0m".format("QueryRests_v2_xml_string not True"))
        #     exit(1)

    async def send_WayBillv4(self, TTN):
        """
        Отправляет акт приёма ТТН
        Принимает только одну накладную
        TTN = только цифры
        """

        files = {
            'xml_file': CURL.WayBillAct_v4(TTN, self.get_fsrar())
        }
        async with httpx.AsyncClient() as client:
            response = (await client.post(f'http://{self.ip}:{self.port}/opt/in/WayBillAct_v4', files=files))
        return response

    def check_utm_error(self):
        try:
            status_UTM = requests.get('http://' + self.ip + ':' + self.port, timeout=2).ok
        except Exception as ex:
            print("\033[31m{}\033[0m".format(ex))
            status_UTM = False
        return status_UTM

    async def check_beer_waybill(self, url_WB, port):
        async with httpx.AsyncClient() as client:
            response = await client.get(url_WB)
            WB = BeautifulSoup(response.text, "xml")
            beer_WB = ET.fromstring(response.text)
        beer = False
        if len(WB.findAll('amc')) == 0:
            beer = True
        elif len(WB.findAll('boxnumber')) == 0:
            beer = True
        elif port == '18082':
            beer = True

        if beer:
            ttn = namedtuple('Bottles', 'name quantity')
            Positions = beer_WB.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position")
            result = []
            for pos in Positions:
                Product = pos.find('{http://fsrar.ru/WEGAIS/TTNSingle_v4}Product')
                FullName = Product.find('{http://fsrar.ru/WEGAIS/ProductRef_v2}FullName').text
                Quantity = pos.find('{http://fsrar.ru/WEGAIS/TTNSingle_v4}Quantity').text
                result.append(ttn(FullName, Quantity))
            return result
        return beer

    async def send_divirgence_ttn(self, url_WB, url_f2r, boxs, ttn_egais):

        async def get_informr2regid(identity):
            async with httpx.AsyncClient() as client:
                F2R = ET.fromstring((await client.get(url_f2r)).text)
            Positions = F2R.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Position")
            for pos in Positions:
                Identity = pos.find('{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Identity').text
                if identity == Identity:
                    InformF2RegId = pos.find('{http://fsrar.ru/WEGAIS/TTNInformF2Reg}InformF2RegId').text
                    return InformF2RegId

        boxes = namedtuple("Boxes", "identity quantity amc informF2RegId")
        boxs_not_scanned = [box.boxnumber for box in boxs if not box.scaned]
        async with httpx.AsyncClient() as client:
            WB = ET.fromstring((await client.get(url_WB)).text)

        Positions = WB.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position")
        result = []
        for pos in Positions:
            amc = []
            Identity = pos.find('{http://fsrar.ru/WEGAIS/TTNSingle_v4}Identity').text
            InformF2RegId = await get_informr2regid(Identity)
            Quantity = pos.find('{http://fsrar.ru/WEGAIS/TTNSingle_v4}Quantity').text
            boxs = pos.findall('*/*/{http://fsrar.ru/WEGAIS/CommonV3}boxpos')
            for box in boxs:
                boxnumber = box.find('{http://fsrar.ru/WEGAIS/CommonV3}boxnumber').text
                if boxnumber not in boxs_not_scanned:
                    amcs = box.findall('*/{http://fsrar.ru/WEGAIS/CommonV3}amc')
                    Quantity = int(Quantity) - len(amcs)
                    for a in amcs:
                        amc.append(a.text)
            result.append(boxes(Identity, Quantity, amc, InformF2RegId))
        files = {'xml_file': CURL.divirgence_ttn(fsrar=self.get_fsrar(), boxes=result, ttn_egais=ttn_egais)}
        async with httpx.AsyncClient() as client:
            response = await client.post(f'http://{self.ip}:{self.port}/opt/in/WayBillAct_v4', files=files)
        return response

    async def get_box_info_from_Waybill(self, url_WB):
        """
        Возвращает Box(name, capacity, boxnumber, count_bottles, amarks, scaned)
        """
        boxinfo = namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned')
        async with httpx.AsyncClient() as client:
            WB = ET.fromstring((await client.get(url_WB)).text)
        Positions = WB.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position")
        result = []
        for pos in Positions:
            Product = pos.find('{http://fsrar.ru/WEGAIS/TTNSingle_v4}Product')
            FullName = Product.find('{http://fsrar.ru/WEGAIS/ProductRef_v2}FullName').text
            ShortName = Product.find('{http://fsrar.ru/WEGAIS/ProductRef_v2}ShortName')
            if ShortName:
                ShortName = ShortName.text
            else:
                ShortName = False
            Capacity = Product.find('{http://fsrar.ru/WEGAIS/ProductRef_v2}Capacity').text
            boxs = pos.findall('*/*/{http://fsrar.ru/WEGAIS/CommonV3}boxpos')
            for box in boxs:
                boxnumber = box.find('{http://fsrar.ru/WEGAIS/CommonV3}boxnumber').text
                if boxnumber not in [b.boxnumber for b in result]:
                    amarks = [box.text for box in box.findall('*/{http://fsrar.ru/WEGAIS/CommonV3}amc')]
                    count_bottles_in_box = len(amarks)
                    if ShortName:
                        result.append(boxinfo(ShortName, Capacity, boxnumber, count_bottles_in_box, amarks, False))
                    else:
                        result.append(boxinfo(FullName, Capacity, boxnumber, count_bottles_in_box, amarks, False))
        return result

    def get_accepted_ttn(self):
        """
        Отдаёт принятые ТТНки списком [[ttnNumber, ...]]
        """
        urls = ET.fromstring(requests.get("http://" + self.ip + ":" + self.port + "/opt/out").text).findall("url")
        tickets = [line.text for line in urls if re.findall('Ticket', line.text)]
        result = []
        for tic in tickets:
            text = requests.get(tic).text
            if text:
                if re.findall('подтверждена', text):
                    ttn = re.findall('TTN-[0-9]+', text)[0]
                    result.append(re.findall('[0-9]+', ttn)[0])

        return result

    async def add_to_whitelist(self, url_WB, boxs, cash):
        """
        Добавляет в белый список акцизы
        Принимает :
        url_WB = Полная ссылка на накладную
        boxs = Коробки
        cash = Только цифры компа
        """
        boxs_not_scanned = [box.boxnumber for box in boxs if not box.scaned]
        async with httpx.AsyncClient() as client:
            WB = ET.fromstring((await client.get(url_WB)).text)
        if not os.path.exists(os.path.join(config.server_path, 'whitelist', cash, 'amark.txt')):
            os.makedirs(os.path.join(config.server_path, 'whitelist', cash, 'amark.txt'))
        with open(os.path.join(config.server_path, 'whitelist', cash, 'amark.txt'), 'a+') as file:
            Positions = WB.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position")
            for pos in Positions:
                boxs = pos.findall('*/*/{http://fsrar.ru/WEGAIS/CommonV3}boxpos')
                EAN = pos.find('{http://fsrar.ru/WEGAIS/TTNSingle_v4}EAN13')
                for box in boxs:
                    boxnumber = box.find('{http://fsrar.ru/WEGAIS/CommonV3}boxnumber').text
                    if boxnumber not in boxs_not_scanned:
                        amcs = box.findall('*/{http://fsrar.ru/WEGAIS/CommonV3}amc')
                        for a in amcs:
                            if EAN:
                                file.write(f'{a} {EAN.text}\n')
                            else:
                                file.write(f'{a}')

    def get_ReplyNATTN(self):
        """
        Отдаёт ТТНки списком [[TTN, ttnNumber, %Y-%m-%d, shipperFsrar]]
        """
        urls = BeautifulSoup(requests.get("http://" + self.ip + ":" + self.port + "/opt/out").text, 'xml').findAll("url")
        tickets = [line.text for line in urls if re.findall('ReplyNATTN', line.text)]
        for ticket in tickets:
            ReplyNATTN = BeautifulSoup(requests.get(ticket).text, 'xml')
            if tickets:
                try:
                    date_NATTN = ReplyNATTN.find("ReplyDate").text.split("T")[0]
                    if datetime.strftime(datetime.now(), "%Y-%m-%d") == date_NATTN:
                        TTNs = ReplyNATTN.findAll("WbRegID")
                        ttnNumber = ReplyNATTN.findAll("ttnNumber")
                        ttnDate = ReplyNATTN.findAll("ttnDate")
                        Shipper = ReplyNATTN.findAll("Shipper")

                        result = []
                        for index, ttn in enumerate(TTNs):
                            if re.findall("^0[5-9]", ttn.string.split("-")[1]):
                                ttn = ttn.string.split("-")[1] + " " + str(ttnNumber[index].text) + " " + str(
                                    ttnDate[index].text) + " " + str(Shipper[index].text)
                                result.append(ttn.split())
                        return result
                    else:
                        print("Дата ReplyNATTN больше суток " + date_NATTN)
                        exit()
                except Exception as ex:
                    print(ex)
                    return None
            else:
                print("Нету ReplyNATTN")
                exit()

        # return tickets #requests.get(tickets[0]).text

    async def not_accepted_ttn(self):
        """
        Отдаёт ТТНки списком [[TTN, ttnNumber, %Y-%m-%d, shipperFsrar], ...]
        """
        ReplyNATTN = self.get_ReplyNATTN()
        accepted_ttn = self.get_accepted_ttn()
        tickets_rejected_or_withdrawn = [ticket for ticket in (await self.get_all_opt_URLS_text()) if re.findall('Ticket', ticket) if
                                         re.findall('отозвана|отказана', requests.get(ticket).text)]
        ttns_rejected_or_withdrawn = [re.findall('[0-9]+', self.parse_ticket_result(ttn).message)[0] for ttn in tickets_rejected_or_withdrawn]
        result = []
        if ReplyNATTN:
            for ttn in ReplyNATTN:
                if ttn[0] not in accepted_ttn and ttn[0] not in ttns_rejected_or_withdrawn:
                    result.append(ttn)

        return result

    def get_date_rutoken(self):
        date_rutoken = json.loads(requests.get("http://" + self.ip + ":" + self.port + "/api/info/list").text)["gost"]["expireDate"].split("+")[0]
        date_rutoken = datetime.strptime(date_rutoken, "%Y-%m-%d %H:%M:%S ")
        return date_rutoken

    def get_name_rutoken(self):
        name = json.loads(requests.get("http://" + self.ip + ":" + self.port + "/api/gost/orginfo").text)["cn"]
        return name

    def get_fsrar(self):
        return BeautifulSoup(requests.get("http://" + self.ip + ":" + self.port + "/diagnosis").text, 'xml').find("CN").text

    def get_cash_info(self):
        """
        Возвращает JSON формат
        {ID, Owner_ID, Full_Name, Short_Name, INN, KPP, Country_Code, Region_Code, Dejure_Address, Fact_Address, isLicense, Version_ts, pass_owner_id}
        """
        fsrar = self.get_fsrar()
        return [_ for _ in json.loads(requests.get("http://" + self.ip + ":" + self.port + "/api/rsa").text)["rows"] if _["Owner_ID"] == fsrar][0]


if __name__ == "__main__":
    utm = UTM(port="8082", ip="10.8.23.14")
    a = asyncio.run(utm.get_Waybill_and_FORM2REGINFO())
    print(a)
