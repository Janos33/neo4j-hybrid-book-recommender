from neo4j import GraphDatabase

class Database:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def get_session(self):
        return self.driver.session()