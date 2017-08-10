# -*- coding: utf-8 -*-
import plotly
import plotly.graph_objs as go

dnevi = ["Ponedeljek", "Torek", "Sreda", "Četrtek", "Petek", "Sobota", "Nedelja"]
meseci = ["Januar", "Februar", "Marec", "April", "Maj", "Junij", "Julij", "Avgust", "September", "Oktober", "November", "December"]

def narisiGrafTeden(podatki, pot):

    tipiMalic = set(podatki.values())

    #Sortiramo podatke glede na dan v tednu
    podatkiPoDnevih = [dict.fromkeys(tipiMalic, 0) for i in range(7)]
    for dan in podatki:
        danVTednu = dan.weekday()
        podatkiPoDnevih[danVTednu][podatki[dan]] += 1

    #Narisemo graf
    data = []
    for tip in tipiMalic:
        data.append(go.Bar(x = dnevi, y = [p[tip] for p in podatkiPoDnevih], name=tip))

    layout = go.Layout(barmode='stack')
    fig = go.Figure(data=data, layout=layout)

    plotly.offline.plot(fig, filename=pot)

def narisiGrafMesec(podatki, pot):
    zaPrikaz = ["OSN", "SUH"]
    
    #Sortiramo podatke glede na dan v tednu
    podatkiPoMesecih = [dict.fromkeys(zaPrikaz, 0) for i in range(12)]
    for dan in podatki:
        mesec = dan.month - 1
        if podatki[dan] in zaPrikaz:
            podatkiPoMesecih[mesec][podatki[dan]] += 1

    #Narisemo graf
    data = []
    for tip in zaPrikaz:
        data.append(go.Bar(x = meseci, y = [p[tip] for p in podatkiPoMesecih], name = tip))
    layout = go.Layout(barmode='stack')
    fig = go.Figure(data=data, layout=layout)
    plotly.offline.plot(fig, filename=pot)

def narisiTortniDiagram(podatki, pot):
    tipiMalic = set(podatki.values())
    
    #Uredimo podatke glede na tip malice
    urejeniPodatki = dict.fromkeys(tipiMalic, 0)
    for dan in podatki:
        urejeniPodatki[podatki[dan]] += 1

    #Narisemo tortni diagram
    trace = [go.Pie(labels=urejeniPodatki.keys(), values=[urejeniPodatki[k] for k in urejeniPodatki])]
    plotly.offline.plot(trace, filename=pot)
