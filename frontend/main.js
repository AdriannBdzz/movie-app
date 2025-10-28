const API = "http://127.0.0.1:8000"; // ajusta si despliegas en otro host

const $ = (sel) => document.querySelector(sel);
const resultsEl = $("#results");
const favsEl = $("#favs");
const btnSearch = $("#btnSearch");
const btnShowFavs = $("#btnShowFavs");
const btnReco = $("#btnReco");
const toastEl = $("#toast");
const spinner = $("#spinner");
const queryInput = $("#query");

let searchAbort = null;
let searchTimer = null;

function showToast(msg){
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 1800);
}

function setLoading(flag){
  spinner.style.display = flag ? "inline-block" : "none";
}

async function doSearch(q){
  if (q.length < 2){
    renderResults([]);
    return;
  }
  // Cancelar la petición anterior si sigue en vuelo
  if (searchAbort) searchAbort.abort();
  searchAbort = new AbortController();

  setLoading(true);
  try{
    const res = await fetch(
      `${API}/search?q=${encodeURIComponent(q)}&_=${Date.now()}`,
      { cache: "no-store", signal: searchAbort.signal }
    );
    const data = await res.json();
    renderResults(data.results || []);
  }catch(e){
    if (e.name !== "AbortError") showToast("Error buscando películas");
  }finally{
    setLoading(false);
  }
}

// Click en botón Buscar (opcional; Enter o escribir ya buscan)
btnSearch.addEventListener("click", () => {
  const q = queryInput.value.trim();
  doSearch(q);
});

// Búsqueda en tiempo real con debounce
queryInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => doSearch(queryInput.value.trim()), 350);
});

// Enter busca al instante
queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    clearTimeout(searchTimer);
    doSearch(queryInput.value.trim());
  }
});

btnShowFavs.addEventListener("click", loadFavs);

btnReco.addEventListener("click", async () => {
  const userId = $("#userId").value.trim();
  if (!userId) return showToast("Introduce tu usuario");
  setLoading(true);
  try{
    const res = await fetch(
      `${API}/recommendations?user_id=${encodeURIComponent(userId)}&_=${Date.now()}`,
      { cache: "no-store" }
    );
    if (!res.ok){
      const err = await res.json();
      return showToast(err.detail || "No se pudo recomendar");
    }
    const data = await res.json();
    renderResults(data.results || []);
  }catch(e){
    showToast("Error cargando recomendaciones");
  }finally{
    setLoading(false);
  }
});

async function loadFavs(){
  const userId = $("#userId").value.trim();
  if (!userId) return showToast("Introduce tu usuario");
  setLoading(true);
  try{
    const res = await fetch(
      `${API}/favorites?user_id=${encodeURIComponent(userId)}&_=${Date.now()}`,
      { cache: "no-store" }
    );
    const favs = await res.json();
    renderFavs(favs);
  }catch(e){
    showToast("Error cargando favoritos");
  }finally{
    setLoading(false);
  }
}

function card(movie){
  const div = document.createElement("div");
  div.className = "card";
  div.innerHTML = `
    <img class="poster" src="https://image.tmdb.org/t/p/w342${movie.poster_path || ''}" onerror="this.style.display='none'" alt="Poster"/>
    <div class="card-body">
      <div class="title">${movie.title}</div>
      <div class="card-actions">
        <button class="btn btn-primary" data-action="fav">⭐ Añadir</button>
      </div>
    </div>`;
  div.querySelector('[data-action="fav"]').addEventListener("click", () => addFav(movie));
  return div;
}

function favCard(movie){
  const div = document.createElement("div");
  div.className = "card";
  div.innerHTML = `
    <img class="poster" src="https://image.tmdb.org/t/p/w342${movie.poster_path || ''}" onerror="this.style.display='none'" alt="Poster"/>
    <div class="card-body">
      <div class="title">${movie.title}</div>
      <div class="card-actions">
        <button class="btn" data-action="del">🗑️ Quitar</button>
      </div>
    </div>`;
  div.querySelector('[data-action="del"]').addEventListener("click", () => delFav(movie.id));
  return div;
}

function renderResults(list){
  const empty = document.getElementById("resultsEmpty");
  resultsEl.innerHTML = "";
  if (!list.length){
    if (empty) empty.style.display = "block";
    return;
  } else {
    if (empty) empty.style.display = "none";
  }
  for (const m of list){
    resultsEl.appendChild(card(m));
  }
}

function renderFavs(list){
  const empty = document.getElementById("favsEmpty");
  favsEl.innerHTML = "";
  if (!list.length){
    if (empty) empty.style.display = "block";
  } else {
    if (empty) empty.style.display = "none";
  }
  for (const m of list){
    favsEl.appendChild(favCard(m));
  }
  // mostrar botón de recomendaciones si hay ≥ 5
  btnReco.style.display = list.length >= 5 ? "inline-flex" : "none";
}

async function addFav(m){
  const userId = $("#userId").value.trim();
  if (!userId) return showToast("Introduce tu usuario");
  try{
    const res = await fetch(`${API}/favorites`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, movie: m })
    });
    if (!res.ok){
      const err = await res.json();
      return showToast(err.detail || "No se pudo añadir");
    }
    showToast("Añadida a favoritos");
    await loadFavs();
  }catch(e){
    showToast("Error al añadir");
  }
}

async function delFav(movieId){
  const userId = $("#userId").value.trim();
  if (!userId) return showToast("Introduce tu usuario");
  try{
    const res = await fetch(
      `${API}/favorites/${movieId}?user_id=${encodeURIComponent(userId)}`,
      { method: "DELETE" }
    );
    if (!res.ok){
      const err = await res.json();
      return showToast(err.detail || "No se pudo eliminar");
    }
    showToast("Eliminada de favoritos");
    await loadFavs();
  }catch(e){
    showToast("Error al eliminar");
  }
}

// Estado inicial
renderResults([]);
renderFavs([]);
