import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
from services.database import Database
import time
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

TOP_K = 10
RELEVANT_THRESHOLD = 4.0
MIN_USER_RATINGS = 10
SAMPLE_SIZE = 500
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'tests', 'results')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'console_output.txt')


def calculate_ndcg(recommended_items, relevant_items, k):
    dcg = 0
    idcg = 0
    relevant_set = set(relevant_items)
    
    for i, item in enumerate(recommended_items[:k]):
        if item in relevant_set:
            dcg += 1.0 / np.log2((i + 1) + 1)
            
    num_relevant = min(len(relevant_items), k)
    for i in range(num_relevant):
        idcg += 1.0 / np.log2((i + 1) + 1)
        
    return dcg / idcg if idcg > 0 else 0


def calculate_mrr(recommended_items, relevant_items):
    relevant_set = set(relevant_items)
    for i, item in enumerate(recommended_items):
        if item in relevant_set:
            return 1.0 / (i + 1)
    return 0.0


def save_results_to_file(text_content):
    """Eredmények mentése txt fájlba"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text_content)
    print(f"\n[SICKER] Az eredmények elmentve ide: {OUTPUT_FILE}")



def run_evaluation():
    print(f"--- KOLLABORATÍV EVALUÁCIÓ INDÍTÁSA ---")

    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    missing_config = [
        name
        for name, value in (
            ("NEO4J_URI", neo4j_uri),
            ("NEO4J_USERNAME", neo4j_username),
            ("NEO4J_PASSWORD", neo4j_password),
        )
        if not value
    ]
    if missing_config:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing_config)
        )

    db = Database(neo4j_uri, (neo4j_username, neo4j_password))
    
    query = """
    MATCH (u:User)-[r:RATED]->(b:Book) 
    WHERE r.rating IS NOT NULL 
    RETURN elementId(u) as user_id, elementId(b) as book_id, toFloat(r.rating) as rating
    """
    
    print("Adatok lekérdezése az adatbázisból...")
    with db.get_session() as session:
        result = session.run(query)
        df = pd.DataFrame([r.values() for r in result], columns=['user_id', 'book_id', 'rating'])
    db.close()
    
    user_counts = df['user_id'].value_counts()
    active_users = user_counts[user_counts >= MIN_USER_RATINGS].index
    df = df[df['user_id'].isin(active_users)]
    
    df['user_idx'] = df['user_id'].astype('category').cat.codes
    df['book_idx'] = df['book_id'].astype('category').cat.codes
    
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['user_idx'])

    train_matrix = csr_matrix(
        (train_df['rating'].values, (train_df['user_idx'].values, train_df['book_idx'].values)),
        shape=(df['user_idx'].max() + 1, df['book_idx'].max() + 1)
    )
    
    print("Modell tanítása...")
    model = NearestNeighbors(metric='cosine', algorithm='brute')
    model.fit(train_matrix)

    metrics = {"precision": [], "recall": [], "f1": [], "ndcg": [], "mrr": []}
    test_user_indices = test_df['user_idx'].unique()
    
    if len(test_user_indices) > SAMPLE_SIZE:
        test_user_indices = np.random.choice(test_user_indices, SAMPLE_SIZE, replace=False)

    print(f"Kiértékelés {len(test_user_indices)} felhasználón...")
    
    for u_idx in test_user_indices:
        user_test_history = test_df[(test_df['user_idx'] == u_idx) & (test_df['rating'] >= RELEVANT_THRESHOLD)]
        ground_truth = set(user_test_history['book_idx'].values)
        if not ground_truth: continue

        try:
            distances, indices = model.kneighbors(train_matrix[u_idx], n_neighbors=20)
        except: continue

        raw_recs = {}

        for i, neighbor_idx in enumerate(indices.flatten()[1:]):
            similarity = 1.0 - distances.flatten()[i+1]
            sim_books = train_df[(train_df['user_idx'] == neighbor_idx) & (train_df['rating'] >= RELEVANT_THRESHOLD)]
            for book_idx in sim_books['book_idx'].values:
                raw_recs[book_idx] = raw_recs.get(book_idx, 0) + similarity
        
        sorted_recs = sorted(raw_recs.items(), key=lambda x: x[1], reverse=True)
        top_k_indices = [item[0] for item in sorted_recs[:TOP_K]]
        
        hits = len(set(top_k_indices).intersection(ground_truth))
        p = hits / TOP_K
        r = hits / len(ground_truth)
        
        metrics["precision"].append(p)
        metrics["recall"].append(r)
        metrics["f1"].append(2 * (p * r) / (p + r) if (p + r) > 0 else 0)
        metrics["ndcg"].append(calculate_ndcg(top_k_indices, list(ground_truth), TOP_K))
        metrics["mrr"].append(calculate_mrr(top_k_indices, ground_truth))

    final_precision = np.mean(metrics['precision']) * 100
    final_recall = np.mean(metrics['recall']) * 100
    final_f1 = np.mean(metrics['f1'])
    final_ndcg = np.mean(metrics['ndcg'])
    final_mrr = np.mean(metrics['mrr'])
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output_text = (
        f"--- KOLLABORATÍV EVALUÁCIÓ EREDMÉNYEK ---\n"
        f"Időpont:    {current_time}\n"
        f"Minta méret: {SAMPLE_SIZE}\n"
        f"-----------------------------------------\n"
        f"Precision:  {final_precision:.2f}%\n"
        f"Recall:     {final_recall:.2f}%\n"
        f"F1-Score:   {final_f1:.4f}\n"
        f"nDCG:       {final_ndcg:.4f}\n"
        f"MRR:        {final_mrr:.4f}\n"
        f"-----------------------------------------\n"
        f"[INFO] A mérés offline kiértékeléssel, rejtett teszthalmazon történt.\n"
    )

    print(output_text)
    save_results_to_file(output_text)

if __name__ == "__main__":
    run_evaluation()