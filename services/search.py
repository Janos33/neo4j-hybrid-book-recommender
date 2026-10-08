class SearchService:
    def __init__(self, db):
        self.db = db

    #A könyv/műfaj/író keresőmezők adatait dolgozza fel

    def search_items(self, term, search_type):
        data = []
        with self.db.get_session() as session:
            
            if search_type == 'book':
                query = """
                CALL db.index.fulltext.queryNodes('bookTitleIndex', $term) YIELD node, score 
                OPTIONAL MATCH (a:Author)-[:AUTHOR_OF]->(node)
                RETURN node.book_id AS id, node.title AS label, collect(a.name) AS extra, score
                ORDER BY score DESC LIMIT 10
                """
                res = session.run(query, term=f"{term}*")
                data = [{"id": r["id"], "label": r["label"], "extra": ", ".join(r["extra"])} for r in res]
            
            elif search_type == 'genre' or search_type == 'country':
                query = """
                CALL db.index.fulltext.queryNodes('genreNameIndex', $term) YIELD node, score 
                RETURN node.tag_id AS id, node.tag_name AS label 
                ORDER BY score DESC LIMIT 10
                """
                res = session.run(query, term=f"{term}*")
                data = [{"id": r["id"], "label": r["label"]} for r in res]
                
            elif search_type == 'author':
                query = """
                CALL db.index.fulltext.queryNodes('authorNameIndex', $term) YIELD node, score 
                RETURN node.author_id AS id, node.name AS label, score 
                ORDER BY score DESC LIMIT 10
                """
                res = session.run(query, term=f"{term}*")
                data = [{"id": r["id"], "label": r["label"]} for r in res]
                 
        return data