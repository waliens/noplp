# -*- coding: utf-8 -*-

from catalog.catalog import Catalog
import os
import json
import uuid
from flask import Flask, request, Response, jsonify, send_from_directory
from random import choice

from lib.logger import get_logger

logger = get_logger(LOG_NAME='noplp')

app = Flask(__name__)
app.rounds = {}
app.challenges = {}
datapath = os.path.join("/home/ec2-user/noplp/backend/data")
# datapath = os.path.join(os.getcwd(), "data")
app.catalog = Catalog(os.path.join(datapath, "list.csv"))
app.rounds = {}
app.current_round_id = None

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT'
        headers = request.headers.get('Access-Control-Request-Headers')
        if headers:
            response.headers['Access-Control-Allow-Headers'] = headers
    return response
app.after_request(add_cors_headers)

def generate_small_id(n_char=4):
    charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
    return ''.join(choice(charset) for _ in range(n_char))

def get_already_selected_categories(app):
    categories = []
    for _, v in app.rounds.items():
        categories = categories + v["categories"]
    return categories

@app.route("/")
def home():
    return "Hello, World!"

@app.route("/test/categories")
def test_categories():
    index = app.catalog.category_index
    return jsonify({"cat": list(index.keys())})

@app.route("/test/unique/categories")
def test_categories_unique():
    index = app.catalog.category_index
    return jsonify({"cat": { k : len(v) for k, v in index.items() if len(v) == 1}})

@app.route("/round", methods=["PUT"])
def new_round():
    app.current_round_id = uuid.uuid1().hex

    seen_categories = get_already_selected_categories(app)

    categories = app.catalog.get_categories(5, seen_categories)
    app.rounds[app.current_round_id] = {
        "categories": categories
    }

    return jsonify({"round": {"id": app.current_round_id, "categories": categories}})

@app.route("/round/<roundid>", methods=["GET"])
def get_round(roundid):
    round = app.rounds[roundid]
    return jsonify({"round": {"id": roundid, "categories": round["categories"]}})

@app.route("/category/<category>/songs", methods=["GET"])
def songs_from_catagory(category):
    songs = app.catalog.get_songs_from_category(category)
    song_names = list(map(lambda s : {"title": s.title, "artist": s.get_artist()}, songs))
    return jsonify({"category": category, "songs": song_names})

@app.route("/song/artist/<artist>/title/<title>/level/<level>", methods=["GET"])
def song(artist, title, level):
    song = app.catalog.get_song(artist, title)
    if not song:
        return Response(
                response=json.dumps({"message": "Song not found"}),
                status=500,
                mimetype='application/json'
                )
    
    lyrics, missing_lyrics = song.generate_song(level)

    # Store the challenge
    challengeid = generate_small_id()
    app.challenges[challengeid] = {"title": song.title, "artist": song.get_artist(), "lyrics": lyrics, "missing_lyrics": missing_lyrics, "tab": song.tab}

    return jsonify({"id": challengeid, "title": song.title, "artist": song.get_artist(), "lyrics": lyrics, "missing_lyrics": missing_lyrics})

@app.route("/admin/reinit")
def reinit():
    app.rounds = {}
    app.challenges = {}
    app.rounds = {}
    app.current_round_id = None
    return jsonify({"status":"App reinitialized"})

@app.route("/admin/challenge/<challengeid>", methods=["GET"])
def get_challenge(challengeid):
    return jsonify(app.challenges[challengeid.upper()])


if __name__ == "__main__":
    # Load lyrics
    logger.info("Loading the lyrics")

    # datapath = os.path.join(os.getcwd(), "data")
    datapath = os.path.join("/home/ec2-user/noplp/backend/data")
    logger.info(datapath)
    app.catalog = Catalog(os.path.join(datapath, "list.csv"))
    app.rounds = {}
    app.current_round_id = None
    
    # logger.info(catalog.artists_index["Tété"][0].generate_song("50"))

    # Start server
    logger.info("Starting server")
    app.run(debug=True, host="0.0.0.0", port="3100")