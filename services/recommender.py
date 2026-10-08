from .builders import QueryBuilder

class RecommenderService:
    def __init__(self, db, vector_engine, collab_engine):
        self.db = db
        self.vector_engine = vector_engine
        self.collab_engine = collab_engine

    def get_recommendations(self, constraints, prefs=None, settings=None):
        
        # Alapbeállítások ha még semmi sincs megadva
        if not settings: settings = {}
        min_rating = settings.get('min_rating', 0.0)
        randomness = settings.get('randomness', 0.1)
        limit_count = settings.get('limit', 35)



        # --- A KÖNYVEK SZŰRÉSE A MEGKÖTÉSEK ÉS KIZÁRÁSOK ALAPJÁN ---


        filters = ["b.title IS NOT NULL"] 
        
        # Megkötések (minimum értékelés, korcsoport, korszak, írók, műfajok)

        if min_rating > 0:
            filters.append(f"toFloat(b.average_rating) >= {min_rating}")

        if constraints.get('age', {}).get('active'):
            q = QueryBuilder.build_age_query(constraints['age'].get('values', []))
            if q: filters.append(q)
            
        if constraints.get('period', {}).get('active'):
            q = QueryBuilder.build_period_query(constraints['period']) 
            if q: filters.append(q)

        if constraints.get('authors', {}).get('active'):
            filters.append("EXISTS { MATCH (a:Author)-[:AUTHOR_OF]->(b) WHERE a.author_id IN $const_authors }")

        if constraints.get('genres', {}).get('active'):
             filters.append("EXISTS { MATCH (b)-[:HAS_TAG]->(t:Tag) WHERE t.tag_id IN $const_genres }")



        # Kizárások (írók és műfajok)
        
        if constraints.get('excluded_authors', {}).get('active'):
            filters.append("NOT EXISTS { MATCH (a:Author)-[:AUTHOR_OF]->(b) WHERE a.author_id IN $excl_authors }")
        
        if constraints.get('excluded_genres', {}).get('active'):
            filters.append("NOT EXISTS { MATCH (b)-[:HAS_TAG]->(t:Tag) WHERE t.tag_id IN $excl_genres }")

        where_clause = " AND ".join(filters)



        # --- KÖNYVEK COLLABORATIVE/CONTENT BASED PONTSZÁMAINAK KISZÁMÍTÁSA ---

        liked_books = prefs.get('books', {}).get('values', [])
        
        vector_scores = {}
        if liked_books and prefs.get('books', {}).get('weight_content', 0) > 0:
            vector_scores = self.vector_engine.recommend(liked_books, n=100)

        collab_scores = {}
        if liked_books and prefs.get('books', {}).get('weight_collab', 0) > 0:
            collab_scores = self.collab_engine.recommend(liked_books, n=100)




        # --- AZ AJÁNLÁSÉRT FELELŐS QUERY ELKÉSZÍTÉSE ---


        query = f"""
        MATCH (b:Book)
        WHERE {where_clause}
        



        // 1. A "népszerűségi pontszám" kiszámítása az értékelések, és az értékelések száma alapján.
        
        WITH b, 
             toFloat(coalesce(b.average_rating, 0.0)) AS rating,
             toInteger(coalesce(b.ratings_count, 0)) AS reviews
        WITH b, rating * log10(reviews + 1) AS popularity_score
        


        // 2. Annak ellenőrzése hogy a könyv műfaja/írója egyezik-e a felhasználó által közvetlenül megadott preferenciákkal
        
        OPTIONAL MATCH (b)-[:HAS_TAG]->(st:Tag)
        WHERE st.tag_id IN $pref_genres
        WITH b, popularity_score, count(DISTINCT st) AS genre_matches
        
        OPTIONAL MATCH (a:Author)-[:AUTHOR_OF]->(b)
        WITH b, popularity_score, genre_matches, collect(a.name) as author_names, collect(a.author_id) as author_ids

        


        // 3. A content based és collaborative pontszámok átadása

        WITH b, popularity_score, genre_matches, author_names, author_ids,
         
         // CHANGE THIS:
         // CASE WHEN $vector_map[b.book_id] IS NOT NULL ...
         
         // TO THIS (Add toString):
         CASE WHEN $vector_map[toString(b.book_id)] IS NOT NULL 
              THEN $vector_map[toString(b.book_id)] ELSE 0.0 END AS vsm_score,
              
         // AND THIS:
         CASE WHEN $collab_map[toString(b.book_id)] IS NOT NULL 
              THEN $collab_map[toString(b.book_id)] ELSE 0.0 END AS cf_score

              

        // 4. A könyvek végső ponszámainak kiszámítása

        WITH b, author_names, popularity_score,
             (genre_matches * $w_genre) +
             (size([x IN author_ids WHERE x IN $pref_authors]) * $w_author) +
             (vsm_score * $w_content) +   
             (cf_score * $w_collab)       
             AS personal_score
             


             

        // 5. A végső sorrend eldöntése, majd a top x könyv átadása
        //Adat hiányában global relevance alapján dönti el a sorrendet
        //Felhasználói kérésre noise hozzáadása a végső pontszámhoz az újszerű eredmények érdekében


        WITH b, author_names, personal_score, popularity_score,
             (rand() * $random_weight) AS noise,
             CASE 
                WHEN personal_score = 0 THEN popularity_score 
                ELSE personal_score + (popularity_score * 0.01) 
             END as final_score
        
        ORDER BY (final_score + noise) DESC
        LIMIT $limit_count
        RETURN b.title as title, author_names as authors, final_score as score
        """
        
        params = {
            "const_authors": constraints.get('authors', {}).get('values', []),
            "const_genres": constraints.get('genres', {}).get('values', []),
            "excl_authors": constraints.get('excluded_authors', {}).get('values', []),
            "excl_genres": constraints.get('excluded_genres', {}).get('values', []),
            
            "pref_genres": prefs.get('genres', {}).get('values', []),
            "pref_authors": prefs.get('authors', {}).get('values', []),
            
            "vector_map": {str(k): v for k, v in vector_scores.items()},
            "collab_map": {str(k): v for k, v in collab_scores.items()},
            
            "w_genre": prefs.get('genres', {}).get('weight', 0),
            "w_author": prefs.get('authors', {}).get('weight', 0),
            "w_content": prefs.get('books', {}).get('weight_content', 0),
            "w_collab": prefs.get('books', {}).get('weight_collab', 0),
            
            "random_weight": randomness,
            "limit_count": limit_count
        }

        with self.db.get_session() as session:
            result = session.run(query, **params)
            return [{"title": r["title"], "authors": ", ".join(r["authors"]), "score": round(r["score"], 2)} for r in result]