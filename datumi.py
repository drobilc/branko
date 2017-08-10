# -*- coding: utf-8 -*-
import datetime
import re

regexDatum = re.compile("(\d{2}\.\d{2}\.\d{4})")

datumi = {"danes": 0,
          "vceraj": -1,
          "včeraj": -1,
          "predvcerajsnjim": -2,
          "predvčerajšnjim": -2,
          "jutri": 1,
          "pojutrijsnjem": 2,
          "pojutrijšnjem": 2
         }

dnevi = ["ponedeljek", "torek", "sreda", "cetrtek", "petek", "sobota", "nedelja"]
dneviSumniki = ["ponedeljek", "torek", "sreda", "četrtek", "petek", "sobota", "nedelja"]

def vDatum(kljucnaBeseda=""):
    danes = datetime.datetime.now()
    zadetki = regexDatum.search(kljucnaBeseda)

    if kljucnaBeseda in datumi:
        steviloDni = datumi[kljucnaBeseda]
        return danes + datetime.timedelta(days=steviloDni)
    elif kljucnaBeseda in dnevi:
        #Poiscemo naslednji dan
        zaporednaStevilkaDne = dnevi.index(kljucnaBeseda)
        if zaporednaStevilkaDne > danes.weekday():
            return danes + datetime.timedelta(days=zaporednaStevilkaDne - danes.weekday())
        else:
            #Pristejemo 1 teden in odstejemo par dni
            steviloDni = 7 - (danes.weekday() - zaporednaStevilkaDne)
            return danes + datetime.timedelta(days=steviloDni)
    elif kljucnaBeseda in dneviSumniki:
        #Poiscemo naslednji dan
        zaporednaStevilkaDne = dneviSumniki.index(kljucnaBeseda)
        if zaporednaStevilkaDne > danes.weekday():
            return danes + datetime.timedelta(days=zaporednaStevilkaDne - danes.weekday())
        else:
            #Pristejemo 1 teden in odstejemo par dni
            steviloDni = 7 - (danes.weekday() - zaporednaStevilkaDne)
            return danes + datetime.timedelta(days=steviloDni)
    elif zadetki:
        zadetek = zadetki.group()
        dat = datetime.datetime.strptime(kljucnaBeseda, '%d.%m.%Y')
        return dat 
    return danes