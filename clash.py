from flask import Flask, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime
import re
from collections import defaultdict
from datetime import datetime
from pymongo import MongoClient
import json



# Configuração do MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["clash_royale"]
players_collection = db["players"]
battles_collection = db["battles"]

# Configuração da API Flask
app = Flask(__name__)
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjljMjM5ZDNhLTA2NWYtNDQyOC04ZTBkLWVlOGMwNzMxYzAyNyIsImlhdCI6MTc0MzUzMjYzOCwic3ViIjoiZGV2ZWxvcGVyLzhmNzA4NDY0LWIxMmYtMDdiMy0zN2FlLTU0NWY4MTM2YmEyMSIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxNzcuMjIxLjM1LjY1Il0sInR5cGUiOiJjbGllbnQifV19.bpkUqyh8uguZrTFYpEkYHt0Wq7jUO3FF8Jjn7dkI--aj1nWZg_ole8u7TCoLWtnWmND-worFzG7hWQClq0tTww"  # Substitua pelo seu token real
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Função para buscar e armazenar dados de um jogador
def fetch_player_data(tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        player_data = response.json()
        # Salva ou atualiza os dados do jogador
        players_collection.update_one({"tag": player_data["tag"]}, {"$set": player_data}, upsert=True)
        return player_data
    return None

# Função para buscar e armazenar batalhas de um jogador
def fetch_battle_log(tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}/battlelog"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        battles = response.json()
        for battle in battles:
            # Salva ou atualiza as batalhas
            battles_collection.update_one({"battleTime": battle["battleTime"]}, {"$set": battle}, upsert=True)
        return battles
    return None

# Função para validar se uma data está no formato correto
def validate_date(date_str):
    """Valida e converte uma string de data no formato ISO para um objeto datetime."""
    try:
        if isinstance(date_str, datetime):  # Evita conversões duplicadas
            return date_str
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


# Consulta 1: Porcentagem de vitórias com uma carta específica
def calculate_win_rate(card_name, start_time, end_time):

    start_time = validate_date(start_time)
    end_time = validate_date(end_time)

    if not start_time or not end_time:
        return {"error": "Formato de data inválido. Use 'YYYY-MM-DDTHH:MM:SS'"}

    # Contar todas as batalhas onde a carta apareceu
    total_battles = battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "$or": [
            {"team.cards.name": card_name},
            {"opponent.cards.name": card_name}
        ]
    })

    # Contar vitórias quando a carta está no time vencedor
    wins_as_team = battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "team.cards.name": card_name,
        "$expr": {"$gt": [{"$arrayElemAt": ["$team.crowns", 0]}, {"$arrayElemAt": ["$opponent.crowns", 0]}]}
    })

    # Contar vitórias quando a carta está no oponente vencedor
    wins_as_opponent = battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "opponent.cards.name": card_name,
        "$expr": {"$gt": [{"$arrayElemAt": ["$opponent.crowns", 0]}, {"$arrayElemAt": ["$team.crowns", 0]}]}
    })

    # Total de vitórias da carta
    total_wins = wins_as_team + wins_as_opponent

    # Calcular a taxa de vitória
    win_rate = (total_wins / total_battles * 100) if total_battles > 0 else 0

    return {
        "card_name": card_name,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_battles": total_battles,
        "total_wins": total_wins,
        "win_rate": win_rate
    }

# Consulta 2: Decks completos com taxa de vitória superior a X%
def get_successful_decks(win_threshold, start_time, end_time):
    start_time = validate_date(start_time)
    end_time = validate_date(end_time)

    if not start_time or not end_time:
        return {"error": "Invalid date format. Use 'YYYY-MM-DDTHH:MM:SS'"}

    pipeline = [
        # Filtro para o intervalo de tempo
        {"$match": {"battleTime": {"$gte": start_time, "$lte": end_time}}},

        # Desenrolar o deck da equipe para contar vitórias por cada deck
        {"$unwind": "$team.deck"},

        # Determinar se o time venceu com base na quantidade de crowns
        {"$group": {
            "_id": "$team.deck",
            "total_battles": {"$sum": 1},
            "wins": {
                "$sum": {
                    "$cond": [{"$gt": ["$team.crowns", "$opponent.crowns"]}, 1, 0]
                }
            }
        }},

        # Calcular a taxa de vitória
        {"$addFields": {
            "win_rate": {"$multiply": [{"$divide": ["$wins", "$total_battles"]}, 100]}
        }},

        # Filtrar decks com taxa de vitória acima do limite definido
        {"$match": {
            "win_rate": {"$gte": win_threshold}
        }}
    ]

    resultado = list(battles_collection.aggregate(pipeline))
    print("Resultado da Query:", resultado)  # Debug
    return resultado

# Consulta 3: Derrotas utilizando um combo de cartas
def calculate_losses_with_combo(cards, start_time, end_time):
    # Validando datas
    start_time = validate_date(start_time)
    end_time = validate_date(end_time)
    if not start_time or not end_time:
        return {"error": "Invalid date format. Use 'YYYY-MM-DDTHH:MM:SS'"}

    return battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "team.cards.name": {"$all": cards},
        "winner": "opponent"
    })

# Rota para calcular taxa de vitória
@app.route("/winrate", methods=["GET"])
def win_rate():
    card_name = request.args.get('card_name')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    if not card_name or not start_time or not end_time:
        return jsonify({"error": "Missing required parameters"}), 400

    # Validar datas
    start_time = validate_date(start_time)
    end_time = validate_date(end_time)

    if not start_time or not end_time:
        return jsonify({"error": "Invalid date format. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400

    # Calcular win rate
    result = calculate_win_rate(card_name, start_time, end_time)

    return jsonify(result)

# Rota para obter decks vitoriosos
@app.route('/winning-decks', methods=['GET'])
def get_winning_decks():
    try:
        win_threshold = float(request.args.get('win_threshold', 50))
        start_time = request.args.get('start_time', '2000-01-01T00:00:00')
        end_time = request.args.get('end_time', '2100-01-01T00:00:00')

        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")

        print(f"Iniciando consulta de decks vencedores...")
        print(f"Parâmetros recebidos - win_threshold: {win_threshold}, start_time: {start_time}, end_time: {end_time}")

        battles = list(battles_collection.find({"battleTime": {"$gte": start_time, "$lte": end_time}}))
        print(f"Total de batalhas encontradas: {len(battles)}")

        deck_stats = defaultdict(lambda: {'wins': 0, 'total': 0, 'players': set()})

        for battle in battles:
            team = battle.get('team', [{}])[0]
            opponent = battle.get('opponent', [{}])[0]

            if 'crowns' not in team or 'crowns' not in opponent:
                continue

            if team['crowns'] > opponent['crowns']:
                winner = team
                loser = opponent
            elif opponent['crowns'] > team['crowns']:
                winner = opponent
                loser = team
            else:
                continue  # Empate

            # Decks como tupla de strings
            winner_deck = tuple(sorted([str(card) for card in winner.get('cards', [])]))
            loser_deck = tuple(sorted([str(card) for card in loser.get('cards', [])]))

            # Captura nome do jogador vencedor
            winner_name = winner.get('name', 'Desconhecido')

            deck_stats[winner_deck]['wins'] += 1
            deck_stats[winner_deck]['total'] += 1
            deck_stats[winner_deck]['players'].add(winner_name)

            deck_stats[loser_deck]['total'] += 1

        # Montagem do resultado final
        resultados = []

        for deck, stats in deck_stats.items():
            winrate = (stats['wins'] / stats['total']) * 100 if stats['total'] > 0 else 0

            if abs(winrate - win_threshold) <= 5:  # ±5% margem
                resultados.append({
                    'deck_cartas': list(deck),
                    'winrate_percentual': round(winrate, 2),
                    'vitorias': stats['wins'],
                    'jogadores_vencedores': list(stats['players']),
                    'batalhas_total': stats['total']
                })

        # Organiza por maior taxa de vitória
        resultados = sorted(resultados, key=lambda d: d['winrate_percentual'], reverse=True)

        return jsonify(resultados)

    except Exception as e:
        print(f"Erro ao buscar os decks vencedores: {e}")
        return jsonify({'erro': 'Erro ao buscar os decks vencedores'}), 500

# Rota para calcular derrotas com combo de cartas
@app.route("/losses_with_combo", methods=["GET"])
def losses_with_combo():
    cards = request.args.getlist("cards")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    return jsonify({"losses": calculate_losses_with_combo(cards, start_time, end_time)})

# Rota para obter dados de um jogador
@app.route("/player/<tag>", methods=["GET"])
def get_player(tag):
    data = fetch_player_data(tag)
    if data:
        return jsonify(data)
    return jsonify({"error": "Player not found"}), 404

# Rota para obter o histórico de batalhas de um jogador
@app.route("/battlelog/<tag>", methods=["GET"])
def get_battle_log(tag):
    data = fetch_battle_log(tag)
    if data:
        return jsonify(data)
    return jsonify({"error": "No battle logs found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
