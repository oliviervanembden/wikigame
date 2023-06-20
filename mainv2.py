import sqlite3
import json
import random
from flask import Flask, request, jsonify, render_template, make_response, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import copy
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
games = {}
correctGuesRew=40
def addPoints(id,points): # temp add real code later
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute(f"SELECT points FROM user WHERE ID='{id}'")
    userData = c.fetchone()
    totalPoints = int(userData)+int(points)


def getUserData(ID):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM user WHERE ID='{ID}'")
    userData = c.fetchone()
    return userData

def idToName(list):
    tempList = []
    for a in list:
        tempList.append(getUserData(a)[0])
    return tempList

class wikigame:

    def __init__(self, ownerID, gameCode):
        self.guesser = None
        self.owner = ownerID
        self.articals = {}
        self.players = [ownerID]
        self.gameCode = gameCode
        self.start = False
        self.correct = ""

    def joinGame(self, userID):
        self.players.append(userID)
        return self.players

    def leaveGame(self, userID):
        if userID in self.articals:
            del self.articals[userID]
        self.players.remove(userID)

    def addArtical(self, name, ownerid):


        self.articals[ownerid] = name

    def getArtical(self, userID):
        self.guesser = userID
        if userID in self.players:
            temp = copy.deepcopy(self.articals)
            temp.pop(int(userID))
            art = random.choice(list(temp.items()))
            self.correct = art[0]
            self.articals.pop(art[0])

            return art[1]
        else:
            return "game not joined"
    def check(self):
        print(self.articals)
        if len(self.articals) == len(self.players):
            return True
        else:
            return False
    def subGuess(self, guesse):
        print("subGuess")
        print(guesse)
        pun = correctGuesRew / (len(self.players)-2)
        print(pun)

        tot= copy.deepcopy(correctGuesRew)
        correct =self.correct
        print(correct)
        print(guesse)
        points = {}

        for b in self.players:
            points[b] = 0
        for a in guesse:
            if int(a) == correct:
                print("hallo")
                points[self.guesser] = tot
                addPoints(self.guesser, tot)
                points[a] = tot/2
                addPoints(a,tot)

            else:
                points[a] = tot
                addPoints(a,tot)

            tot -= pun
        retGuese= []
        retPoints = {}
        for a in points:
            retPoints[getUserData(a)[0]]= points[a]

        for a in guesse:
            retGuese.append(getUserData(a)[0])

        return {"order": retGuese,"correct":getUserData(self.correct)[0], "points":retPoints}






def generateCode():
    while True:
        code = ""
        for _ in range(2):
            code += random.choice(ascii_uppercase)

        if code not in games:
            break

    return code


@app.route('/', methods=["POST", "GET"])
def home():
    if request.method == "POST":
        code = request.form.get("code").capitalize()
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        if join != False:
            if code in games:
                session["gameCode"] = code
                ID = request.cookies.get('userID')
                if ID not in games[code].players:
                    games[code].players.append(ID)
                return redirect(url_for("lobby"))
            else:
                print("error code does noet exits")
                return redirect(url_for("home"))

        if create != False:

            return redirect(url_for("createGame"))


    else:
        ID = request.cookies.get('userID')
        if ID is None:
            return render_template('home.html')
        else:
            userData = getUserData(ID)
            session['name'] = userData[0]
            session['points'] = userData[2]
            session['userID'] = ID
            #print(session['userID'])
            return render_template('welcomeBack.html', name=userData[0], points=userData[2])


@app.route('/addUser', methods=['POST'])
def addUser():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    name = request.form.to_dict(flat=False)['name'][0]
    c.execute("SELECT MAX(ID) FROM user")
    ID = c.fetchone()
    ID = ID[0] + 1
    c.execute(f"INSERT INTO user VALUES ('{name}',{ID},0)")
    conn.commit()
    resp = make_response(render_template('accountcreated.html', name=name, ID=ID))
    resp.set_cookie('userID', str(ID))
    return resp


@app.route('/createGame')
def createGame():
    gameCode = generateCode()
    session['gameCode'] = gameCode

    games[gameCode] = wikigame(request.cookies.get('userID'), gameCode)
    return redirect(url_for('lobby'))

@app.route('/test')
def test():
    return render_template("test.html")

@app.route('/lobby')
def lobby():
    gameCode =session.get("gameCode")
    userID = session.get('userID')
    print(userID)
    print(games[gameCode].players)
    if gameCode in games and userID in games[gameCode].players:
        tempplayer= copy.deepcopy(games[gameCode].players)
        tempplayer.remove(userID)
        print(idToName(tempplayer))
        if games[gameCode].owner == userID:
            return render_template("lobby.html", owner=True, code=gameCode, players=idToName(tempplayer), userID=userID)
        else:
            return render_template("lobby.html", owner=False, code=gameCode, players=idToName(tempplayer), userID=userID)
    else:
        return redirect(url_for(""))

@app.route('/game')
def game():
    gameCode = session.get("gameCode")
    if games[gameCode].start:
        return render_template("game.html", userID=session.get('userID'))
    else:
        return redirect(url_for('lobby'))


@socketio.on('join')
def on_join(data):
    print("join")
    userID = data['userID']
    room = data['gameCode']
    join_room(room)
    socketio.emit("addUser",getUserData(userID)[0], to=room)


@socketio.on('leave') #
def on_leave(data):
    username = data['username']
    room = data['gameCode']
    leave_room(room)
    socketio.emit("delUser", username, to=room)

@socketio.on('nextRound')
def nextRound(data):

    socketio.emit("next",games[str(session['gameCode'])].correct)
    

@socketio.on('start')
def on_start(data):
    print("started")
    games[data['gameCode']].start = True
    print(data['gameCode'])
    socketio.emit("startGame",to=data['gameCode'])


@socketio.on('addArt')
def addArt(data):
    userID = data['userID']
    art = data["art"]
    gameCode = session.get("gameCode")
    games[gameCode].addArtical(art, userID)

    if games[gameCode].check():
        guesser = random.choice(games[gameCode].players)
        guessers = [
            {"id": player, "name": getUserData(player)[0]}
            for player in games[gameCode].players
            if player != guesser
        ]

        data = {
            "art": games[gameCode].getArtical(guesser),
            "guesserID" :guesser,
            "guesserName": getUserData(guesser)[0],
            "players": guessers
        }
        print("send")
        socketio.emit("startRound", data)

#VNYXQXQS
#VNYXQXQS
#submitGuess
@socketio.on('submitGuess')
def submitGuess(data):
    print(data)
    socketio.emit("subbedGuess", games[str(session['gameCode'])].subGuess(data))

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)