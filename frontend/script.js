const baseUrl = "https://projetomongo-456802.rj.r.appspot.com";

function formatDate(id) {
    const val = document.getElementById(id).value;
    return new Date(val).toISOString().split(".")[0];
}

async function getWinRate() {
    const card = document.getElementById("wr_card").value;
    const start = formatDate("wr_start");
    const end = formatDate("wr_end");
    const res = await fetch(`${baseUrl}/winrate?card_name=${card}&start_time=${start}&end_time=${end}`);
    const data = await res.json();
    document.getElementById("wr_result").textContent = JSON.stringify(data, null, 2);
}

async function getWinningDecks() {
    const threshold = document.getElementById("wd_threshold").value;
    const start = formatDate("wd_start");
    const end = formatDate("wd_end");
    const res = await fetch(`${baseUrl}/winning-decks?win_threshold=${threshold}&start_time=${start}&end_time=${end}`);
    const data = await res.json();
    document.getElementById("wd_result").textContent = JSON.stringify(data, null, 2);
}

async function getLossesWithCombo() {
    const cards = document.getElementById("lc_cards").value.split(",").map(c => c.trim());
    const start = formatDate("lc_start");
    const end = formatDate("lc_end");
    const params = new URLSearchParams();
    cards.forEach(card => params.append("cards", card));
    params.append("start_time", start);
    params.append("end_time", end);
    const res = await fetch(`${baseUrl}/losses_with_combo?${params.toString()}`);
    const data = await res.json();
    document.getElementById("lc_result").textContent = JSON.stringify(data, null, 2);
}

async function getPlayer() {
    const tag = document.getElementById("player_tag").value;
    const res = await fetch(`${baseUrl}/player/${tag}`);
    const data = await res.json();
    document.getElementById("player_result").textContent = JSON.stringify(data, null, 2);
}

async function getBattleLog() {
    const tag = document.getElementById("battle_tag").value;
    const res = await fetch(`${baseUrl}/battlelog/${tag}`);
    const data = await res.json();
    document.getElementById("battle_result").textContent = JSON.stringify(data, null, 2);
}

async function getVitoriasDesvantagem() {
    const card = document.getElementById("vd_card").value;
    const percent = document.getElementById("vd_percent").value;
    const res = await fetch(`${baseUrl}/vitorias-desvantagem?card=${card}&percent=${percent}`);
    const data = await res.json();
    document.getElementById("vd_result").textContent = JSON.stringify(data, null, 2);
}

async function getCombosVencedores() {
    const n = document.getElementById("cv_n").value;
    const percent = document.getElementById("cv_percent").value;
    const start = formatDate("cv_start");
    const end = formatDate("cv_end");
    const res = await fetch(`${baseUrl}/combos-vencedores?n=${n}&percent=${percent}&start=${start}&end=${end}`);
    const data = await res.json();
    document.getElementById("cv_result").textContent = JSON.stringify(data, null, 2);
}

async function getTopJogadores(){
    const res = await fetch(`${baseUrl}/top-jogadores`);
    const data = await res.json();
    document.getElementById("top_result").textContent = JSON.stringify(data, null, 2);
}

async function getCartasMaisComuns(){
    const res = await fetch(`${baseUrl}/cartas-mais-comuns`);
    const data = await res.json();
    document.getElementById("comunss_result").textContent = JSON.stringify(data, null, 2);
}

async function getCartasMenorElixir(){
    const res = await fetch(`${baseUrl}/cartas-menor-elixir`);
    const data = await res.json();
    document.getElementById("elisir_results").textContent = JSON.stringify(data, null, 2);
}
