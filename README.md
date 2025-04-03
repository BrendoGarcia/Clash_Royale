# API-Atividade

Atenção Ao formato da data/hora.
Atenção Aos Registros de Batalhos apenas as ultimas 30 são armazenas limitação da prorpia api do clash Royale.
Portanto os registros são todos desse ano.
Atenção Para rodar tudo certinho é necesario ter o MongoDb instalado o pc,
trocar a chave da api do clash royale, Atenção ao criar a chave da api procure na internet o ip da sua rede,
Atenção instalar as bibliotecas antes de rodas o codigo,
Por ultimo se quiser usar os dados de batalha de outro jogador é preciso ou baixar os dados aparir da api. ou fazer uma requisição das batalhas pela api. 
PS: Já temos esse endpoint funcionando



Antes de Fazer qualquer consulta deve ser feito uma requisição. requisição essa com a função de pegar os dados da api e armazenar no banco MongoDB.
Deve ser feito de seguinte forma.

```bash
http://127.0.0.1:5000/player/battlelog/<tag>
````
Onde o Campo TAG deve conter a tag do jogor com isso sera baixado os dados da ultimas 30 batalhas do player.

Exemplo de como deve ser feira;
```bash
http://127.0.0.1:5000/player/battlelog/202GY8C0YP
```
Exemplo de Uma Batalha:
```bash
 {
    "arena": {
      "id": 54000011,
      "name": "Spooky Town"
    },
    "battleTime": "20250403T175213.000Z",
    "deckSelection": "collection",
    "gameMode": {
      "id": 72000006,
      "name": "Ladder"
    },
    "isHostedMatch": false,
    "isLadderTournament": false,
    "leagueNumber": 1,
    "opponent": [
      {
    "team": [
      {,
        "crowns": 1,
        "elixirLeaked": 1.17,
        "globalRank": null,
        "kingTowerHitPoints": 4392,
        "name": "IceBee2007",
        "princessTowersHitPoints": null,
        "startingTrophies": 3898,
        "supportCards": [
          {
            "iconUrls": {
              "medium": "https://api-assets.clashroyale.com/cards/300/MVj028nMLCmBuP3HlV503uxVAxFg7jyliJVZ5JYJ1h8.png"
            },
            "id": 159000002,
            "level": 2,
            "maxLevel": 6,
            "name": "Dagger Duchess",
            "rarity": "legendary"
          }
        ],
        "tag": "#202GY8C0YP",
        "trophyChange": -30
      }
    ],
    "type": "PvP"
  }
```




Consultas Solicitadas:
Descrição:
Este endpoint retorna a taxa de vitória de um card específico dentro de um intervalo de tempo definido.

```bash
URL:http://127.0.0.1:5000/winrate
```

Parâmetros:
```bash
card_name | String |Sim | Nome do card para o qual deseja obter a taxa de vitória |
start_time| String |Sim | Data e hora de início do intervalo de busca             |
end_time  | String |SIM |Data e hora de fim do intervalo de busca                 |
```
Exemplo de Uso.
```bash
http://127.0.0.1:5000/winrate?card_name=Witch&start_time=2025-01-01T00:00:00&end_time=2025-04-01T23:59:59
```
Exemplo de Resposta:
```bash
{
  "card_name": "Balloon",
  "end_time": "2025-04-01T23:59:59",
  "start_time": "2025-01-01T00:00:00",
  "total_battles": 14,
  "total_wins": 8,
  "win_rate": 57.14285714285714
}
```
