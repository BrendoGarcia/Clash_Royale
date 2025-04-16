from flask import Flask, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pymongo import MongoClient
import json
from flask_cors import CORS
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import random
from itertools import combinations

# Configuração do MongoDB
# client = MongoClient("mongodb://localhost:27017/")
uri = "mongodb+srv://brendofcg:qwer1234Bb@agrupamentobanco.zb2av.mongodb.net/?appName=AgrupamentoBanco"
client = MongoClient(uri, server_api=ServerApi('1')) 
db = client["clash_royale"]
players_collection = db["players"]
battles_collection = db["battles"]
# Configuração da API Flask
app = Flask(__name__)
cors = CORS(app)
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6ImMwNzhlOTU1LTMwNjMtNGYxNi05OWY4LWE0ZDViYzdlYmY4NCIsImlhdCI6MTc0NDgwNDAwNiwic3ViIjoiZGV2ZWxvcGVyLzhmNzA4NDY0LWIxMmYtMDdiMy0zN2FlLTU0NWY4MTM2YmEyMSIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxNzkuMTI0LjE0MC4xMTMiXSwidHlwZSI6ImNsaWVudCJ9XX0.Ty9kTfMal0qwf8qp-LXKCcIHQjE6Mt8gM-eokyu3DkPutdYWpmsIS9HgBdo1ML88Y7FGt4bgNKiAgeXej40C5Q"  # Substitua pelo seu token real
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
# Função para buscar e armazenar batalhas de um jogador
def fetch_battle_log(tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}/battlelog"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        battles = response.json()
        for battle in battles:
            # Converter battleTime para datetime antes de salvar
            try:
                battle_time = datetime.strptime(battle["battleTime"], "%Y%m%dT%H%M%S.000Z")
                battle["battleTime"] = battle_time
            except Exception as e:
                print(f"Erro ao converter battleTime para datetime: {e}")
                continue

            # Gerar uma duração entre 2 e 10 minutos (em segundos)
            duration_minutes = random.randint(2, 10)
            duration_seconds = random.randint(0, 59)
            total_duration = timedelta(minutes=duration_minutes, seconds=duration_seconds).total_seconds()

            battle["duration"] = total_duration

            # Salvar no banco
            battles_collection.update_one(
                {"battleTime": battle["battleTime"]},
                {"$set": battle},
                upsert=True
            )
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
    # Recuperar os parâmetros de entrada
    card = request.args.get('card', '')
    percent = request.args.get('percent', '')
    
    try:
        trophy_percent = float(percent)  # Percentual de desvantagem
    except ValueError:
        trophy_percent = 0  # Caso o valor seja inválido, usamos 0 como padrão
    
    # Simular a obtenção dos dados das partidas (substitua pelo seu código de busca)
    partidas = buscar_partidas_com_card(card)  # Função fictícia para buscar as partidas

    # Filtrar partidas que atendem aos critérios (com base no percentual de desvantagem)
    partidas_validas = []
    for partida in partidas:
        # Checar as condições: vencedor tem menos troféus com base no percentual de desvantagem
        if partida['winner']['trophies'] < partida['loser']['trophies'] * (1 - trophy_percent / 100):
            partidas_validas.append(partida)

    # Cálculo da média de duração e a mais próxima de 120 segundos
    total_duracao = 0
    closest_to_120s = None
    for partida in partidas_validas:
        total_duracao += partida['duration']
        if closest_to_120s is None or abs(partida['duration'] - 120) < abs(closest_to_120s - 120):
            closest_to_120s = partida['duration']
    
    # Calcular a quantidade de vitórias com desvantagem
    disadvantage_victories = len(partidas_validas)
    
    # Calcular a média de duração
    if len(partidas_validas) > 0:
        average_duration = total_duracao / len(partidas_validas)
    else:
        average_duration = 0

    # Criar a resposta
    resultado = {
        "average_duration": average_duration,
        "card": card,
        "closest_to_120s": closest_to_120s,
        "disadvantage_victories": disadvantage_victories
    }

    # Se não houver partidas válidas, adiciona uma mensagem explicativa
    if disadvantage_victories == 0:
        resultado["message"] = "Nenhuma partida atende aos critérios especificados."

    return jsonify(resultado)

def buscar_partidas_com_card(card):
    # Função fictícia para simular a busca de partidas
    # Você deve substituir isso com a lógica real para recuperar as partidas de sua base de dados
    return [
        # Exemplo de partida
        {
            'winner': {'trophies': 3000},
            'loser': {'trophies': 3500},
            'duration': 115
        },
        # Outra partida
        {
            'winner': {'trophies': 2800},
            'loser': {'trophies': 3000},
            'duration': 125
        },
        # Mais partidas podem ser adicionadas aqui
    ]



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

    partidas = list(battles_collection.find({
        "battleTime": {"$gte": start, "$lte": end},
        "team.cards": {"$exists": True},
        "opponent.cards": {"$exists": True}
    }))

    stats = {}

    for partida in partidas:
        try:
            team = partida["team"][0]
            opponent = partida["opponent"][0]

            team_cards = team["cards"]
            cartas = sorted(set([c["name"] for c in team_cards]))

            if len(cartas) < n:
                continue  # ignora combos menores que o esperado

            is_win = team["crowns"] > opponent["crowns"]

            for combo in combinations(cartas, n):
                combo = tuple(sorted(combo))
                if combo not in stats:
                    stats[combo] = {"wins": 0, "total": 0}
                stats[combo]["total"] += 1
                if is_win:
                    stats[combo]["wins"] += 1
        except Exception as e:
            print(f"Erro ao processar partida: {e}")
            continue

    resultados = []
    for combo, dados in stats.items():
        total = dados["total"]
        wins = dados["wins"]
        if total == 0:
            continue
        win_rate = (wins / total) * 100
        if win_rate >= min_win_rate:
            resultados.append({
                "combo": list(combo),
                "wins": wins,
                "total_battles": total,
                "win_rate": round(win_rate, 2)
            })

    resultados.sort(key=lambda x: x["win_rate"], reverse=True)

    return jsonify(resultados[:1000])

# rota para elixit
@app.route('/cartas-menor-elixir', methods=['GET'])
def cartas_menor_elixir():
    pipeline = [
        {"$unwind": "$team"},
        {"$unwind": "$team.cards"},
        {"$group": {
            "_id": "$team.cards.name",
            "elixir": {"$avg": "$team.cards.elixirCost"}  # <--- Corrigido aqui
        }},
        {"$sort": {"elixir": 1}}
    ]

    resultado = list(battles_collection.aggregate(pipeline))
    return jsonify(resultado)


# rotas cartas comuns
@app.route('/cartas-mais-comuns', methods=['GET'])
def cartas_mais_comuns():
    pipeline = [
        {"$unwind": "$team"},
        {"$unwind": "$team.cards"},
        {"$group": {
            "_id": "$team.cards.name",
            "decks": {"$sum": 1}
        }},
        {"$sort": {"decks": -1}},
        {"$limit": 10}
    ]

    resultado = list(battles_collection.aggregate(pipeline))
    return jsonify(resultado)

# Jogadores com mais vitorias e seus decks
@app.route('/top-jogadores', methods=['GET'])
def top_jogadores():
    pipeline = [
        {
            "$project": {
                "player": "$team.name",  # Corrigido aqui
                "cartas": "$team.cards.name",
                "vitoria": {
                    "$gt": [
                        {"$arrayElemAt": ["$team.crowns", 0]},
                        {"$arrayElemAt": ["$opponent.crowns", 0]}
                    ]
                }
            }
        },
        {"$match": {"vitoria": True}},
        {
            "$group": {
                "_id": {"jogador": "$player", "deck": "$cartas"},
                "vitorias_com_deck": {"$sum": 1}
            }
        },
        {"$sort": {"vitorias_com_deck": -1}},
        {
            "$group": {
                "_id": "$_id.jogador",
                "vitorias_totais": {"$sum": "$vitorias_com_deck"},
                "deck_mais_usado": {"$first": "$_id.deck"},
                "vitorias_com_deck": {"$first": "$vitorias_com_deck"}
            }
        },
        {"$sort": {"vitorias_totais": -1}},
        {"$limit": 3}
    ]

    resultado = list(battles_collection.aggregate(pipeline))
    return jsonify(resultado)



if __name__ == "__main__":
    app.run(debug=True)
