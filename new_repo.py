import json
import os
import sys

import subprocess
from termcolor import colored
from collections import defaultdict
import ast
import requests

def update_rating(user_name, games_played, games_tied, games_lost, rating):
    file_path = 'src/data/scoreboard_preview.json'
    
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []
    
    user_found = False
    for user in data:
        if user['github_user'] == user_name:
            user['games_played'] = games_played
            user['games_tied'] = games_tied
            user['games_lost'] = games_lost
            user['rating'] = rating
            user_found = True
            break
    
    if not user_found:
        data.append({
            'github_user': user_name,
            'games_played': games_played,
            'games_won': games_played - games_lost - games_tied,
            'games_tied': games_tied,
            'games_lost': games_lost,
            'rating': rating
        })
    
    data.sort(key=lambda x: x['rating'], reverse=True)
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def update_players_file(user_name, repo_url):
    ''' Actualiza el archivo players.json , añade al usuario y su repo,
      en caso de ya existir actualiza el repo'''

    FILE_PATH = "src/data/players.json"
    with open(FILE_PATH, 'r') as file:
        players = json.load(file)

    player_found = False
    for player in players:
        if player['github_user'] == user_name:
            player['repo'] = repo_url
            player_found = True
            break

    if not player_found:
        players.append({"github_user": user_name, "games_played": [], "repo": repo_url})

    with open(FILE_PATH, 'w') as file:
        json.dump(players, file, indent=4)
    print("Players.json updated")


def update_players_file_game_ID(user_name, game_ID):
    ''' Actualiza el archivo players.json , añade al usuario y su repo,
      en caso de ya existir actualiza el repo'''

    FILE_PATH = "src/data/players.json"
    with open(FILE_PATH, 'r') as file:
        players = json.load(file)

    for player in players:
        if player['github_user'] == user_name:
            player['games_played'].append(game_ID)
            break

    with open(FILE_PATH, 'w') as file:
        json.dump(players, file, indent=4)
    print("Players.json updated, game ID")


def get_new_game_id():
    game_ids = []
    for filename in os.listdir('games'):
        if filename.endswith(".json"):
            try:
                game_id = int(filename.split('.')[0])
                game_ids.append(game_id)
            except ValueError:
                continue
    max_id = max(game_ids, default=-1)
    return max_id + 1

def save_game_info(game_ID,user1,user2,user3,user4,result):
    new_game = {
        "game_id": game_ID,
        "players": [user1, user2, user3, user4],
        "result":  result
    }

    FILE_PATH = "src/data/games.json"
    with open(FILE_PATH, 'r') as file:
        games = json.load(file)

    games.append(new_game)

    with open(FILE_PATH, 'w') as file:
        json.dump(games, file, indent=4)
    print("games.json updated")
    
    

def start_new_player(container_id,port,image_name):
    ''' Corre el contenedor de docker en un puerto dado '''
    print(f"Corriendo el contenedor {container_id}...")
    run_player = f"docker run -d --rm -p 127.0.0.1:{port}:8000 --name {container_id} {image_name}"
    subprocess.run(run_player, shell=True)
    print(colored(f'Container ID: {container_id}', 'cyan'))
    print(colored(f'Puerto asignado: {port}', 'green'))


def parse_output(output_str):
    try:
        parsed_output = ast.literal_eval(output_str)
        if not isinstance(parsed_output, dict):
            print("La salida no es un diccionario")
            return None
        return parsed_output
    except (ValueError, SyntaxError):
        print("La salida no se pudo parsear")
        return None


def run_game(p1, p2, tipo, game_ID):
    '''Corre un juego entre los dos jugadores que estan en los puertos p1 y p2 contra dos jugadores tipo'''
    
    with open(f'games/{game_ID}.json', 'w') as f:
        json.dump({}, f)

    # check if th json was created
    if not os.path.exists(f'games/{game_ID}.json'):
        print("Error creating json file")
        return {}
    

    
    cmd = f"python src/domino/domino.py play -p0 Remote http://127.0.0.1:{p1} -p1 {tipo} -p2 Remote http://127.0.0.1:{p2} -p3 {tipo} -v --out games/{game_ID}.json"
  
    completed_process = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if completed_process.returncode != 0:
        print(f"Error running command: {completed_process.stderr}")
        return {}

    try:
        return parse_output(completed_process.stdout)
    except json.JSONDecodeError:
        print(f"Invalid output: {completed_process.stdout}")
        return {}
    

def get_repo_from_pull_request(pull_request_url):
    ''' Obtiene el link del repo a partir de un link de un PR '''
    
    api_url = pull_request_url.replace("https://github.com/", "https://api.github.com/repos/")
    api_url = api_url.replace("/pull/", "/pulls/")

    # Hacer la solicitud a la API de GitHub
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        # Obtener el URL del repositorio
        repo_url = data['head']['repo']['html_url']
        return repo_url
    else:
        return "Error: No se pudo obtener información del pull request."

    
def main():
    
    os.makedirs('games', exist_ok=True)

    if len(sys.argv) != 3:
        print("Use: new_repo.py <user> <url_pr>")
        sys.exit(1)

    user_name = sys.argv[1]
    repo_url =  get_repo_from_pull_request(sys.argv[2])
    p1=5000
    p2=5001
    docker_build1 = f"docker build -t {user_name.lower()+'_a'} {repo_url}.git"
    docker_build2 = f"docker build -t {user_name.lower()+'_b'} {repo_url}.git"
    build_out1 = subprocess.run(docker_build1, shell=True)
    build_out2 = subprocess.run(docker_build2, shell=True)

    
    if build_out1.returncode == 0 and build_out2.returncode == 0:
        update_players_file(user_name, repo_url)

        start_new_player(user_name.lower()+'_a',p1,user_name.lower()+'_a')
        start_new_player(user_name.lower()+'_b',p2,user_name.lower()+'_b')

        tipos=['Agachao', 'AlwaysDouble', 'DataDropper', 'DataKeeper', 'DoubleEnd',
                'LessPlayed', 'NonDouble', 'Passer',
                'Repeater', 'BigDrop', 'SmallDrop', 'Supportive',
                'TableCounter']

        games_played = len(tipos)
        games_won = 0
        games_lost = 0
        games_tied = 0

        for tipo in tipos:
            game_ID = get_new_game_id()
            print(f"Playing games between {user_name} and {tipo}")
            result = run_game(p1,p2,tipo,game_ID)
            save_game_info(game_ID,user_name,tipo,user_name,tipo,result)
            update_players_file_game_ID(user_name, game_ID)
            print(result)
            result=dict(result)
            games_won += result[-1]
            games_tied += result[0]
            games_lost += result[1]

            print(result) 

        rating = games_won*100 + games_tied*25 + games_lost*0

        update_rating(user_name, games_played, games_tied, games_lost, rating)

if __name__ == "__main__":
    main()
