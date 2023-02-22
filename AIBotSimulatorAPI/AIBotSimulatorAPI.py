import json
from flask import Flask, jsonify, send_file, request
from pymongo import MongoClient
from bson import ObjectId, json_util
from config import OPENAI_API_KEY
import io
import os
import openai
import re
import datetime

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

@app.route('/playoff/create')
def create_playoff_games():
    # Get the top 2 bots sorted by wins
    top_2_bots = list(db.bots.find({}, {"_id": False, "botId": True, "wins": True}).sort([("wins", -1)]).limit(2))
    bot_ids = [bot["botId"] for bot in top_2_bots]

    # Create the championship game
    game = {
        'team1': str(bot_ids[0]),
        'team2': str(bot_ids[1]),
        'gameId': db.games.count_documents({}) + 1,
        'championship': 'yes',
        'createDate': datetime.datetime.utcnow(),
         'updateDate': datetime.datetime.utcnow()
    }
    db.games.insert_one(game)
    return jsonify({'message': 'Championship game created successfully'}), 200






@app.route('/schedule/next')
def get_next_game():
    # Check if all games have a winner
    games_count = db.games.count_documents({})
    all_games_have_winner = db.games.count_documents({"winner": {"$exists": False}}) == 0
    if all_games_have_winner:
        # Create the next set of playoff games
        create_playoff_games(db)
    
    # Find the first game with no winner
    game = db.games.find_one({"winner": {"$exists": False}}, sort=[("gameId", 1)])
    if game is None:
        # Check if there are any games at all
        if games_count == 0:
            return jsonify({"message": "No games found."}), 404
        
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




@app.route('/bots/<bot_id>/image')
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


@app.route('/bots/<bot_id>')
def get_bot_data(bot_id):
    # Find the bot document by its ID
    bot = db.bots.find_one({'botId': bot_id})
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404

    # Convert the ObjectId to a string before returning the game data as JSON
    return json_util.dumps(bot)

@app.route('/schedule/<game_id>/game')
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

  
@app.route('/schedule/<int:number_to_fetch>')
def get_games(number_to_fetch):
    # Find all games with no winner
    games = db.games.find({"winner": {"$exists": False}})

    # Convert the cursor to a list
    games = list(games)

    # Sort the games by game ID
    games = sorted(games, key=lambda x: x["gameId"])


    # Limit the results to the specified number of games
    games = games[:number_to_fetch]

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


@app.route('/bots/leaderboard')
def get_leaderboard():
    # Find the top 15 bots with the most wins
    bots = db.bots.find({}, {"_id": False, "botId": True, "wins": True, "losses": True}).sort([("wins", -1)]).limit(15)

    # Create a list of bot data dictionaries with just the required fields
    leaderboard = [{"botId": bot["botId"], "wins": bot["wins"], "losses": bot["losses"]} for bot in bots]

    # Return the leaderboard as JSON
    return jsonify(leaderboard)


@app.route('/bots/<bot_id>/games')
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

@app.route('/battles/<int:game_id>', methods=['POST'])
def post_generate_battle(game_id):
    # Get the gameId from the request
    game_id = request.json.get('gameId')

    # Look up the game document by its ID
    game = db.games.find_one({'gameId': game_id})
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    if 'winner' in game:
        return jsonify({'error': 'Game already played'}), 400
    team1 = db.bots.find_one({"botId": str(game["team1"])})
    team2 = db.bots.find_one({"botId": str(game["team2"])})

    # Construct the prompt for the OpenAI API request
    prompt_text = "A set of 4 bot battles:Battle1 SniperBot[35] - A robot with a highly accurate targeting system that can strike from a distance.Tempest [7]- Tempest is a powerful battle robot with a lightweight yet durable alloy body that can withstand a lot of damage. Its head is equipped with a special heat-seeking visor, allowing it to detect and track enemies. Its arms are equipped with powerful electrical shockers that can deliver powerful shocks to its enemies. Its legs are fitted with powerful jets for flight, allowing it to soar through the air and deliver powerful attacks from above. Its main weapons are its electrical shockers and its jets for flight. It can use its electrical shockers to shock its enemies and its jets to launch itself forward and deliver powerful attacks.{\"resulttext\": \"\n1. SniperBot takes aim and fires a precise shot, but Tempest quickly creates a sheet of ice that deflects the attack. \n2. Tempest unleashes a flurry of ice shards that hit SniperBot and damage its targeting system. \n3. SniperBot tries to recalibrate its targeting, but Tempest's freezing ray hits it, immobilizing it in place. \n4. Tempest moves in for the finishing blow, crushing SniperBot with its powerful forelegs. Tempest wins.\",\"winner\": 7}Battle 2 Odin-X[6] - Odin-X is a powerful battle robot with a special adamantium alloy body that can withstand a lot of damage. Its head is equipped with a multi-function visor, allowing it to detect and track enemies. Its arms are equipped with a powerful energy cannon and energy shield, allowing it to both attack and defend against enemies. All of its limbs are augmented by powerful servo-motors, giving it superior speed, strength and agility in combat. Its main weapons are its energy cannon and energy shield. It can use its energy cannon to shoot powerful blasts at its enemies and its energy shield to block and deflect attacks. Its servo-motors give it powerful durability and the speed it needs to attack and defend quickly.Shining Guardian[5] - Shining Guardian is a powerful battle robot with a shining silver alloy body that can withstand a lot of damage. Its head is equipped with a gold visor, allowing it to detect and track enemies. Its arms and legs are equipped with powerful energy cannons that can fire powerful blasts of energy. Its lower body is equipped with powerful jets for flight, allowing it to soar through the air and deliver powerful attacks from above. Its main weapons are its energy cannons and its jets for flight. It can use its energy cannons to blast its enemies and its jets to launch itself forward and deliver powerful attacks.{\"resulttext\": \"\n1. Shining Guardian fires off a blast of energy, but Odin-X is able to block the attack with its energy shield. \n2. Odin-X launches itself forward and delivers a powerful punch, but Shining Guardian spins and dodges the attack. \n3. Odin-X charges forward and slams Shining Guardian with its energy cannon, dealing massive damage and causing its systems to shut down. Odin-X wins.\",    \"winner\": 6} Battle 3 Rotorstorm[8] -  Rotorstorm is a powerful battle robot with a light but durable alloy body that can withstand a lot of damage. Its head is equipped with a special radar system, allowing it to detect and track enemies. Its arms are equipped with powerful rotary blades that can slice through enemies with ease. Its lower body is equipped with powerful jet engines for flight, allowing it to soar through the air and deliver powerful attacks from above. Its main weapons are its rotary blades and its jet engines for flight. It can use its rotary blades to cut down its enemies and its jet engines to launch itself forward and deliver powerful attacks.MechaBiozilla[32] - MechaBiozilla is a powerful battle robot with an armored bio-steel body that can withstand a lot of damage. Its head is equipped with a motion-tracking visor, allowing it to detect and track enemies. Its arms are equipped with powerful claws that can tear through enemies with ease. Its lower body is equipped with powerful hydraulics, allowing it to jump and land hard enough to cause massive damage. Its main weapons are its claws and its hydraulics. It can use its claws to rip apart its enemies and its hydraulics to launch itself forward and deliver powerful attacks.{\"resulttext\": \"\n1. Rotorstorm takes to the skies and launches a powerful burst of wind towards MechaBiozilla, but the robot activates its hydro-boosters and jumps out of the way. \n2. MechaBiozilla charges forward and swipes at Rotorstorm with its powerful claws, but its rotary blades manage to block the attack. \n3. Rotorstorm dives towards the ground and launches an air blast directly at MechaBiozilla, sending it spinning out of control. \n4. Rotorstorm evades a savage swipe from MechaBioZilla. \n5. Rotorstorm slices through its opponent with its rotary blades, delivering the finishing blow and claiming victory. Rotorstorm wins.\",\"winner\": 8} Battle 4"
    prompt = f"{prompt_text}{team1['name']}[{team1['botId']}] {team2['name']}[{team2['botId']}] "
    response = openai.Completion.create(
    model="text-davinci-003",
    prompt=prompt,
    temperature=0.9,
    max_tokens=1421,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )
    
    response_text = response["choices"][0]["text"]
    match = re.search(r'"resulttext": "([^"]+)",.*"winner": (\d+)', response_text)
    if match:
        resulttext = match.group(1)
        winner = str(match.group(2))
    else:
     return jsonify({'error': 'Failed to extract resulttext and winner'}), 500

   # Update the bots documents
    winning_bot = db.bots.find_one({'botId': winner})
    losing_bot = None
    if team1['botId'] == winner:
        losing_bot = team2
    else:
        losing_bot = team1

    db.bots.update_one({'botId': winner}, {'$inc': {'wins': 1}})
    db.bots.update_one({'botId': losing_bot['botId']}, {'$inc': {'losses': 1}})

    # Update the games document
    if game.get("series", False):
        if winner == game["team1"]:
            db.games.update_one({'gameId': game_id}, {'$inc': {'team1wins': 1}})
            if game.get("team1wins", 0) == 4:
                db.games.update_one({'gameId': game_id}, {'$set': {'winner': game["team1"], 'resulttext': resulttext}})
                return jsonify({'winner': game["team1"], 'resulttext': resulttext})
        elif winner == game["team2"]:
            db.games.update_one({'gameId': game_id}, {'$inc': {'team2wins': 1}})
            if game.get("team2wins", 0) == 4:
                db.games.update_one({'gameId': game_id}, {'$set': {'winner': game["team2"], 'resulttext': resulttext}})
                return jsonify({'winner': game["team2"], 'resulttext': resulttext})

    else:
        db.games.update_one({'gameId': game_id}, {'$set': {'winner': winner, 'resulttext': resulttext}})
        return jsonify({'winner': winner, 'resulttext': resulttext})

def create_playoff_games(db):

    # Get the teams based on their final standings
    teams = list(db.bots.find().sort("wins", -1))
    
    # Create the playoff matchups
    matchups = [
        (teams[0], teams[7]),
        (teams[1], teams[6]),
        (teams[2], teams[5]),
        (teams[3], teams[4])
    ]
    
    # Create the games for each matchup
    if db.games.count_documents({"playoffround": {"$exists": True}}) == 0:
        for i, matchup in enumerate(matchups):
            team1, team2 = matchup
            for j in range(7):

                game = {
                    "gameId": db.games.count_documents({}) + 1,
                    "team1": team1["botId"],
                    "team2": team2["botId"],
                    "series": True,
                    "team1wins": 0,
                    "team2wins": 0,
                    "playoffround": 1
                }
            db.games.insert_one(game)

    
    # Check if all games with playoffround = 1 have a winner
    playoff_round_1 = list(db.games.find({"playoffround": 1}))
    all_round_1_games_played = all(game.get("winner") is not None for game in playoff_round_1)
    if all_round_1_games_played:
        # Check if there are any games with playoffround = 2
        playoff_round_2_exists = db.games.count_documents({"playoffround": 2}) > 0
        if not playoff_round_2_exists:
            # Create the next set of games with the winners of playoffround = 1
            matchups = [(playoff_round_1[0]["winner"], playoff_round_1[1]["winner"]), (playoff_round_1[2]["winner"], playoff_round_1[3]["winner"])]
            for i, matchup in enumerate(matchups):
                team1, team2 = matchup
                game = {
                    "gameId": db.games.count_documents({}) + 1,
                    "team1": team1,
                    "team2": team2,
                    "series": True,
                    "team1wins": 0,
                    "team2wins": 0,
                    "playoffround": 2
                }
            db.games.insert_one(game)

            
        # Check if all games with playoffround = 2 have a winner
        playoff_round_2 = list(db.games.find({"playoffround": 2}))
        all_round_2_games_played = all(game.get("winner") is not None for game in playoff_round_2)
        if all_round_2_games_played:
            # Create the championship game with the winners of playoffround = 2
            championship_matchup = (playoff_round_2[0]["winner"], playoff_round_2[1]["winner"])
            team1, team2 = championship_matchup
            game = {
                "gameId": db.games.count_documents({}) + 1,
                "team1": team1,
                "team2": team2,
                "series": True,
                "team1wins": 0,
                "team2wins": 0,
                "playoffround": 3
            }
        db.games.insert_one(game)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
