from flask import Flask, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime
import re
from collections import defaultdict
from datetime import datetime
from pymongo import MongoClient
import json
from flask_cors import CORS


# Configuração do MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["clash_royale"]
players_collection = db["players"]
battles_collection = db["battles"]

# Configuração da API Flask
app = Flask(__name__)
cors = CORS(app)
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

    # Total de batalhas em que a carta participou
    total_battles = battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "$or": [
            {"team.cards.name": card_name},
            {"opponent.cards.name": card_name}
        ]
    })

    # Vitórias com a carta no time vencedor
    wins_as_team = battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "team.cards.name": card_name,
        "$expr": {"$gt": ["$team.crowns", "$opponent.crowns"]}
    })

    # Vitórias com a carta no oponente vencedor
    wins_as_opponent = battles_collection.count_documents({
        "battleTime": {"$gte": start_time, "$lte": end_time},
        "opponent.cards.name": card_name,
        "$expr": {"$gt": ["$opponent.crowns", "$team.crowns"]}
    })

    total_wins = wins_as_team + wins_as_opponent
    total_losses = total_battles - total_wins

    win_rate = round((total_wins / total_battles * 100), 2) if total_battles > 0 else 0
    loss_rate = round((total_losses / total_battles * 100), 2) if total_battles > 0 else 0

    return {
        "card_name": card_name,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_battles": total_battles,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "win_rate": win_rate,
        "loss_rate": loss_rate
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

def calculate_disadvantage_wins(card_name, trophy_percent):
    trophy_factor = 1 - (trophy_percent / 100)

    query = {
        "$expr": {
            "$and": [
                # Partida durou menos de 120 segundos
                {"$lt": ["$duration", 120]},
                
                # Vencedor teve menos troféus que o perdedor, com Z% de diferença
                {
                    "$cond": [
                        {"$gt": [{"$arrayElemAt": ["$team.crowns", 0]}, {"$arrayElemAt": ["$opponent.crowns", 0]}]},
                        {
                            "$lt": [
                                {"$arrayElemAt": ["$team.startTrophies", 0]},
                                {
                                    "$multiply": [
                                        {"$arrayElemAt": ["$opponent.startTrophies", 0]},
                                        trophy_factor
                                    ]
                                }
                            ]
                        },
                        {
                            "$lt": [
                                {"$arrayElemAt": ["$opponent.startTrophies", 0]},
                                {
                                    "$multiply": [
                                        {"$arrayElemAt": ["$team.startTrophies", 0]},
                                        trophy_factor
                                    ]
                                }
                            ]
                        }
                    ]
                },

                # Perdedor destruiu 2 ou mais torres
                {
                    "$cond": [
                        {"$gt": [{"$arrayElemAt": ["$team.crowns", 0]}, {"$arrayElemAt": ["$opponent.crowns", 0]}]},
                        {"$gte": [{"$arrayElemAt": ["$opponent.crowns", 0]}, 2]},
                        {"$gte": [{"$arrayElemAt": ["$team.crowns", 0]}, 2]}
                    ]
                }
            ]
        },
        "$or": [
            {"team.cards.name": card_name},
            {"opponent.cards.name": card_name}
        ]
    }

    result = battles_collection.count_documents(query)
    return {"card": card_name, "disadvantage_victories": result}

def top_combos(n, min_win_rate, start_time, end_time):
    pipeline = [
        {
            "$match": {
                "battleTime": {"$gte": start_time, "$lte": end_time},
                "team.cards": {"$exists": True},
                "opponent.cards": {"$exists": True}
            }
        },
        {
            "$project": {
                "team_cards": "$team.cards.name",
                "team_crowns": {"$arrayElemAt": ["$team.crowns", 0]},
                "opponent_crowns": {"$arrayElemAt": ["$opponent.crowns", 0]}
            }
        },
        {
            "$project": {
                "combo": {
                    "$slice": [
                        {"$setUnion": ["$team_cards"]}, n
                    ]
                },
                "is_win": {"$gt": ["$team_crowns", "$opponent_crowns"]}
            }
        },
        {
            "$group": {
                "_id": "$combo",
                "total": {"$sum": 1},
                "wins": {"$sum": {"$cond": ["$is_win", 1, 0]}}
            }
        },
        {
            "$project": {
                "total": 1,
                "wins": 1,
                "win_rate": {
                    "$cond": [
                        {"$eq": ["$total", 0]},
                        0,
                        {"$multiply": [{"$divide": ["$wins", "$total"]}, 100]}
                    ]
                }
            }
        },
        {
            "$match": {
                "win_rate": {"$gte": min_win_rate}
            }
        },
        {
            "$sort": {"win_rate": -1}
        },
        {
            "$limit": 10
        }
    ]

    result = battles_collection.aggregate(pipeline)

    return [
        {
            "combo": r["_id"],
            "wins": r["wins"],
            "total_battles": r["total"],
            "win_rate": round(r["win_rate"], 2)
        }
        for r in result
    ]


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
    try:
        cards = request.args.getlist("cards")
        start_time = request.args.get("start_time", "2000-01-01T00:00:00")
        end_time = request.args.get("end_time", "2100-01-01T00:00:00")

        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")

        losses = 0

        battles = battles_collection.find({"battleTime": {"$gte": start_time, "$lte": end_time}})

        for battle in battles:
            team = battle.get("team", [{}])[0]
            opponent = battle.get("opponent", [{}])[0]

            if 'crowns' not in team or 'crowns' not in opponent:
                continue

            if team['crowns'] < opponent['crowns']:
                loser = team
            elif opponent['crowns'] < team['crowns']:
                loser = opponent
            else:
                continue  # empate

            loser_cards = [card.get("name") if isinstance(card, dict) else card for card in loser.get("cards", [])]

            if all(card in loser_cards for card in cards):
                losses += 1

        return jsonify({"losses": losses})

    except Exception as e:
        print(f"Erro ao calcular derrotas com combo: {e}")
        return jsonify({"erro": "Erro ao calcular derrotas com combo"}), 500


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

# Rota Para Obter as Vitoais Estranhas;
@app.route('/vitorias-desvantagem', methods=['GET'])
def vitorias_com_desvantagem():
    card_name = request.args.get('card')
    trophy_percent = float(request.args.get('percent', 10))  # Percentual de desvantagem
    try:
        disadvantage_factor = 1 - (trophy_percent / 100)
    except (ZeroDivisionError, ValueError):
        return jsonify({"error": "Percentual de desvantagem inválido."}), 400

    if not card_name:
        return jsonify({"error": "O parâmetro 'card' é obrigatório."}), 400

    query = {
        "$expr": {
            "$and": [
                # A partida durou menos de 2 minutos
                {"$lt": ["$duration", 120]},  # Assumindo que 'duration' possa existir em alguns documentos

                # Verificando se o vencedor tinha pelo menos Z% menos troféus do que o perdedor
                {
                    "$or": [
                        {
                            "$and": [
                                {"$gt": [{"$arrayElemAt": ["$team.crowns", 0]}, {"$arrayElemAt": ["$opponent.crowns", 0]}]},
                                {
                                    "$lte": [
                                        {"$arrayElemAt": ["$team.startTrophies", 0]},
                                        {"$multiply": [{"$arrayElemAt": ["$opponent.startTrophies", 0]}, disadvantage_factor]}
                                    ]
                                }
                            ]
                        },
                        {
                            "$and": [
                                {"$gt": [{"$arrayElemAt": ["$opponent.crowns", 0]}, {"$arrayElemAt": ["$team.crowns", 0]}]},
                                {
                                    "$lte": [
                                        {"$arrayElemAt": ["$opponent.startTrophies", 0]},
                                        {"$multiply": [{"$arrayElemAt": ["$team.startTrophies", 0]}, disadvantage_factor]}
                                    ]
                                }
                            ]
                        }
                    ]
                },

                # Verificando se o perdedor derrubou pelo menos 2 torres
                {
                    "$or": [
                        {"$gte": [{"$arrayElemAt": ["$opponent.crowns", 0]}, 2]},
                        {"$gte": [{"$arrayElemAt": ["$team.crowns", 0]}, 2]}
                    ]
                }
            ]
        },
        # Filtra partidas que envolvem a carta especificada
        "$or": [
            {"team.cards.name": card_name},
            {"opponent.cards.name": card_name}
        ]
    }

    try:
        count = battles_collection.count_documents(query)
        total_duration = 0

        matching_battles = battles_collection.find(query)
        for battle in matching_battles:
            # Tentando acessar o campo 'duration'. Se não existir, get retornará None e não afetará a soma.
            duration = battle.get('duration')
            if isinstance(duration, (int, float)):
                total_duration += duration

        average_duration = total_duration / count if count > 0 and total_duration > 0 else 0

        return jsonify({
            "card": card_name,
            "disadvantage_victories": count,
            "average_duration": average_duration  # Tempo médio em segundos
        })
    except Exception as e:
        return jsonify({"error": f"Erro ao consultar o banco de dados: {str(e)}"}), 500



# Rota Para obter os cambos vencedores
@app.route('/combos-vencedores', methods=['GET'])
def combos_vencedores():
    try:
        n = int(request.args.get('n'))
        min_win_rate = float(request.args.get('percent'))
        start = datetime.fromisoformat(request.args.get('start'))
        end = datetime.fromisoformat(request.args.get('end'))
    except:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    pipeline = [
    {
        "$match": {
            "battleTime": {"$gte": start, "$lte": end},
            "team.cards": {"$exists": True},
            "opponent.cards": {"$exists": True}
        }
    },
    {
        "$project": {
            "team_cards": "$team.cards.name",
            "team_crowns": {"$arrayElemAt": ["$team.crowns", 0]},
            "opponent_crowns": {"$arrayElemAt": ["$opponent.crowns", 0]}
        }
    },
    {
        "$project": {
            "combo": {
                "$slice": [
                    {
                        "$sortArray": {
                            "input": {
                                "$setUnion": ["$team_cards"]  # remove duplicatas
                            },
                            "sortBy": 1  # ordena alfabeticamente
                        }
                    },
                    n  # limita a n cards
                ]
            },
            "is_win": {"$gt": ["$team_crowns", "$opponent_crowns"]}
        }
    },
    {
        "$group": {
            "_id": "$combo",
            "total": {"$sum": 1},
            "wins": {"$sum": {"$cond": ["$is_win", 1, 0]}}
        }
    },
    {
        "$project": {
            "total": 1,
            "wins": 1,
            "win_rate": {
                "$cond": [
                    {"$eq": ["$total", 0]},
                    0,
                    {"$multiply": [{"$divide": ["$wins", "$total"]}, 100]}
                ]
            }
        }
    },
    {
        "$match": {
            "win_rate": {"$gte": min_win_rate}
        }
    },
    {
        "$sort": {"win_rate": -1}
    },
    {
        "$limit": 100
    }
]


    results = list(battles_collection.aggregate(pipeline))

    return jsonify([
        {
            "combo": r["_id"],
            "wins": r["wins"],
            "total_battles": r["total"],
            "win_rate": round(r["win_rate"], 2)
        }
        for r in results
    ])




if __name__ == "__main__":
    app.run(debug=True)