from flask import Flask, jsonify, send_file
from pymongo import MongoClient
from bson import ObjectId
from io import BytesIO

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
        "gameId": game["gameId"],
        "team1": {
            "name": team1["name"],
            "battleCapability": team1["battleCapability"],
            "wins": team1["wins"],
            "losses": team1["losses"],
            "botId": team1["botId"],
            "imageId": str(team1["imageId"])
        },
        "team2": {
            "name": team2["name"],
            "battleCapability": team2["battleCapability"],
            "wins": team2["wins"],
            "losses": team2["losses"],
            "botId": team2["botId"],
            "imageId": str(team2["imageId"])
        }
    })
@app.route('/getbotimage/<string:bot_id>')
def get_bot_image(bot_id):
    # Find the bot by bot_id
    bot = db.bots.find_one({"botId": bot_id})
    if bot is None:
        return {"message": "Bot not found."}, 404

    # Find the image by image_id
    image_id = bot["imageId"]
    image = db.images.find_one({"_id": ObjectId(image_id)})
    if image is None:
        return {"message": "Image not found."}, 404

    # Create a file-like object from the image binary data
    image_data = BytesIO(image["data"])

    # Return the image as a file
    return send_file(image_data, mimetype=image["mimetype"])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)