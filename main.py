import sqlite3
import flask
import json
import random
from flask import Flask, request, jsonify, render_template, make_response, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

gameIDS= []
def generateCode():
    while True:
        code = ""
        for _ in range(8):
            code += random.choice(ascii_uppercase)

        if code not in gameIDS:
            break

    return code
def getUserData(ID):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM user WHERE ID='{ID}'")
    userData = c.fetchone()
    return userData

class wikigame:
    def __init__(self,ownerID):
        self.ownerID = ownerID
        self.articals = {}
        self.players = [ownerID]
    def joinGame(self,userID):
        self.players.append(userID)
        return self.players
    def leaveGame(self,userID):
        if userID in self.articals:
            del self.articals[userID]
        self.players.remove(userID)
    def addartical(self,name,ownerid):
        if ownerid in self.players:
            self.articals[ownerid] = name
            return True
        else:
            return False
    def getArtical(self,userID):
        if userID in self.players:

            temp = self.articals
            del temp[userID]
            art = random.choice(list(temp.items()))
            print(art)
            return art
        else:
            return "game not joined"

games = {
    88: wikigame(4)
}


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@app.route('/', methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        if join != False:
            session["gameID"]= code

        if create!= False:
            return redirect(url_for("createGame"))


    else:
        ID = request.cookies.get('userID')
        if ID is None:
            return render_template('home.html')
        else:
            userData = getUserData(ID)
            print(userData)
            return render_template('welcomeBack.html', name=userData[0],points=userData[2])

@app.route('/game')
def game():
    return  render_template("game.html")
@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)

@app.route('/createGame', methods=['get'])
def createGame():
    ownerID = request.cookies.get('userID')
    gameID = generateCode()
    games[gameID]= wikigame(ownerID)
    return render_template('lobbyOwner.html')


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
    resp = make_response(render_template('accountcreated.html',name=name,ID=ID))
    resp.set_cookie('userID', str(ID))
    return resp

@app.route('/user', methods=['get'])
def user():
    ID = request.args.get('ID')
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM user WHERE ID='{ID}'")
    userData = c.fetchone()
    print(userData)
    return jsonify({'name':userData[0], 'ID':userData[1], 'points':userData[2]})


@app.route('/addArtical', methods=['post'])
def addArtical():
    print(games)
    gameID = request.args.get('gameID')
    articalName = request.args.get('articalName')
    userID = request.args.get('userID')
    games[int(gameID)].addartical(articalName,userID)
    return jsonify({"gameID": gameID, "articalName": articalName})
@app.route('/getArtical', methods=['get'])
def getArtical():
    gameID = request.args.get('gameID')
    userID = request.args.get('userID')
    return jsonify(games[int(gameID)].getArtical(userID)[1])

@app.route('/createGameApi', methods=['post'])
def createGameApi():
    ownerID = request.args.get('ownerID')
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("SELECT MAX(gameID) FROM games")
    gameID = c.fetchone()
    gameID = gameID[0] + 1
    c.execute(f"INSERT INTO games VALUES ('{gameID}',{ownerID},1)")
    conn.commit()
    games[gameID]= wikigame(ownerID)
    return jsonify({"userID":ownerID,"gameID":gameID})
@app.route('/addUserAPi', methods=['POST'])
def addUserApi():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    name = request.args.get('name')
    c.execute("SELECT MAX(ID) FROM user")
    ID = c.fetchone()
    ID = ID[0] + 1
    c.execute(f"INSERT INTO user VALUES ('{name}',{ID},0)")
    conn.commit()
    return jsonify({'name': name, "ID":ID,"points":0})

app.run(debug=True)