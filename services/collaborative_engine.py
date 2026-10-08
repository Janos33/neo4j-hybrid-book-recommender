import os
import pickle
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

class CollaborativeEngine:
    def __init__(self, db):
        self.db = db
        self.model_knn = NearestNeighbors(metric='cosine', algorithm='brute')
        self.book_mapper = {}
        self.book_inv_mapper = {}
        self.sparse_matrix = None
        self._is_fitted = False
        self.CACHE_PATH = "data/collab_model.pkl"



#A modell tanítása, nincs rá szükség ha van elmentett modell

    def fit(self):
        if os.path.exists(self.CACHE_PATH):
            print("COLLAB ENGINE: Found cached model. Loading from disk...")
            try:
                with open(self.CACHE_PATH, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.model_knn = cache_data['model']
                    self.sparse_matrix = cache_data['matrix']
                    self.book_mapper = cache_data['mapper']
                    self.book_inv_mapper = cache_data['inv_mapper']
                self._is_fitted = True
                print("COLLAB ENGINE: Loaded from cache.")
                return
            except Exception as e:
                print(f"COLLAB ENGINE: Cache corrupted ({e}). Rebuilding...")

        print("COLLAB ENGINE: Querying FULL ratings database...")
        query = """
        MATCH (u:User)-[r:RATED]->(b:Book)
        WHERE r.rating IS NOT NULL
        RETURN b.book_id as book_id, u.user_id as user_id, toFloat(r.rating) as rating
        """
        
        with self.db.get_session() as session:
            result = session.run(query)
            df = pd.DataFrame([r.values() for r in result], columns=['book_id', 'user_id', 'rating'])

        if df.empty:
            print("COLLAB ENGINE: No ratings found.")
            return

        print(f"COLLAB ENGINE: Processing {len(df)} ratings...")

        df['user_index'] = df['user_id'].astype('category').cat.codes
        df['book_index'] = df['book_id'].astype('category').cat.codes

        book_ids = df['book_id'].astype('category').cat.categories
        self.book_mapper = {id: i for i, id in enumerate(book_ids)}
        self.book_inv_mapper = {i: id for i, id in enumerate(book_ids)}

        num_users = df['user_index'].max() + 1
        num_books = df['book_index'].max() + 1

        self.sparse_matrix = csr_matrix(
            (df['rating'].values, (df['book_index'].values, df['user_index'].values)), 
            shape=(num_books, num_users)
        )
        
        print("COLLAB ENGINE: Fitting k-NN...")
        self.model_knn.fit(self.sparse_matrix)
        self._is_fitted = True
        
        print("COLLAB ENGINE: Saving model to disk...")
        with open(self.CACHE_PATH, 'wb') as f:
            pickle.dump({
                'model': self.model_knn,
                'matrix': self.sparse_matrix,
                'mapper': self.book_mapper,
                'inv_mapper': self.book_inv_mapper
            }, f)
        print("COLLAB ENGINE: Ready.")



#Ajánlás készítése

    def recommend(self, liked_book_ids, n=50):
        if not self._is_fitted or not liked_book_ids:
            return {}

        recommendations = {}
        valid_ids = [bid for bid in liked_book_ids if bid in self.book_mapper]
        
        if not valid_ids: return {}

        indices = [self.book_mapper[bid] for bid in valid_ids]

        distances_matrix, indices_matrix = self.model_knn.kneighbors(
            self.sparse_matrix[indices], 
            n_neighbors=n+1
        )
        
        for i, _ in enumerate(indices):
            raw_indices = indices_matrix[i]
            raw_distances = distances_matrix[i]

            for j in range(1, len(raw_indices)):
                neighbor_idx = raw_indices[j]
                neighbor_dist = raw_distances[j]
                neighbor_id = self.book_inv_mapper[neighbor_idx]
                
                if neighbor_id in liked_book_ids: continue

                similarity = 1.0 - neighbor_dist
                
                if neighbor_id in recommendations:
                    recommendations[neighbor_id] = max(recommendations[neighbor_id], similarity)
                else:
                    recommendations[neighbor_id] = similarity

        return recommendations