import mysql.connector
from flask import Flask, jsonify
import sys
import json
import configparser
from collections import Counter
# Qualty of Life package for CORS with Flask ( when developing on same machine )
from flask_cors import CORS, cross_origin

# Reads Config to connect to DB ( since currently my DB is on AWS )
sql_config = configparser.ConfigParser()
sql_config.read('sql.properties')

# Connect to data base and create cursor

dbconfig = {
    "user": sql_config['DEFAULT']['user'],
    "password": sql_config['DEFAULT']['password'],
    "host": sql_config['DEFAULT']['host'],
    "database": sql_config['DEFAULT']['database']
}

cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
cnx.close()

# Create Flask app and apply cors
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# API for retrieving data about a specific player


@app.route('/player/<username>')
@cross_origin()
def getPlayerData(username):

    cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
    cursor = cnx.cursor(buffered=True, dictionary=True)

    data = queryPlayer(username, cursor)

    cursor.close()
    cnx.close()

    return data


def queryPlayer(username, cursor):

    sql = "SELECT * FROM profile WHERE username = '" + str(username) + "';"
    cursor.execute(sql)
    row = cursor.fetchone()

    sql = "SELECT id FROM deck WHERE profile_id = '" + row['uid'] + "';"
    cursor.execute(sql)
    deck_rows = cursor.fetchall()

    decks = []
    for deck_row in deck_rows:
        decks.append(queryDeck(deck_row['id'], cursor))

    sql = "SELECT id, starttime FROM `match` JOIN profile ON `match`.player1_uid = profile.uid OR `match`.player2_uid = profile.uid WHERE profile.uid = '" + \
        row['uid'] + "' ORDER BY starttime DESC LIMIT 10;"
    cursor.execute(sql)
    match_rows = cursor.fetchall()
    matches = []
    for match_row in match_rows:
        matches.append(queryMatch(match_row['id'], cursor))

    sql = "SELECT COUNT(*) FROM `match` JOIN profile ON `match`.player1_uid = profile.uid OR `match`.player2_uid = profile.uid WHERE profile.uid = '" + \
        row['uid'] + "';"
    cursor.execute(sql)
    count_all = cursor.fetchone()

    cursor.fetchall()

    sql = "SELECT COUNT(*) FROM `match` JOIN profile ON `match`.player1_uid = profile.uid  OR `match`.player2_uid = profile.uid WHERE profile.uid = '" + \
        row['uid'] + "' AND ((player1_uid = '" + row['uid'] + \
        "' AND winner = 0) OR (player2_uid = '" + \
        row['uid'] + "' AND winner = 1));"
    cursor.execute(sql)
    win_count = cursor.fetchone()

    return {
        "username": row['username'],
        "uid": row['uid'],
        "decks": decks,
        "matches": matches,
        "matchCount": count_all['COUNT(*)'],
        "matchWins": win_count['COUNT(*)']
    }


def queryPlayerUsername(uid, cursor):
    sql = "SELECT username FROM profile WHERE uid = '" + str(uid) + "';"
    cursor.execute(sql)
    row = cursor.fetchone()

    return row['username']

# API for retrieving data about a specific card


@app.route('/card/<identifier>')
@cross_origin()
def getCardData(identifier):

    cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
    cursor = cnx.cursor(buffered=True, dictionary=True)

    data = queryCard(identifier, cursor)

    cursor.close()
    cnx.close()

    return data


def queryCard(identifier, cursor):
    identifier = str(identifier)

    if identifier.isdigit():
        sql = "SELECT * FROM card WHERE id = " + identifier + ";"
    else:
        identifier = identifier.replace("_", " ")
        sql = "SELECT * FROM card WHERE name = '" + identifier + "';"

    cursor.execute(sql)
    row = cursor.fetchone()

    sql = "SELECT component_id FROM run_requirements WHERE card_id = " + \
        str(row['id']) + ";"
    cursor.execute(sql)
    run_components_rows = cursor.fetchall()

    run_requirements = []
    for run_component in run_components_rows:
        run_requirements.append(getComponentData(
            run_component['component_id'], cursor))

    return {
        "name": row['name'],
        "id": int(row['id']),
        "collection": int(row['collection_id']),
        "textureName": row['textureName'],
        "maxHealth": int(row['maxHealth']),
        "maxDefense": int(row['maxDefense']),
        "maxAttack": int(row['maxAttack']),
        "runRequirements": int(row['runRequirements']),
        "runComponents": run_requirements,
        "ability": getAbilityData(int(row['ability_id']), cursor)
    }


@app.route('/card')
@cross_origin()
def getCardStats():
    cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
    cursor = cnx.cursor(buffered=True, dictionary=True)

    sql = "SELECT id, COUNT(match_id) as matches, SUM(win) as wins FROM card_stats GROUP BY id ORDER BY id;;"
    cursor.execute(sql)
    amount = cursor.rowcount
    cards = cursor.fetchall()

    card_stats = [None] * amount

    for card_row in cards:
        card_stats[card_row['id']] = {
            "card": queryCard(card_row['id'], cursor),
            "matches": card_row['matches'],
            "wins": card_row['wins']
        }

    card_stats = sorted(card_stats, key=lambda d: 0 if d['matches'] <= 0 else d['wins'] / d['matches'], reverse=True) 

    cursor.close()
    cnx.close()

    return {"card_stats": card_stats}

# API for retrieving data about a specific deck


@app.route('/deck/<id>')
@cross_origin()
def getDeckData(id):

    cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
    cursor = cnx.cursor(buffered=True, dictionary=True)

    data = queryDeck(id, cursor)

    cursor.close()
    cnx.close()

    return data


def queryDeck(id, cursor):
    sql = "SELECT * FROM deck WHERE id = " + str(id) + ";"
    cursor.execute(sql)
    deck_row = cursor.fetchone()

    sql = "SELECT COUNT(*) as matches FROM deck_stats WHERE id = '" + \
        str(id) + "';"
    cursor.execute(sql)
    matches = cursor.fetchone()['matches']

    sql = "SELECT COUNT(*) as wins FROM deck_stats WHERE id = '" + \
        str(id) + "' AND win = 1;"
    cursor.execute(sql)
    wins = cursor.fetchone()['wins']

    sql = "SELECT * FROM deck_has_card WHERE deck_id = " + str(id) + ";"
    cursor.execute(sql)
    deck_card_rows = cursor.fetchall()

    cards = []

    for card_row in deck_card_rows:
        for x in range(0, card_row['amount']):
            cards.append(queryCard(card_row['card_id'], cursor))

    return {
        "name": deck_row['name'],
        "id": int(id),
        "cards": cards,
        "owner": queryPlayerUsername(deck_row['profile_id'], cursor),
        "matches" : matches,
        "wins" : wins
    }


@app.route('/decks')
@cross_origin()
def getDeckStats():
    cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
    cursor = cnx.cursor(buffered=True, dictionary=True)

    sql = "SELECT * FROM deck;"
    cursor.execute(sql)
    deck_rows = cursor.fetchall()

    decks = []

    for deck_row in deck_rows:
        sql = "SELECT COUNT(*) as matches FROM deck_stats WHERE id = '" + \
            str(deck_row['id']) + "';"
        cursor.execute(sql)
        matches = cursor.fetchone()['matches']

        sql = "SELECT COUNT(*) as wins FROM deck_stats WHERE id = '" + \
            str(deck_row['id']) + "' AND win = 1;"
        cursor.execute(sql)
        wins = cursor.fetchone()['wins']

        decks.append({
            "id": deck_row['id'],
            "name": deck_row['name'],
            "owner": queryPlayerUsername(deck_row['profile_id'], cursor),
            "matches": matches,
            "wins": wins
        })

    decks.sort(key=lambda s: (
        0 if s['matches'] <= 0 else s['wins'] / s['matches'], -s['matches']), reverse=True)

    cursor.close()
    cnx.close()

    return {"deck_stats": decks}

# API for retrieving macro data about the game


@app.route('/stats')
@cross_origin()
def getStats():
    return {"data": "You requested game stats."}

# API for retrieving data about a specific match between players


@app.route('/match/<id>')
@cross_origin()
def getMatchData(id):
    cnx = mysql.connector.connect(pool_name="api_pool", **dbconfig)
    cursor = cnx.cursor(buffered=True, dictionary=True)

    data = queryMatch(id, cursor)

    cursor.close()
    cnx.close()

    return data["data"]


def queryMatch(id, cursor):
    sql = "SELECT * FROM `match` WHERE id = " + str(id) + ";"
    cursor.execute(sql)
    row = cursor.fetchone()

    collected = []

    sql = "SELECT data FROM move WHERE match_id = '" + str(id) + "';"
    cursor.execute(sql)
    data = cursor.fetchone()

    return data

@app.route('/match')
@cross_origin()
def getMatchStats():

    return


def getAbilityData(id, cursor):
    sql = "SELECT * FROM ability WHERE id = '" + str(id) + "';"
    cursor.execute(sql)
    row = cursor.fetchone()

    return {"id": row['id'], "name": row['name'], "textureName": row['textureName'], "description": row['description']}


def getComponentData(id, cursor):
    sql = "SELECT * FROM components WHERE id = '" + str(id) + "';"
    cursor.execute(sql)
    row = cursor.fetchone()
    return {"id": row['id'], "name": row['name'], "textureName": row['textureName']}


# run app
app.run(host='0.0.0.0', port=8080)
