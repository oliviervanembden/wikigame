import sqlite3
import flask
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
        self.owner = ownerID
        self.articals = {}
        self.players = [ownerID]
        self.gameCode = gameCode
        self.start = False

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
        if userID in self.players:
            temp = self.articals
            print(temp)
            temp.pop(userID)
            art = random.choice(list(temp.items()))
            print(art)
            return art
        else:
            return "game not joined"
    def check(self):
        print(len(self.articals))
        print(len(self.players))
        if len(self.articals) == len(self.players):
            return True
        else:
            return False


def generateCode():
    while True:
        code = ""
        for _ in range(8):
            code += random.choice(ascii_uppercase)

        if code not in games:
            break

    return code


@app.route('/', methods=["POST", "GET"])
def home():
    if request.method == "POST":
        code = request.form.get("code")
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


@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['gameCode']
    leave_room(room)
    socketio.emit("delUser", username, to=room)



@socketio.on('start')
def on_start(data):
    print("started")
    games[data['gameCode']].start = True
    socketio.emit("startGame",to=data['gameCode'])


@socketio.on('addArt')
def addArt(data):
    userID = data['userID']
    art = data["art"]
    gameCode= session.get("gameCode")
    games[gameCode].addArtical(art,userID)

    if games[gameCode].check():
        guessr = random.choice(games[gameCode].players)
        socketio.emit("startRound",{art:games[gameCode].getArtical(guessr),"guessr":getUserData(guessr)[0]}, to=gameCode)






if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)