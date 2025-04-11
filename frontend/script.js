const form = document.getElementById("filters");
const deckContainer = document.getElementById("deck-container");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  deckContainer.innerHTML = "<p>Carregando...</p>";

  const start = document.getElementById("start").value;
  const end = document.getElementById("end").value;
  const threshold = document.getElementById("threshold").value || 50;

  const url = `/winning-decks?start_time=${start}&end_time=${end}&win_threshold=${threshold}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (!Array.isArray(data)) {
      deckContainer.innerHTML = "<p>Nenhum deck encontrado.</p>";
      return;
    }

    deckContainer.innerHTML = "";

    data.forEach(deck => {
      const card = document.createElement("div");
      card.classList.add("deck-card");

      card.innerHTML = `
        <h3>Winrate: ${deck.winrate_percentual}%</h3>
        <ul>${deck.deck_cartas.map(c => `<li>${c}</li>`).join("")}</ul>
        <div class="deck-info">
          Vitórias: ${deck.vitorias}<br/>
          Batalhas: ${deck.batalhas_total}<br/>
          Jogadores: ${deck.jogadores_vencedores.join(", ")}
        </div>
      `;

      deckContainer.appendChild(card);
    });
  } catch (error) {
    console.error(error);
    deckContainer.innerHTML = "<p>Erro ao buscar os decks.</p>";
  }
});
