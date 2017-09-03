import malica
import datetime
import json
import graf
import glob

def soPodatkiZePreneseni(uporabnik):
	datoteke = glob.glob("podatki/{}.json".format(uporabnik.uporabniskoIme))
	return len(datoteke) > 0;

def soGrafiZeIzdelani(uporabnik):
    datoteke = glob.glob("{}*.html".format(uporabnik.uporabniskoIme))
    return len(datoteke) > 0;

def prenesiVsePodatkeUporabnika(uporabnik):
    #Gremo od danes nazaj dokler ne naletimo na prazno mnozico podatkov
    #Danasnji datum
    danes = datetime.datetime.now()

    #Datum 5 let nazaj (1. september)
    zacetniDatum = datetime.datetime(danes.year - 5, 9, 1)

    #Generiramo vse tedne med zacetnimDatumom in danes (52 tednov)
    datumi = [zacetniDatum + datetime.timedelta(i * 7) for i in range(52 * 5)]

    podatki = {}
    for datum in datumi:
        podatkiTeden = uporabnik.pridobiPodatke(datum)
        #print "Podatki za datum {}: {}".format(datum.strftime("%d.%m.%Y"), str(podatkiTeden))
        #Vsak dan vpisemo v slovar podatkov
        for dan in range(len(podatkiTeden)):
            podatkiDan = podatkiTeden[dan]
            datumDan = datum + datetime.timedelta(dan)
            podatki[datumDan] = podatkiDan

    pretvorjeniPodatki = {}
    for kljuc in podatki:
        novKljuc = kljuc.strftime("%Y-%m-%d")
        pretvorjeniPodatki[novKljuc] = podatki[kljuc]

    #Podatki so pridobljeni, shranimo jih v datoteko
    with open('podatki/{}.json'.format(uporabnik.uporabniskoIme), 'w') as datoteka:
        json.dump(pretvorjeniPodatki, datoteka)

    return '{}.json'.format(uporabnik.uporabniskoIme)

def ustvariGrafe(imeDatoteke, uporabnik):
    with open(imeDatoteke, 'r') as datoteka:
        podatkiZaPretvorit = json.load(datoteka)

    #Pretvorimo datume iz stringa v datetime objekt
    podatki = {}
    for kljuc in podatkiZaPretvorit:
        datum = datetime.datetime.strptime(kljuc, "%Y-%m-%d")
        podatki[datum] = podatkiZaPretvorit[kljuc]

        #Narisemo vse 3 grafe
        graf.narisiGrafTeden(podatki, "grafi/{}_dnevni.html".format(uporabnik.uporabniskoIme))
        graf.narisiGrafMesec(podatki, "grafi/{}_mesecni.html".format(uporabnik.uporabniskoIme))
        graf.narisiTortniDiagram(podatki, "grafi/{}_tortni.html".format(uporabnik.uporabniskoIme))

