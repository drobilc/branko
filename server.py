# -*- coding: utf-8 -*-
from flask import Flask, request, redirect, render_template
from flask import send_from_directory
from messengerbot import MessengerClient, messages, attachments, templates, elements, users
import sqlite3 as lite
import requests
import random
import json
import malica, datumi
import prenesipodatke
import threading
import time

#Preberemo spremenljivke iz datoteke
with open('config.json') as data_file:
    data = json.load(data_file)

access_token = data["access_token"]
mysql_host = data["mysql_host"]
mysql_user = data["mysql_user"]
mysql_password = data["mysql_password"]
mysql_database = data["mysql_database"]
app_url = data["app_url"]
server_url = data["server_url"]
sole = data["sole"]

gumbPrijava = elements.AccountLinkingButton(url="{}{}".format(server_url, "/prijava"))
gumbiZaSePrijavit = templates.ButtonTemplate(text='Preden te lahko odjavljam od malice me moraš pooblastiti.', buttons=[gumbPrijava])
priponkaPrijava = attachments.TemplateAttachment(template=gumbiZaSePrijavit)

topelObrokEmojiji = ["🍝", "🍕", "🍗", "🍖", "🍱", "🍜", "🍛", "🍲"]
suhObrokEmojiji = ["🍞", "🍰", "🍩", "🍪", "🍔", "🍟"]

# Kaj je mozno napisati Branku
gumbPodatki = elements.PostbackButton(title="Podatki danes", payload="podatki danes")
gumbOdjava = elements.PostbackButton(title="Odjava danes", payload="odjava danes")
gumbPrijava = elements.PostbackButton(title="Prijava danes", payload="prijava danes")
vsiGumbi = [gumbPodatki, gumbOdjava, gumbPrijava]
gumbiPomoc = templates.ButtonTemplate(text='Kako ti lahko pomagam?', buttons=vsiGumbi)
priponkaPomoc = attachments.TemplateAttachment(template=gumbiPomoc)

prenasanjePodatkov = []

class Baza:
	conn = None
	def __init__(self, host, user, password, db):
		#self.host = host
		#self.user = user
		#self.password = password
		#self.db = db
		pass
	def connect(self):
		self.conn = lite.connect('baza.db')
		self.query("CREATE TABLE IF NOT EXISTS uporabnik (id varchar(20) NOT NULL, uporabnisko_ime varchar(20) DEFAULT NULL, geslo varchar(30) DEFAULT NULL, PRIMARY KEY (id))")
		self.commit()
	def query(self, sql):
		try:
			cursor = self.conn.cursor()
			cursor.execute(sql)
		except (Exception):
			self.connect()
			cursor = self.conn.cursor()
			cursor.execute(sql)
		return cursor
	def commit(self):
		self.conn.commit()

#Zazenemo spletno aplikacijo (Flask aplikacija)
app = Flask(__name__, static_url_path='')

bazaPodatkov = Baza(mysql_host, mysql_user, mysql_password, mysql_database)

messenger = MessengerClient(access_token=access_token)

def najdiUporabnikaVBazi(fbid):
	kurzor = bazaPodatkov.query("SELECT * FROM uporabnik WHERE id = '{}'".format(fbid))
	vrstica = kurzor.fetchone()
	return vrstica

def tipka(user_id):
	data = {"recipient": {"id": user_id}, "sender_action": "typing_on"}
	resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + access_token, json=data)

def reply(user, message):
	recipient = messages.Recipient(recipient_id = user)
	message = messages.Message(text=message)
	req = messages.MessageRequest(recipient, message)
	messenger.send(req)

#Messengerjevo preverjanje streznika
@app.route('/', methods=['GET'])
def handle_verification():
	return request.args['hub.challenge']

def pp(uporabnik, sender):
	recipient = messages.Recipient(recipient_id = sender)
	imeDatoteke = prenesipodatke.prenesiVsePodatkeUporabnika(uporabnik)
	prenesipodatke.ustvariGrafe("podatki/{}".format(imeDatoteke), uporabnik)
	prenasanjePodatkov.remove(uporabnik.uporabniskoIme)
	gumbGraf1 = elements.WebUrlButton(title='Dnevni diagram', url='{}/graf?uporabnik={}&tip=1'.format(server_url, sender))
	gumbGraf2 = elements.WebUrlButton(title='Mesečni diagram', url='{}/graf?uporabnik={}&tip=2'.format(server_url, sender))
	gumbGraf3 = elements.WebUrlButton(title='Tortni diagram', url='{}/graf?uporabnik={}&tip=3'.format(server_url, sender))
	seznamGrafov = templates.ButtonTemplate(text='S pritiskom na spodnji gumb vam lahko prikažem različne podatke', buttons=[gumbGraf1, gumbGraf2, gumbGraf3])
	grafPriponka = attachments.TemplateAttachment(template=seznamGrafov)
	message = messages.Message(attachment=grafPriponka)
	requ = messages.MessageRequest(recipient, message)
	messenger.send(requ)

# Vsakic, ko nam uporabniki posljejo sporocilo se izvede ta metoda
# Tukaj najprej najdemo uporabnika in njegovo sporocilo in glede na
# poslane podatke ustrezno reagiramo.
@app.route('/', methods=['POST'])
def handle_incoming_messages():
	data = request.json

	#Dobimo id uporabnika in sporocilo
	sender = data['entry'][0]['messaging'][0]['sender']['id']
	recipient = messages.Recipient(recipient_id = sender)

	#Ce se uporabnik prijavlja
	povezovanje = data['entry'][0]['messaging'][0]
	if povezovanje and 'account_linking' in povezovanje:
		povezovanje = povezovanje['account_linking']
		s = povezovanje["status"]
		if s and s == "linked":
			p = povezovanje["authorization_code"]
			message = messages.Message(text="Super, prijavil si se kot {}".format(p))
			req = messages.MessageRequest(recipient, message)
			messenger.send(req)
			message = messages.Message(attachment=priponkaPomoc)
			req = messages.MessageRequest(recipient, message)
			messenger.send(req)
			return "ok"
		else:
			message = messages.Message(text="Prišlo je do napake. Prosim poskusi znova.")
			req = messages.MessageRequest(recipient, message)
			messenger.send(req)
			return "ok"

	# Razen ce ni postback lahko iz podatkov najdemo message
	message = data['entry'][0]['messaging'][0]['message']['text']

	#Preverimo, ali je uporabnik ze registriran (ce se ni, mu posljemo uvodno sporocilo)
	uporabnik = najdiUporabnikaVBazi(sender)
	if not uporabnik:
		ime = imeUporabnika(sender)
		reply(sender, "Živjo {}! 😄\nSem Branko, tvoj digitalni asistent, ki ti pomaga pri odjavi in prijavi na šolsko malico.".format(ime))
		tipka(sender)
		time.sleep(0.8)
		reply(sender, "Preden ti lahko pomagam moraš imeti ustvarjen račun na šolski spletni strani za upravljanje z malico.")
		tipka(sender)
		time.sleep(1)
		message = messages.Message(attachment=priponkaPrijava)
		req = messages.MessageRequest(recipient, message)
		messenger.send(req)
		return "ok"
	
	#Ugotovimo kaj zeli uporabnik narediti
	message = message.lower()
	if message.startswith("podatki"):
		ostaliPodatki = message.replace("podatki", "").strip().split(" ")
		tipka(sender)
		print "Prijavljam uporabnika", uporabnik[0], uporabnik[1]
		uporabnik = malica.Malica(uporabnik[1], uporabnik[2])
		odgovor = []
		for dan in ostaliPodatki:
			datum = datumi.vDatum(dan)
			stanje = uporabnik.pridobiPodatkeNaDan(datum)
			if stanje == "OSN":
				odgovor.append("Dne ({}) si na toplem obroku. {}".format(datum.strftime("%d.%m.%Y"), random.choice(topelObrokEmojiji)))
			elif stanje == "SUH":
				odgovor.append("Dne ({}) si na suhem obroku. {}".format(datum.strftime("%d.%m.%Y"), random.choice(suhObrokEmojiji)))
			else:
				odgovor.append("Dne ({}) si od malice odjavljen! Pametna odločitev 😉".format(datum.strftime("%d.%m.%Y")))
		reply(sender, "\n".join(odgovor))
		return "ok"
	elif message.startswith("odjava"):
		dan = message.replace("odjava", "").strip()#.split(" ")
		tipka(sender)
		print "Prijavljam uporabnika", uporabnik[0], uporabnik[1]
		uporabnik = malica.Malica(uporabnik[1], uporabnik[2])
		datum = datumi.vDatum(dan)
		uporabnik.odjava(datum)
		reply(sender, "Dne {} si od malice odjavjen.".format(datum.strftime("%d.%m.%Y")))
		return "ok"
	elif message.startswith("prijava"):
		dan = message.replace("prijava", "").strip()#.split(" ")
		tipka(sender)
		print "Prijavljam uporabnika", uporabnik[0], uporabnik[1]
		uporabnik = malica.Malica(uporabnik[1], uporabnik[2])
		datum = datumi.vDatum(dan)
		uporabnik.prijava(datum)
		reply(sender, "Dne {} si na malico prijavljen.".format(datum.strftime("%d.%m.%Y")))
		return "ok"
	elif message.startswith("graf"):

		#Najprej uporabniku sporocimo, da bomo sedaj ustvarjali grafe
		reply(sender, "Ustvarjanje grafov traja nekaj časa, zato vas prosim za potrpežljivost. Podatke vam pošljem takoj ko jih obdelam.")
		tipka(sender)

		#Uporabnika prijavimo
		uporabnik = malica.Malica(uporabnik[1], uporabnik[2])

		#Ce ze prenasamo podatke je use kul, naj tip malo caka
		if uporabnik.uporabniskoIme in prenasanjePodatkov:
			return "ok"
		
		else:
			if not prenesipodatke.soPodatkiZePreneseni(uporabnik):
				prenasanjePodatkov.append(uporabnik.uporabniskoIme)
				thr = threading.Thread(target=pp, args=(uporabnik, sender), kwargs={})
				thr.start()
				return "ok"
			else:
				gumbGraf1 = elements.WebUrlButton(title='Dnevni diagram', url='{}/graf?uporabnik={}&tip=1'.format(server_url, sender))
				gumbGraf2 = elements.WebUrlButton(title='Mesečni diagram', url='{}/graf?uporabnik={}&tip=2'.format(server_url, sender))
				gumbGraf3 = elements.WebUrlButton(title='Tortni diagram', url='{}/graf?uporabnik={}&tip=3'.format(server_url, sender))
				seznamGrafov = templates.ButtonTemplate(text='S pritiskom na spodnji gumb vam lahko prikažem različne podatke', buttons=[gumbGraf1, gumbGraf2, gumbGraf3])
				grafPriponka = attachments.TemplateAttachment(template=seznamGrafov)
				message = messages.Message(attachment=grafPriponka)
				requ = messages.MessageRequest(recipient, message)
				messenger.send(requ)
		
		return "ok"
	else:
		reply(sender, "Oprosti, tega ukaza ne razumem. 😐")
		message = messages.Message(attachment=priponkaPomoc)
		req = messages.MessageRequest(recipient, message)
		messenger.send(req)
	return "ok"

def idUporabnika(koda):
	url = "https://graph.facebook.com/v2.6/me?access_token={}&fields=recipient&account_linking_token={}".format(access_token, koda)
	r = requests.get(url)
	podatki = r.json()
	return podatki["recipient"]

def imeUporabnika(koda):
	url = "https://graph.facebook.com/v2.6/{}?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token={}".format(koda, access_token)
	r = requests.get(url)
	podatki = r.json()
	return podatki["first_name"]

def vstaviPodatkeVBazo(uid, uporabniskoIme, geslo):
	kurzor = bazaPodatkov.query("INSERT INTO uporabnik (id, uporabnisko_ime, geslo) VALUES ({}, '{}', '{}');".format(uid, uporabniskoIme, geslo))
	bazaPodatkov.commit()

@app.route('/graf', methods=['GET'])
def prikaziGraf():
	#Rabimo id uporabnika + tip grafa
	uporabnik = request.args.get('uporabnik')
	tip = request.args.get('tip')
	uporabnik = najdiUporabnikaVBazi(uporabnik)[1] #uporabnisko ime uporabnika
	tt = ["dnevni", "mesecni", "tortni"][int(tip) - 1]
	return send_from_directory("/home/administrator/branko/grafi/", "{}_{}.html".format(uporabnik, tt))
	#return app.send_static_file("./grafi/9006723_mesecni.html")

# Prijava uporabnika na spletno stran
@app.route('/prijava', methods=['GET'])
def prijava():
	accountLinkingToken = request.args.get('account_linking_token')
	redirectUri = request.args.get('redirect_uri')
	return render_template('login.html', account_linking_token=accountLinkingToken, redirect_uri=redirectUri, sole=sole, authorization_url="{}{}".format(server_url, "/auth"))

#Avtorizacija uporabnika na stran
@app.route('/auth', methods=['POST'])
def avtorizacija():
	accountLinkingToken = request.form['account_linking_token']
	uporabniskoIme = request.form['uporabnisko_ime']
	geslo = request.form['geslo']
	sola = request.form['sola']

	print "Nov uporabnik se zeli avtorizirati, podatki: {}, {}, {}".format(uporabniskoIme, geslo, sola)

	# Najdemo uporabnikov messenger id
	uid = idUporabnika(accountLinkingToken)

	try:
		preizkusPrijave = malica.Malica(uporabniskoIme, geslo)
		vstaviPodatkeVBazo(uid, uporabniskoIme, geslo)
		preusmeritev = request.form['redirect_uri'] + "&authorization_code={}".format(uporabniskoIme)
		return redirect(preusmeritev)
	except Exception as e:
		print e.message
		preusmeritev = request.form['redirect_uri']
		return redirect(preusmeritev)

if __name__ == '__main__':
	app.run(debug=True)