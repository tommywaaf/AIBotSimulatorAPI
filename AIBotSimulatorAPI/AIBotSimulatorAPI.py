from flask import Flask, jsonify, send_file
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# Connect to the MongoDB database
client = MongoClient(host="161.35.137.38",
                     port=27017,
                     username="tommy",
                     password="tommytommy",
                     authSource="admin")
db = client['mydatabase']

@app.route('/getnextgame')
def get_next_game():
    # Find the first game with no winner
    game = db.games.find_one({"winner": {"$exists": False}}, sort=[("gameId", 1)])
    if game is None:
        return jsonify({"message": "No active games found."}), 404

    # Get the bots for the game
    team1 = db.bots.find_one({"botId": str(game["team1"])})
    team2 = db.bots.find_one({"botId": str(game["team2"])})

    # Return the bot details as JSON
    return jsonify({
        "team1": {
            "name": team1["name"],
            "battleCapability": team1["battleCapability"],
            "wins": team1["wins"],
            "losses": team1["losses"],
            "imageId": str(team1["imageId"])
        },
        "team2": {
            "name": team2["name"],
            "battleCapability": team2["battleCapability"],
            "wins": team2["wins"],
            "losses": team2["losses"],
            "imageId": str(team2["imageId"])
        }
    })


@app.route('/getteam1image')
def get_team1_image():
    # Find the first game with no winner
    game = db.games.find_one({"winner": {"$exists": False}}, sort=[("gameId", 1)])
    if game is None:
        return jsonify({"message": "No active games found."}), 404

    # Get the team1 bot and its image
    team1 = db.bots.find({"botId": str(game["team1"])})
    image_id = team1["imageId"]
    image = db.images.find({"_id": ObjectId(image_id)})

    # Return the image as a file
    return send_file(image["path"], mimetype=image["mimetype"])


@app.route('/getteam2image')
def get_team2_image():
    # Find the first game with no winner
    game = db.games.find_one({"winner": {"$exists": False}}, sort=[("gameId", 1)])
    if game is None:
        return jsonify({"message": "No active games found."}), 404

    # Get the team2 bot and its image
    team2 = db.bots.find({"botId": str(game["team2"])})
    image_id = team2["imageId"]
    image = db.images.find({"_id": ObjectId(image_id)})

    # Return the image as a file
    return send_file(image["path"], mimetype=image["mimetype"])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
