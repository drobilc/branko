# -*- coding: utf-8 -*-
from flask import Flask, request, redirect, render_template, send_from_directory
from messengerbot import MessengerClient, messages, attachments, templates, elements, users
import sqlite3 as lite
import requests, random, json
import malica, datumi, prenesipodatke
import threading
import time

#Preberemo spremenljivke iz datoteke
with open('config.json') as dataFile:
    data = json.load(dataFile)

accessToken = data["access_token"]
serverUrl = data["server_url"]
sole = data["sole"]

# Ustvarimo ustrezne gumbe za povezovanje racuna
gumbPrijava = elements.AccountLinkingButton(url="{}{}".format(serverUrl, "/prijava"))
gumbiZaSePrijavit = templates.ButtonTemplate(text='Prosim prijavi se s pomočjo spodnjega gumba.', buttons=[gumbPrijava])
priponkaPrijava = attachments.TemplateAttachment(template=gumbiZaSePrijavit)

# Ustvarimo gumbe za pomoc uporabniku
gumbPodatki = elements.PostbackButton(title="Podatki", payload="podatki danes")
gumbOdjava = elements.PostbackButton(title="Odjava", payload="odjava danes")
gumbPrijava = elements.PostbackButton(title="Prijava", payload="prijava danes")
#gumbZamenjava = elements.PostbackButton(title="Zamenjava danes", payload="zamenjava danes")
gumbiPomoc = templates.ButtonTemplate(text='Kako ti lahko pomagam?', buttons=[gumbPodatki, gumbOdjava, gumbPrijava])#, gumbZamenjava])
priponkaPomoc = attachments.TemplateAttachment(template=gumbiPomoc)

# Emojiji za lepsi izgled odgovora
topelObrokEmojiji = ["🍝", "🍕", "🍗", "🍖", "🍱", "🍜", "🍛", "🍲"]
suhObrokEmojiji = ["🍞", "🍰", "🍩", "🍪", "🍔", "🍟"]

class Baza:
	conn = None
	def __init__(self):
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
bazaPodatkov = Baza()
messenger = MessengerClient(access_token=accessToken)

def findUserInDatabase(fbid):
	kurzor = bazaPodatkov.query("SELECT * FROM uporabnik WHERE id = '{}'".format(fbid))
	vrstica = kurzor.fetchone()
	return vrstica

def insertUserIntoDatabase(uid, uporabniskoIme, geslo):
	kurzor = bazaPodatkov.query("INSERT INTO uporabnik (id, uporabnisko_ime, geslo) VALUES ({}, '{}', '{}');".format(uid, uporabniskoIme, geslo))
	bazaPodatkov.commit()

def removeUserFromDatabase(uid):
	cursor = bazaPodatkov.query("DELETE FROM uporabnik WHERE id = {};".format(uid))
	bazaPodatkov.commit()

def getUserId(koda):
	url = "https://graph.facebook.com/v2.6/me?access_token={}&fields=recipient&account_linking_token={}".format(accessToken, koda)
	request = requests.get(url)
	podatki = request.json()
	return podatki["recipient"]

def getUserName(koda):
	url = "https://graph.facebook.com/v2.6/{}?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token={}".format(koda, accessToken)
	request = requests.get(url)
	podatki = request.json()
	return podatki["first_name"]

def sendMessage(recipient, text):
	message = messages.Message(text=text)
	messageRequest = messages.MessageRequest(recipient, message)
	messenger.send(messageRequest)

def typingIndicatorOn(recipient):
	data = {"recipient": {"id": recipient.recipient_id}, "sender_action": "typing_on"}
	resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token={}".format(accessToken), json=data)

def parseUserMessage(message, recipient):
	message = message.lower()

	# Tabela vseh moznih ukazov uporabnika
	allCommands = ['podatki', 'prijava', 'odjava', 'zamenjava']
	
	# Prva beseda je ukaz, vse naslednje pa dodatne informacije
	commandData = message.split(" ", 1)
	command = commandData[0]
	dateString = commandData[1] if len(commandData) > 1 else ''
	receivedMealType = ''
	if ':' in dateString:
		receivedMealType = dateString.split(':')[1].upper()
		dateString = dateString.split(':')[0]

	if command in allCommands:
		# We get user from database and log into malica.scng.si website
		userData = findUserInDatabase(recipient.recipient_id)
		user = malica.Malica(userData[1], userData[2])
		date = datumi.vDatum(dateString)
		typingIndicatorOn(recipient)

		if command == 'podatki':
			try:
				mealType = user.pridobiPodatkeNaDan(date)
				if mealType == "OSN":
					sendMessage(recipient, "Dne ({}) si na toplem obroku. {}".format(date.strftime("%d.%m.%Y"), random.choice(topelObrokEmojiji)))
				elif mealType == "SUH":
					sendMessage(recipient, "Dne ({}) si na suhem obroku. {}".format(date.strftime("%d.%m.%Y"), random.choice(suhObrokEmojiji)))
				else:
					sendMessage(recipient, "Dne ({}) si od malice odjavljen! Pametna odločitev 😉".format(date.strftime("%d.%m.%Y")))
			except Exception:
				sendMessage(recipient, "Oprostite, toda na ta datum ne morem najti podatkov...")
		elif command == 'prijava':
			pass
		elif command == 'odjava':
			user.odjava(date)
			sendMessage(recipient, "Dne {} si od malice odjavjen.".format(date.strftime("%d.%m.%Y")))
		elif command == 'zamenjava':
			if len(receivedMealType) > 0:
				user.zamenjava(date, receivedMealType)
				sendMessage(recipient, "Dne {} si na {} obroku.".format(date.strftime("%d.%m.%Y"), receivedMealType))
			else:
				gumbSuhiObrok = elements.PostbackButton(title="Suhi obrok", payload="zamenjava {}:suh".format(date.strftime("%d.%m.%Y")))
				gumbOsnovniObrok = elements.PostbackButton(title="Topli obrok", payload="zamenjava {}:osn".format(date.strftime("%d.%m.%Y")))
				gumbiZamenjava = templates.ButtonTemplate(text='Kakšen tip obroka želiš?', buttons=[gumbSuhiObrok, gumbOsnovniObrok])
				priponkaZamenjava = attachments.TemplateAttachment(template=gumbiZamenjava)
				messageZamenjava = messages.Message(attachment=priponkaZamenjava)
				messageRequest = messages.MessageRequest(recipient, messageZamenjava)
				messenger.send(messageRequest)

	else:
		sendMessage(recipient, "Oprosti, tega ukaza ne razumem. 😐")
		messageHelp = messages.Message(attachment=priponkaPomoc)
		messageRequest = messages.MessageRequest(recipient, messageHelp)
		messenger.send(messageRequest)

def messageReceived(data, recipient):
	if not 'message' in data or not 'text' in data['message']:
		return "ok"

	receivedMessage = data['message']['text']
	userData = findUserInDatabase(recipient.recipient_id)

	# Ce uporabnika se ni v bazi, mu posljemo uvodno sporocilo
	if not userData:
		userName = getUserName(recipient.recipient_id)
		sendMessage(recipient, "Živjo {}! 😄\nSem Branko, tvoj digitalni asistent, ki ti pomaga pri odjavi in prijavi na šolsko malico.".format(userName))
		typingIndicatorOn(recipient)
		time.sleep(0.8)
		sendMessage(recipient, "Preden ti lahko pomagam moraš imeti ustvarjen račun na šolski spletni strani za upravljanje z malico.")
		typingIndicatorOn(recipient)
		time.sleep(1)
		message = messages.Message(attachment=priponkaPrijava)
		req = messages.MessageRequest(recipient, message)
		messenger.send(req)
		return "ok"

	# Ce je uporabnik ze prijavljen ugotovimo kaj sploh zeli narediti
	parseUserMessage(receivedMessage, recipient)

def postbackReceived(data, recipient):
	receivedPostback = data['postback']['payload']
	parseUserMessage(receivedPostback, recipient)

def accountLinkingReceived(data, recipient):
	status = data['account_linking']['status']
	if status == 'linked':
		# Uporabnik se je ravnokar povezal
		authorizationCode = data['account_linking']['authorization_code']
		message = messages.Message(text='Super, prijavil si se kot {}'.format(authorizationCode))
		messageRequest = messages.MessageRequest(recipient, message)
		messenger.send(messageRequest)
		message = messages.Message(attachment=priponkaPomoc)
		messageRequest = messages.MessageRequest(recipient, message)
		messenger.send(messageRequest)
	elif status == 'unlinked':
		removeUserFromDatabase(recipient.recipient_id)
		message = messages.Message(text='Uspešno si izbrisal svoj račun.')
		messageRequest = messages.MessageRequest(recipient, message)
		messenger.send(messageRequest)

# Messengerjevo preverjanje streznika (vsakic ko streznik poslje kodo, mu jo vrnemo)
@app.route('/', methods=['GET'])
def handleVerification():
	return request.args['hub.challenge']

# Vsakic, ko nam uporabniki posljejo sporocilo se izvede ta metoda
# Tukaj najprej najdemo uporabnika in njegovo sporocilo in glede na
# poslane podatke ustrezno reagiramo.
@app.route('/', methods=['POST'])
def handle_incoming_messages():
	# Preberemo poslano sporocilo (to je v obliki json)
	data = request.json

	# Odvisno od tipa sporocila se Branko razlicno odzove
	messageData = data['entry'][0]['messaging'][0]

	# Najdemo id uporabnika in ustvarimo objekt Recipient
	senderId = messageData['sender']['id']
	recipient = messages.Recipient(recipient_id=senderId)

	if "message" in messageData:
		messageReceived(messageData, recipient)
	elif "postback" in messageData:
		postbackReceived(messageData, recipient)
	elif "account_linking" in messageData:
		accountLinkingReceived(messageData, recipient)

	return "ok"

# Prijava uporabnika na spletno stran
@app.route('/prijava', methods=['GET'])
def prijava():
	accountLinkingToken = request.args.get('account_linking_token')
	redirectUri = request.args.get('redirect_uri')
	return render_template('login.html', account_linking_token=accountLinkingToken, redirect_uri=redirectUri, sole=sole, authorization_url="{}{}".format(serverUrl, "/auth"))

#Avtorizacija uporabnika na stran
@app.route('/auth', methods=['POST'])
def avtorizacija():
	accountLinkingToken = request.form['account_linking_token']
	uporabniskoIme = request.form['uporabnisko_ime']
	geslo = request.form['geslo']
	sola = request.form['sola']

	# Najdemo uporabnikov messenger id
	uid = getUserId(accountLinkingToken)

	try:
		preizkusPrijave = malica.Malica(uporabniskoIme, geslo)
		insertUserIntoDatabase(uid, uporabniskoIme, geslo)
		preusmeritev = request.form['redirect_uri'] + "&authorization_code={}".format(uporabniskoIme)
		return redirect(preusmeritev)
	except Exception:
		preusmeritev = request.form['redirect_uri']
		return redirect(preusmeritev)

if __name__ == '__main__':
	app.run(debug=True)