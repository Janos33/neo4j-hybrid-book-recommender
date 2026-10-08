import os
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class VectorEngine:
    def __init__(self, db):
        self.db = db
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self.book_ids = []
        self.book_indices = {}
        self._is_fitted = False
        self.CACHE_PATH = "data/vector_model.pkl"



#A modell tanítása, nincs rá szükség ha van elmentett modell

    def fit(self):
        if os.path.exists(self.CACHE_PATH):
            print("VECTOR ENGINE: Found cached model. Loading from disk...")
            try:
                with open(self.CACHE_PATH, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.tfidf_matrix = cache_data['matrix']
                    self.vectorizer = cache_data['vectorizer']
                    self.book_ids = cache_data['ids']
                    self.book_indices = cache_data['indices']
                self._is_fitted = True
                print(f"VECTOR ENGINE: Loaded {len(self.book_ids)} books from cache.")
                return
            except Exception as e:
                print(f"VECTOR ENGINE: Cache corrupted ({e}). Rebuilding...")

        print("VECTOR ENGINE: Querying FULL database...")
        query = """
        MATCH (b:Book)
        WHERE b.title IS NOT NULL
        OPTIONAL MATCH (b)-[:HAS_TAG]->(t:Tag)
        WITH b, collect(t.tag_name) as tags
        OPTIONAL MATCH (a:Author)-[:AUTHOR_OF]->(b)
        WITH b, tags, collect(a.name) as authors
        RETURN b.book_id as id, 
               reduce(s = "", x IN tags | s + x + " ") + 
               reduce(s = "", x IN authors | s + x + " ") + 
               b.title as content_soup
        """
        
        with self.db.get_session() as session:
            result = session.run(query)
            data = [record for record in result]

        if not data:
            print("VECTOR ENGINE: No books found.")
            return

        self.book_ids = [r['id'] for r in data]
        self.book_indices = {r['id']: i for i, r in enumerate(data)}
        corpus = [r['content_soup'] for r in data]

        print(f"VECTOR ENGINE: Vectorizing {len(corpus)} books...")
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self._is_fitted = True
        
        print("VECTOR ENGINE: Saving model to disk...")
        with open(self.CACHE_PATH, 'wb') as f:
            pickle.dump({
                'matrix': self.tfidf_matrix,
                'vectorizer': self.vectorizer,
                'ids': self.book_ids,
                'indices': self.book_indices
            }, f)
        print("VECTOR ENGINE: Ready.")


#Ajánlás készítése

    def recommend(self, liked_book_ids, n=50):
        if not self._is_fitted or not liked_book_ids:
            return {}

        valid_indices = [self.book_indices[bid] for bid in liked_book_ids if bid in self.book_indices]
        if not valid_indices: return {}

        user_vector = np.mean(self.tfidf_matrix[valid_indices], axis=0)
        
        cosine_scores = cosine_similarity(np.asarray(user_vector), self.tfidf_matrix).flatten()
        top_indices = cosine_scores.argsort()[-n:][::-1]

        recommendations = {}
        for idx in top_indices:
            book_id = self.book_ids[idx]
            if book_id in liked_book_ids: continue
            recommendations[book_id] = float(cosine_scores[idx])

        return recommendations