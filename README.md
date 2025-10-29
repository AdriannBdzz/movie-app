
# 🎬 Movie-App — Recomendador de Películas con Machine Learning  

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=flat&logo=sqlite&logoColor=white)
![TMDb](https://img.shields.io/badge/TMDb-API-green?style=flat&logo=tmdb&logoColor=white)

##  Descripción  

**Movie-App** es una aplicación web que recomienda películas personalizadas mediante un **modelo de Machine Learning entrenado por usuario**.  
El sistema combina información de **The Movie Database (TMDb)**, datos de favoritos del usuario y un modelo de **regresión logística** que aprende de sus preferencias.  

El proyecto está dividido en:  
-  **Backend (FastAPI + ML + SQLite)**  
-  **Frontend (HTML + JS)** *(publicado vía GitHub Pages)*  

---

##  Arquitectura general  

```
movie-app/
├── backend/
│   ├── app.py          ← API principal FastAPI
│   ├── database.py     ← Configuración SQLite + SQLAlchemy
│   ├── models.py       ← Modelo ORM: tabla de favoritos
│   ├── schemas.py      ← Modelos Pydantic (Movie, Favorite, RecoResponse)
│   ├── tmdb.py         ← Cliente TMDb API (búsqueda, detalles, colecciones, keywords)
│   ├── ml.py           ← Entrenamiento ML por usuario (regresión logística)
│   ├── recommender.py  ← Recomendador simple basado en géneros
│   ├── movies.db       ← Base de datos SQLite
│   ├── .env            ← Variables de entorno (TMDb API key, idioma, región)
│   └── models/         ← Carpeta donde se guardan los pesos del modelo entrenado
└── frontend/
    ├── index.html
    ├── main.js
    └── style.css
```

---

##  Tecnologías  

| Componente | Tecnología | Descripción |
|-------------|-------------|-------------|
| API Backend | **FastAPI** | Framework web moderno, rápido y asíncrono |
| Base de datos | **SQLite + SQLAlchemy** | Almacena favoritos de usuario |
| Machine Learning | **NumPy** | Entrenamiento de regresión logística personalizada |
| Fuente de datos | **TMDb API** | Obtiene películas, géneros, directores y keywords |
| Frontend | **HTML + JS** | Interfaz simple para búsqueda y favoritos |

---

##  Ejecución local  

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/AdriannBdzz/movie-app.git
cd movie-app/backend
```

### 2️⃣ Crear y activar entorno virtual
```bash
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
```

### 3️⃣ Instalar dependencias
```bash
pip install -r requirements.txt
```

*(Si no existe el archivo, instala los principales manualmente)*  
```bash
pip install fastapi uvicorn sqlalchemy requests python-dotenv numpy
```

### 4️⃣ Configurar variables de entorno
Copia el archivo `.env.example` como `.env` y añade tu clave de TMDb:
```
TMDB_API_KEY=tu_api_key_aqui
TMDB_LANG=es-ES
TMDB_REGION=ES
```

### 5️⃣ Ejecutar servidor
```bash
uvicorn app:app --reload
```

El backend se ejecutará en:
👉 [http://localhost:8000](http://localhost:8000)

---

##  Endpoints principales  

| Método | Ruta | Descripción |
|--------|------|--------------|
| `GET /health` | Verifica el estado de la API |
| `GET /search?q=` | Busca películas en TMDb |
| `POST /favorites` | Añade película a favoritos |
| `GET /favorites?user_id=` | Lista favoritos del usuario |
| `DELETE /favorites/{movie_id}` | Elimina un favorito |
| `GET /recommendations?user_id=` | Devuelve recomendaciones personalizadas |

---

##  Cómo funciona el modelo  

1. **El usuario marca películas como favoritas.**  
2. **Cuando alcanza ≥ 5 favoritos, se entrena un modelo propio.**  
   - Enriquecimiento con datos TMDb (géneros, keywords, director, colección).  
   - Generación de *negativos* a partir de películas populares.  
   - Entrenamiento de **regresión logística** por usuario.  
3. **Recomendaciones = ML + rating TMDb + diversidad.**  
4. **Modelo guardado** en `/models/{user_id}_w.npy` y reutilizado.

---

##  Ejemplo de flujo API  

```bash
GET /search?q=inception
POST /favorites { "user_id": "user123", "movie": { "id": 27205, "title": "Inception" } }
GET /recommendations?user_id=user123
```

---

##  Base de datos  

| Campo | Tipo | Descripción |
|--------|------|-------------|
| id | int | Clave primaria |
| user_id | str | Identificador del usuario |
| movie_id | int | ID TMDb |
| movie_title | str | Título |
| poster_path | str | Imagen |
| genre_ids | str | Lista coma-separada de géneros |

---

##  Autor  

**Adrián Bermúdez Muñoz**  
🎓 Proyecto personal de IA y desarrollo web.  
💡 Objetivo: aplicar técnicas de ML para personalizar recomendaciones de contenido.
