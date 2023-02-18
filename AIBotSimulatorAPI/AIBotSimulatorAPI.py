from flask import Flask, jsonify, send_file, request
from pymongo import MongoClient
from bson import ObjectId
import io
import os
import openai


app = Flask(__name__)

# Get the username and password from environment variables
username = os.environ.get("MONGODB_USERNAME")
password = os.environ.get("MONGODB_PASSWORD")
# Set the OpenAI API key
openai.api_key = "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"
# Connect to the MongoDB database
client = MongoClient(
    "localhost",
    27017,
    username=username,
    password=password,
    authSource="admin"
)
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

@app.route('/getallbotgames/<bot_id>')
def get_all_bot_games(bot_id):
    # Find all games where the specified bot is a player
    games = db.games.find({"$or": [{"team1": bot_id}, {"team2": bot_id}]}, sort=[("gameId", 1)])

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

@app.route('/postgeneratebattle', methods=['POST'])
def post_generate_battle():
    # Get the gameId from the request
    game_id = request.json.get('gameId')

    # Look up the bots for the game
    game = db.games.find_one({'gameId': game_id})
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    team1 = db.bots.find_one({"botId": str(game["team1"])})
    team2 = db.bots.find_one({"botId": str(game["team2"])})

    # Construct the prompt for the OpenAI API request
    prompt = f"dummy text dummy text team1[{team1['battleCapability']}] team2[{team2['battleCapability']}] dummy text"

    # Send the API request to OpenAI
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.9,
        max_tokens=1421,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    # Return the response as JSON
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
