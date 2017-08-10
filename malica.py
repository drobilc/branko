import requests
from bs4 import BeautifulSoup
import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Malica(object):

    def __init__(self, uporabniskoIme, geslo):
        self.uporabniskoIme = uporabniskoIme

        self.seja = requests.Session()
        glava = {'User-agent': 'Mozilla/4.0 (compatible; MSIE 6.0; ' 'Windows NT 5.2; .NET CLR 1.1.4322)'}
        parametri = {'UserName': uporabniskoIme, 'Password': geslo, 'RememberMe': 'true'}
        r = self.seja.post("https://malica.scng.si/Account/LogOn?ReturnUrl=%2f", headers=glava, params=parametri, verify=False)

        html = BeautifulSoup(r.text, "html.parser")

        error = html.find("div", {"class":"validation-summary-errors"})
        if error:
            raise Exception("Prijava neuspesna", error.text)

    def izlusciPodatke(self, html):
        html = BeautifulSoup(html, "html.parser")
        tabela = html.findAll('td')
        teden = [stolpec.text.strip() for stolpec in tabela][2:]
        return teden

    def pridobiPodatke(self, datum):
        pretvorjenDatum = datum.strftime("%m/%d/%Y")
        parametri = {"nextDateStart": pretvorjenDatum}
        response = self.seja.get("https://malica.scng.si/Home/Test", params=parametri)
        return self.izlusciPodatke(response.text)

    def pridobiPodatkeNaDan(self, datum):
        return self.pridobiPodatke(datum)[0]

    def pridobiPodatkeDanes(self):
        danes = datetime.date.today()
        return self.pridobiPodatkeNaDan(danes)

    def pridobiPodatkeTaTeden(self):
        danes = datetime.date.today()
        datum = danes - datetime.timedelta(days=danes.weekday())
        return self.pridobiPodatke(datum)

    def odjava(self, datum):
        pretvorjenDatum = datum.strftime("%d.%m.%Y")
        parametri = {'dnevi' : 'td_231_2_' + pretvorjenDatum, 'hid2' : '', 'act' : 'ODJ'}
        response = self.seja.post("https://malica.scng.si/Home/OdjaviSpremembeMeni", params=parametri)

    def prijava(self, datum):
        pretvorjenDatum = datum.strftime("%d.%m.%Y")
        parametri = {'dnevi' : 'td_231_2_' + pretvorjenDatum, 'hid2' : '', 'act' : 'PRJ'}
        response = self.seja.post("https://malica.scng.si/Home/PrijaviSpremembeMeni", params=parametri)

    def zamenjava(self, datum, tip="SUH"):
        pretvorjenDatum = datum.strftime("%d.%m.%Y")
        parametri = {'dnevi' : 'td_231_2_' + pretvorjenDatum, 'hid2' : tip, 'act' : 'ZAM'}
        response = self.seja.post("https://malica.scng.si/Home/ZamenjajSpremembeMeni", params=parametri)