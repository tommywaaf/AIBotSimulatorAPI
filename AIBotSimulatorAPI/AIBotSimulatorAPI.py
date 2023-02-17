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

@app.route('/getbotdata/<bot_id>')
def get_bot_data(bot_id):
    # Find the bot document by its ID
    bot = db.bots.find_one({'botId': bot_id})
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404
    
    # Return the bot document as JSON
    return jsonify(bot)

@app.route('/getgamedata/<game_id>')
def get_game_data(game_id):
    # Find the game document by its ID
    game = db.games.find_one({'gameId': game_id})
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    # Return the game data as JSON
    return jsonify(game)
  
@app.route('/getnext20games')
def get_next_20_games():
    # Find the next 20 games with no winner, sorted by game ID
    games = db.games.find({"winner": {"$exists": False}}, sort=[("gameId", 1)], limit=20)

    # Create a list of game details
    game_list = []
    for game in games:
        team1 = db.bots.find_one({"botId": str(game["team1"])})
        team2 = db.bots.find_one({"botId": str(game["team2"])})

        game_details = {
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
        }
        game_list.append(game_details)

    # Return the list of game details as JSON
    return jsonify(game_list)

@app.route('/getleaderboard')
def get_leaderboard():
    # Find the top 15 bots with the most wins
    bots = db.bots.find({}, {"_id": False, "botId": True, "wins": True, "losses": True}).sort([("wins", -1)]).limit(15)

    # Create a list of bot data dictionaries with just the required fields
    leaderboard = [{"botId": bot["botId"], "wins": bot["wins"], "losses": bot["losses"]} for bot in bots]

    # Return the leaderboard as JSON
    return jsonify(leaderboard)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
