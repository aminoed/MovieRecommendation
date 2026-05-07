# from graphdatascience import GraphDataScience
from neo4j import GraphDatabase
import csv

URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")

driver = GraphDatabase.driver(URI, auth=AUTH)


# def close():
#     driver.close()
#     print("=====database closed!=====")


# def test_connection():
#     with driver.session() as session:
#         result = session.run("RETURN 'Hello Neo4j' AS msg")
#         for record in result:
#             print(record["msg"])
#
#
# if __name__ == "__main__":
#     test_connection()
#     driver.close()
def run_query(query):
    with driver.session() as session:
        result = session.run(query)
        return [record.data() for record in result]


print(run_query("""
MATCH (u:User)-[:WATCHED]->(m:Movie)

RETURN
    COUNT(DISTINCT u) AS users,
    COUNT(DISTINCT m) AS movies,
    COUNT(*) AS interactions
"""))
print(run_query("""
MATCH (u:User)-[:WATCHED]->(m:Movie)

WHERE toLower(m.title) CONTAINS "star wars"

RETURN
    COUNT(DISTINCT u) AS users
"""))
# run_query("""
# CALL gds.knn.write('movieGraph', {
#   nodeLabels: ['Movie'],
#   nodeProperties: ['embedding'],
#   topK: 10,
#   randomSeed: 42,
#   concurrency: 1,
#   sampleRate: 1.0,
#   deltaThreshold: 0.0,
#   writeRelationshipType: 'SIMILAR',
#   writeProperty: 'score'
# })
# """)
#
# print(run_query("""
# MATCH ()-[r:SIMILAR]->()
# RETURN COUNT(r) AS count
# """))

# print(run_query("""
# MATCH (u:User {userId: "u_1"})-[:WATCHED]->(m:Movie)
# MATCH (m)-[s:SIMILAR]->(rec:Movie)
# WHERE NOT (u)-[:WATCHED]->(rec)
#
# RETURN
#     u.userId AS user,
#     m.title AS watched,
#     rec.title AS recommended,
#     s.score AS similarity
# LIMIT 50
# """))
