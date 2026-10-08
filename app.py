import os
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from services.database import Database
from services.recommender import RecommenderService
from services.search import SearchService
from services.vector_engine import VectorEngine
from services.collaborative_engine import CollaborativeEngine

app = Flask(__name__)
load_dotenv(Path(__file__).resolve().parent / ".env")



# --- HITELESITÉSI ADATOK MEGADÁSA, ADATBÁZIS INICIALIZÁLÁSA ---

def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


URI = required_env("NEO4J_URI")
USERNAME = required_env("NEO4J_USERNAME")
PASSWORD = required_env("NEO4J_PASSWORD")

db = Database(URI, (USERNAME, PASSWORD))



# --- AJÁNLÓMOTOROK LÉTREHOZÁSA  ---

vector_engine = VectorEngine(db)
collab_engine = CollaborativeEngine(db)

recommender_service = RecommenderService(db, vector_engine, collab_engine)
search_service = SearchService(db)



# --- MODELEK BETÖLTÉSE VAGY TANÍTÁSA ---

if not os.path.exists('data'):
    os.makedirs('data')

try:
    with app.app_context():
        print("--- SYSTEM STARTUP ---")
        vector_engine.fit()
        collab_engine.fit()
        print("--- SYSTEM READY ---")
except Exception as e:
    print(f"Startup Warning: {e}")



# --- HTTP VÉGPONTOK ÖSSZEKAPCSOLÁSA ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        books = recommender_service.get_recommendations(
            data.get('constraints', {}), 
            data.get('preferences', {}),
            data.get('settings', {}) 
        )
        return render_template('result.html', books=books)
    except Exception as e:
        print(f"Error in /recommend: {e}")
        return f"<h3>Szerver Hiba: {e}</h3>", 500

@app.route('/api/search', methods=['GET'])
def search():
    term = request.args.get('q', '')
    search_type = request.args.get('type', 'book')
    
    if len(term) < 2: return jsonify([])

    try:
        results = search_service.search_items(term, search_type)
        return jsonify(results)
    except Exception as e:
        print(f"Search Error: {e}")
        return jsonify([])



# --- ALKALMAZÁS FUTTATÁSA ---

if __name__ == '__main__':
    try:
        app.run(port=5000, debug=True)
    finally:
        db.close()