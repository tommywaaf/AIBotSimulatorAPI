from flask import Flask, jsonify, send_file
from pymongo import MongoClient
from bson import ObjectId
import io


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


@app.route('/getbotimage/<bot_id>')
def get_bot_image(bot_id):
    # Find the bot document by its ID
    bot = db.bots.find_one({'botId': bot_id})
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404
    
    # Find the image document by its ID
    image = db.images.find_one({'_id': ObjectId(bot['imageId'])})
    if not image:
        return jsonify({'error': 'Image not found'}), 404
    
    # Return the image data with the appropriate content type
    return send_file(io.BytesIO(image['data']), mimetype=image['contentType'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
