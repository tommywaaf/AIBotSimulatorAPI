import json
from flask import Flask, jsonify, send_file, request
from pymongo import MongoClient
from bson import ObjectId, json_util
from config import OPENAI_API_KEY
import io
import os
import openai


app = Flask(__name__)
openai.api_key = OPENAI_API_KEY

# Get the username and password from environment variables
username = os.environ.get("MONGODB_USERNAME")
password = os.environ.get("MONGODB_PASSWORD")
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

    # Convert the ObjectId to a string before returning the game data as JSON
    return json_util.dumps(bot)

@app.route('/getgamedata/<game_id>')
def get_game_data(game_id):
    # Convert the game_id to an integer
    try:
        game_id = int(game_id)
    except ValueError:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    # Find the game document by its ID
    game = db.games.find_one({'gameId': game_id})
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    # Convert the ObjectId to a string before returning the game data as JSON
    return json_util.dumps(game)
  
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
    prompt_text = "A set of 4 bot battles:\nBattle1\nSniperBot[35] - A robot with a highly accurate targeting system that can strike from a distance.\nTempest [7]- Tempest is a powerful battle robot with a lightweight yet durable alloy body that can withstand a lot of damage. Its head is equipped with a special heat-seeking visor, allowing it to detect and track enemies. Its arms are equipped with powerful electrical shockers that can deliver powerful shocks to its enemies. Its legs are fitted with powerful jets for flight, allowing it to soar through the air and deliver powerful attacks from above. Its main weapons are its electrical shockers and its jets for flight. It can use its electrical shockers to shock its enemies and its jets to launch itself forward and deliver powerful attacks.\n{\n\"resulttext\": \"1. SniperBot takes aim and fires a precise shot, but Tempest quickly creates a sheet of ice that deflects the attack. 2. Tempest unleashes a flurry of ice shards that hit SniperBot and damage its targeting system. 3. SniperBot tries to recalibrate its targeting, but Tempest's freezing ray hits it, immobilizing it in place. 4. Tempest moves in for the finishing blow, crushing SniperBot with its powerful forelegs. Tempest wins.\",\n\"winner\": 7\n}\n\nBattle 2\nOdin-X[6] - Odin-X is a powerful battle robot with a special adamantium alloy body that can withstand a lot of damage. Its head is equipped with a multi-function visor, allowing it to detect and track enemies. Its arms are equipped with a powerful energy cannon and energy shield, allowing it to both attack and defend against enemies. All of its limbs are augmented by powerful servo-motors, giving it superior speed, strength and agility in combat. Its main weapons are its energy cannon and energy shield. It can use its energy cannon to shoot powerful blasts at its enemies and its energy shield to block and deflect attacks. Its servo-motors give it powerful durability and the speed it needs to attack and defend quickly.\nShining Guardian[5] - Shining Guardian is a powerful battle robot with a shining silver alloy body that can withstand a lot of damage. Its head is equipped with a gold visor, allowing it to detect and track enemies. Its arms and legs are equipped with powerful energy cannons that can fire powerful blasts of energy. Its lower body is equipped with powerful jets for flight, allowing it to soar through the air and deliver powerful attacks from above. Its main weapons are its energy cannons and its jets for flight. It can use its energy cannons to blast its enemies and its jets to launch itself forward and deliver powerful attacks.\n{\n    \"resulttext\": \"1. Shining Guardian fires off a blast of energy, but Odin-X is able to block the attack with its energy shield. 2. Odin-X launches itself forward and delivers a powerful punch, but Shining Guardian spins and dodges the attack. 3. Odin-X charges forward and slams Shining Guardian with its energy cannon, dealing massive damage and causing its systems to shut down. Odin-X wins.\",\n    \"winner\": 6\n}\n\nBattle 3\nRotorstorm[8] -  Rotorstorm is a powerful battle robot with a light but durable alloy body that can withstand a lot of damage. Its head is equipped with a special radar system, allowing it to detect and track enemies. Its arms are equipped with powerful rotary blades that can slice through enemies with ease. Its lower body is equipped with powerful jet engines for flight, allowing it to soar through the air and deliver powerful attacks from above. Its main weapons are its rotary blades and its jet engines for flight. It can use its rotary blades to cut down its enemies and its jet engines to launch itself forward and deliver powerful attacks.\nMechaBiozilla[32] - MechaBiozilla is a powerful battle robot with an armored bio-steel body that can withstand a lot of damage. Its head is equipped with a motion-tracking visor, allowing it to detect and track enemies. Its arms are equipped with powerful claws that can tear through enemies with ease. Its lower body is equipped with powerful hydraulics, allowing it to jump and land hard enough to cause massive damage. Its main weapons are its claws and its hydraulics. It can use its claws to rip apart its enemies and its hydraulics to launch itself forward and deliver powerful attacks.\n{\n\"resulttext\": \"1. Rotorstorm takes to the skies and launches a powerful burst of wind towards MechaBiozilla, but the robot activates its hydro-boosters and jumps out of the way. 2. MechaBiozilla charges forward and swipes at Rotorstorm with its powerful claws, but its rotary blades manage to block the attack. 3. Rotorstorm dives towards the ground and launches an air blast directly at MechaBiozilla, sending it spinning out of control. 4. Rotorstorm evades a savage swipe from MechaBioZilla. 5. Rotorstorm slices through its opponent with its rotary blades, delivering the finishing blow and claiming victory. Rotorstorm wins.\",\n\"winner\": 8\n}\n\nBattle 4\n"

    prompt = f"{prompt_text}{team1['name']}[{team1['botId']}] - battleCapability {team2['name']}[{team2['botId']}] - battleCapability"
    response = openai.Completion.create(
    model="text-davinci-003",
    prompt=prompt,
    temperature=0.9,
    max_tokens=1421,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
)

    new_response = json.loads(response["choices"][0]["text"].replace('\n', ''))
    response = json.dumps(new_response)
    return response
    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
