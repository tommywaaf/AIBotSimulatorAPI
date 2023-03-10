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
         # Check if there is a championship game with a winner
        championship_game = db.games.find_one({"playoffround": 3, "winner": {"$exists": True}})
        if championship_game is not None:
            winner = championship_game["winner"]
            return jsonify({"message": "Champion has been declared. The winner is " + winner + "."})
        
    # Get the bots for the game
    team1 = db.bots.find_one({"botId": str(game["team1"])})
    team2 = db.bots.find_one({"botId": str(game["team2"])})

    # Return the bot details as JSON
    return jsonify({
        "gameId": game["gameId"],
        "team1wins": game.get("team1wins"),
        "team2wins": game.get("team2wins"),
        "playoffround": game.get("playoffround"),
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
    response = openai.Completion.create(
    model="text-davinci-003",
    prompt = (f"Here are 3 battles determined in 2 to 6 steps.\nBattle1\nTeam1\n      Name: OctoFrog\n      BattleCapability: Agility, Camouflage, Invisibility, Stealth, Tentacle attacks, Adhesion, Electroreception, Adaptability, Intelligence, Lashing Tongue.\nTeam2\n      Name:Cheetahbot\n      BattleCapability: Speed, Agility, Acrobatics, Enhanced Vision, Stealth, Sensor Network, Precision, Endurance, Razor Claws, Fierce Bite.\nresults\n      resulttext:\n1. The Octofrog uses its agility and invisibility, but a misstep causes it to stumble and sustain damage.\n2. The Cheetahbot uses its enhanced vision and razor claws, landing solid hits on the Octofrog.\n3. The Octofrog retaliates with a lashing tongue attack, but the damage reduces its impact.\n4. The Cheetahbot goes for a fierce bite, causing significant damage to the Octofrog.\n5. The Octofrog tries to electrocute the Cheetahbot, but the attack is weakened by the damage sustained.\n6.  The Cheetahbot overpowers the weakened Octofrog, resulting in a victory.\n      winner: Cheetahbot.\nBatle2\nTeam1\n      Name: OctoFrog\n      BattleCapability: Agility, Camouflage, Invisibility, Stealth, Tentacle attacks, Adhesion, Electroreception, Adaptability, Intelligence, Lashing Tongue.\nTeam2\n      Name:Cheetahbot\n      BattleCapability: Speed, Agility, Acrobatics, Enhanced Vision, Stealth, Sensor Network, Precision, Endurance, Razor Claws, Fierce Bite.\nresults\n      resulttext:\n1. The Octofrog uses its camouflage and adhesion to stick to the walls, making it difficult for the Cheetahbot to find it.\n2. The Cheetahbot uses its sensor network to locate the Octofrog and launches a precision attack.\n3. The Octofrog retaliates with a lashing tongue attack, but the Cheetahbot dodges it.\n4. The Cheetahbot uses its razor claws to slash at the Octofrog, causing significant damage.\n5. The Octofrog uses its electroreception and intelligence to gain an advantage, but it is not enough to overpower the Cheetahbot.\n6. The Cheetahbot uses its speed and agility to outmaneuver the Octofrog, resulting in a victory.\n      winner: Cheetahbot.\nBattle3\nTeam1\n      Name:{team1['name']}\n      BattleCapability:{team1['battleCapability']}\nTeam2\n      Name:{team2['name']}\n      BattleCapability:{team2['battleCapability']}\nResults\n"),
    temperature=0.9,
    max_tokens=1421,
    top_p=1,
    frequency_penalty=0,

    )
    
    response_text = response["choices"][0]["text"]
    pattern = r'      resulttext:\n([\s\S]+)\n.*winner: (\w+)'
    match = re.search(pattern, response_text)
    if match:
        resulttext = match.group(1)
        winner_name = match.group(2)
    else:
        print({'error': 'Failed to extract resulttext and winner'})

    # Update the bots documents
    winner_name = winner_name.strip()
    winner_doc = db.bots.find_one({'name': winner_name})
    winner = winner_doc['botId']
    if team1['botId'] == winner_name:
        losing_bot = team2
    else:
        losing_bot = team1

    db.bots.update_one({'botId': winner_name}, {'$inc': {'wins': 1}})
    db.bots.update_one({'botId': losing_bot['botId']}, {'$inc': {'losses': 1}})

    if game.get("series", False):
        if winner_name == game["team1"]["botId"]:
            db.games.update_one({'gameId': game_id}, {'$inc': {'team1wins': 1}})
            if game.get("team1wins", 0) == 3:
                db.games.update_one({'gameId': game_id}, {'$set': {'winner': game["team1"], 'resulttext': resulttext}})
                if game.get("playoffround", 0) == 3:
                    db.bots.update_one({'botId': winner_name}, {'$inc': {'championships': 1}})
        elif winner_name == game["team2"]["botId"]:
            db.games.update_one({'gameId': game_id}, {'$inc': {'team2wins': 1}})
            if game.get("team2wins", 0) == 3:
                db.games.update_one({'gameId': game_id}, {'$set': {'winner': game["team2"], 'resulttext': resulttext}})
                if game.get("playoffround", 0) == 3:
                    db.bots.update_one({'botId': winner_name}, {'$inc': {'championships': 1}})
    else:
        db.games.update_one({'gameId': game_id}, {'$set': {'winner': winner, 'resulttext': resulttext}})

    return jsonify({'winner': winner, 'resulttext': resulttext})


    
def create_playoff_games(db):

    # Create the playoff matchups
    if db.games.count_documents({"playoffround": {"$exists": True}}) == 0:
        # Get the teams based on their final standings
        teams = list(db.bots.find().sort("wins", -1))
        matchups = [
            (teams[0], teams[7]),
            (teams[1], teams[6]),
            (teams[2], teams[5]),
            (teams[3], teams[4])
        ]
        for i, matchup in enumerate(matchups):
            team1, team2 = matchup
            for j in range(1):
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
                round_2_game = {
                    "gameId": db.games.count_documents({}) + 1,
                    "team1": team1,
                    "team2": team2,
                    "series": True,
                    "team1wins": 0,
                    "team2wins": 0,
                    "playoffround": 2
                }
                db.games.insert_one(round_2_game)
        #create championship
        playoff_round_2 = list(db.games.find({"playoffround": 2}))
        all_round_2_games_played = all(game.get("winner") is not None for game in playoff_round_2)
        if all_round_2_games_played and db.games.count_documents({"playoffround": 3}) == 0:
            championship_matchup = (playoff_round_2[0]["winner"], playoff_round_2[1]["winner"])
            team1, team2 = championship_matchup
            round_3_game = {
                "gameId": db.games.count_documents({}) + 1,
                "team1": team1,
                "team2": team2,
                "series": True,
                "team1wins": 0,
                "team2wins": 0,
                "playoffround": 3
            }
            db.games.insert_one(round_3_game)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
