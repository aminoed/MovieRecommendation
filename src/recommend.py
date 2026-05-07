import re

from neo4j import GraphDatabase

URI = "neo4j://127.0.0.1:7687"
USER = "neo4j"
PASSWORD = "12345678"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def run_query(query, parameters=None):
    with driver.session() as session:
        result = session.run(query, parameters)
        return [record.data() for record in result]


def normalize_title(title):

    title = title.lower()

    title = title.strip()

    title = title.replace('"', '')

    title = re.sub(r'[^a-z0-9\s]', ' ', title)

    title = re.sub(r'\s+', ' ', title)

    return title


def get_similar_movies(movie_title, limit=5):
    query = """
    MATCH (m:Movie {title: $title})-[s:SIMILAR]->(rec:Movie)
    RETURN rec.title AS movie, s.score AS score
    ORDER BY score DESC
    LIMIT $limit
    """

    return run_query(query, {
        "title": movie_title,
        "limit": limit
    })


def get_shared_actors(movie1, movie2):
    query = """
    MATCH (m1:Movie {title: $movie1})<-[:ACTED_IN]-(p:Person)-[:ACTED_IN]->(m2:Movie {title: $movie2})
    RETURN collect(DISTINCT p.name)[0..5] AS actors
    """

    result = run_query(query, {
        "movie1": movie1,
        "movie2": movie2
    })

    return result[0]["actors"] if result else []


def get_shared_directors(movie1, movie2):
    query = """
    MATCH (m1:Movie {title: $movie1})<-[:DIRECTED]-(d:Person)-[:DIRECTED]->(m2:Movie {title: $movie2})
    RETURN collect(DISTINCT d.name) AS directors
    """

    result = run_query(query, {
        "movie1": movie1,
        "movie2": movie2
    })

    return result[0]["directors"] if result else []


def get_shared_genres(movie1, movie2):
    query = """
    MATCH (m1:Movie {title: $movie1})-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(m2:Movie {title: $movie2})
    RETURN collect(DISTINCT g.name) AS genres
    """

    result = run_query(query, {
        "movie1": movie1,
        "movie2": movie2
    })

    return result[0]["genres"] if result else []


def recommend_movie(movie_title):
    recommendations = get_similar_movies(movie_title)

    final_results = []

    for rec in recommendations:

        rec_title = rec["movie"]
        score = rec["score"]

        actors = get_shared_actors(movie_title, rec_title)
        directors = get_shared_directors(movie_title, rec_title)
        genres = get_shared_genres(movie_title, rec_title)

        explanation = []

        if actors:
            explanation.append(
                f"Shared actors: {', '.join(actors)}"
            )

        if directors:
            explanation.append(
                f"Shared directors: {', '.join(directors)}"
            )

        if genres:
            explanation.append(
                f"Shared genres: {', '.join(genres)}"
            )

        final_results.append({
            "recommended_movie": rec_title,
            "similarity_score": round(score, 4),
            "explanation": explanation
        })

    return final_results


results = recommend_movie("Star Wars")

for r in results:

    print("\n====================")
    print("Recommended Movie:", r["recommended_movie"])
    print("Similarity Score:", r["similarity_score"])

    print("Why Recommended?")

    for e in r["explanation"]:
        print("-", e)
