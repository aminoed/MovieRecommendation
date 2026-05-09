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
    if not title:
        return ""

    title = title.lower()

    title = title.strip()

    title = title.encode("ascii", "ignore").decode()

    title = re.sub(r'[^a-z0-9\s]', ' ', title)

    title = re.sub(r'\s+', ' ', title)

    return title


def write_normalized_titles():
    query = """
    MATCH (m:Movie)
    RETURN id(m) AS id, m.title AS title
    """

    movies = run_query(query)

    for movie in movies:
        node_id = movie["id"]
        title = movie["title"]
        normalized = normalize_title(title)

        update_query = """
        MATCH (m)
        WHERE id(m) = $id
        SET m.normalized_title = $normalized
        """

        run_query(update_query, {"id": node_id, "normalized": normalized})


def add_relationship_weights():
    queries = [
        """
        MATCH ()-[r:WATCHED]-()
        SET r.weight = 3
        """,

        """
        MATCH ()-[r:ACTED_IN]-()
        SET r.weight = 6
        """,

        """
        MATCH ()-[r:DIRECTED]-()
        SET r.weight = 8
        """,

        """
        MATCH ()-[r:HAS_GENRE]-()
        SET r.weight = 0.5
        """
    ]

    for q in queries:
        run_query(q)


def drop_old_graph():
    query = """
    CALL gds.graph.exists('recommendation-graph')
    YIELD exists
    WITH exists
    WHERE exists
    CALL gds.graph.drop('recommendation-graph')
    YIELD graphName
    RETURN graphName
    """

    run_query(query)


def create_graph_projection():
    query = """
    CALL gds.graph.project( 'recommendation-graph',
      ['User', 'Movie', 'Person', 'Genre'],
      {
        WATCHED: { orientation: 'UNDIRECTED', properties: 'weight'},
        ACTED_IN: { orientation: 'UNDIRECTED', properties: 'weight'},
        DIRECTED: { orientation: 'UNDIRECTED', properties: 'weight'},
        HAS_GENRE: { orientation: 'UNDIRECTED', properties: 'weight'}
      }
    )
    """

    run_query(query)


def run_fastrp():
    query = """
    CALL gds.fastRP.mutate(
      'recommendation-graph',
      {
        embeddingDimension: 256,
        randomSeed: 42,
        mutateProperty: 'embedding',
        relationshipWeightProperty: 'weight',
        iterationWeights: [1.0, 1.0, 0.5],
        normalizationStrength: 0.8
      }
    )
    """

    run_query(query)


def run_knn():
    query = """
    CALL gds.knn.write(
      'recommendation-graph',
      {
        nodeProperties: ['embedding'],
        topK: 50,
        sampleRate: 1.0,
        deltaThreshold: 0.0,
        randomSeed: 42,
        concurrency: 1,
        writeRelationshipType: 'SIMILAR',
        writeProperty: 'score'
      }
    )
    """
    run_query(query)


def get_user_watched_movies(user_Id):
    query = """
    MATCH (u:User {userId: $user})-[:WATCHED]->(m:Movie)
    RETURN collect(m.normalized_title) AS watched
    """

    result = run_query(query, {"user": user_Id})

    if result:
        return set(result[0]["watched"])

    return set()


def get_similar_movies(movie_title, limit=100):
    normalized = normalize_title(movie_title)

    query = """
    MATCH (m:Movie)
    WHERE m.normalized_title = $title
    MATCH (m)-[s:SIMILAR]->(rec:Movie)
    RETURN
        rec.title AS movie,
        s.score AS score

    ORDER BY score DESC
    LIMIT $limit
    """

    return run_query(query, {"title": normalized, "limit": limit})


def get_actor_candidates(movie_title, min_shared=2):
    query = """
    MATCH (m1:Movie)
    WHERE m1.normalized_title = $movie1
    MATCH (m1)<-[:ACTED_IN]-(p:Person)-[:ACTED_IN]->(m2:Movie)
    WHERE m1 <> m2
    WITH
        m2,
        count(DISTINCT p) AS sharedCount
    WHERE sharedCount >= $min_shared
    RETURN
        m2.title AS movie,
        sharedCount AS score
    ORDER BY score DESC
    LIMIT 100
    """

    return run_query(query, {
        "movie1": normalize_title(movie_title),
        "min_shared": min_shared
    })


def get_director_candidates(movie_title):
    query = """
    MATCH (m1:Movie)
    WHERE m1.normalized_title = $movie1
    MATCH (m1)<-[:DIRECTED]-(d:Person)-[:DIRECTED]->(m2:Movie)
    WHERE m1 <> m2
    RETURN
        m2.title AS movie,
        count(DISTINCT d) AS score
    ORDER BY score DESC
    LIMIT 100
    """

    return run_query(query, {"movie1": normalize_title(movie_title)})


def get_genre_candidates(movie_title, min_shared=2):
    query = """
    MATCH (m1:Movie)
    WHERE m1.normalized_title = $movie1
    MATCH (m1)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(m2:Movie)
    WHERE m1 <> m2
    WITH
        m2,
        count(DISTINCT g) AS sharedGenres
    WHERE sharedGenres >= $min_shared
    RETURN
        m2.title AS movie,
        sharedGenres AS score
    ORDER BY score DESC
    LIMIT 100
    """

    return run_query(query, {
        "movie1": normalize_title(movie_title),
        "min_shared": min_shared
    })


def get_collaborative_candidates(movie_title):
    query = """
    MATCH (target:Movie)
    WHERE target.normalized_title = $movie1
    MATCH (u:User)-[:WATCHED]->(target)
    MATCH (u)-[:WATCHED]->(rec:Movie)
    WHERE rec <> target
    RETURN
        rec.title AS movie,
        count(DISTINCT u) AS score
    ORDER BY score DESC
    LIMIT 100
    """

    return run_query(query, {"movie1": normalize_title(movie_title)})


def get_shared_actors(movie1, movie2):
    query = """
    MATCH (m1:Movie) WHERE m1.normalized_title = $movie1
    MATCH (m2:Movie) WHERE m2.normalized_title = $movie2

    MATCH (m1)<-[:ACTED_IN]-(p:Person)-[:ACTED_IN]->(m2)
    RETURN collect(DISTINCT p.name)[0..5] AS actors
    """

    result = run_query(query, {
        "movie1": normalize_title(movie1),
        "movie2": normalize_title(movie2)
    })

    return result[0]["actors"] if result else []


def get_shared_directors(movie1, movie2):
    query = """
    MATCH (m1:Movie) WHERE m1.normalized_title = $movie1
    MATCH (m2:Movie) WHERE m2.normalized_title = $movie2

    MATCH (m1)<-[:DIRECTED]-(d:Person)-[:DIRECTED]->(m2)
    RETURN collect(DISTINCT d.name) AS directors
    """

    result = run_query(query, {
        "movie1": normalize_title(movie1),
        "movie2": normalize_title(movie2)
    })

    return result[0]["directors"] if result else []


def get_shared_genres(movie1, movie2):
    query = """
    MATCH (m1:Movie) WHERE m1.normalized_title = $movie1
    MATCH (m2:Movie) WHERE m2.normalized_title = $movie2

    MATCH (m1)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(m2)
    RETURN collect(DISTINCT g.name) AS genres
    """

    result = run_query(query, {
        "movie1": normalize_title(movie1),
        "movie2": normalize_title(movie2)
    })

    return result[0]["genres"] if result else []


def get_franchise_bonus(movie1, movie2):
    words1 = set(normalize_title(movie1).split())
    words2 = set(normalize_title(movie2).split())

    stopwords = {"the", "a", "an", "part", "episode", "movie", "film"}

    words1 = words1 - stopwords
    words2 = words2 - stopwords

    overlap = len(words1.intersection(words2))

    if overlap >= 3:
        return 4

    elif overlap >= 2:
        return 2

    elif overlap >= 1:
        return 0.5

    return 0


def recommend_movie_for_user(user_Id, movie_title):
    watched_movies = get_user_watched_movies(user_Id)

    embedding_candidates = get_similar_movies(movie_title)
    actor_candidates = get_actor_candidates(movie_title)
    director_candidates = get_director_candidates(movie_title)
    genre_candidates = get_genre_candidates(movie_title)
    collaborative_candidates = get_collaborative_candidates(movie_title)

    candidates = {}

    def init_candidate(title):
        normalized = normalize_title(title)
        if normalized not in candidates:
            candidates[normalized] = {
                "movie_title": title,
                "embedding_score": 0,
                "actor_score": 0,
                "director_score": 0,
                "genre_score": 0,
                "collab_score": 0
            }

        return normalized

    for rec in embedding_candidates:
        normalized = init_candidate(rec["movie"])
        candidates[normalized]["embedding_score"] = rec["score"]

    for rec in actor_candidates:
        normalized = init_candidate(rec["movie"])
        candidates[normalized]["actor_score"] = rec["score"]

    for rec in director_candidates:
        normalized = init_candidate(rec["movie"])
        candidates[normalized]["director_score"] = rec["score"]

    for rec in genre_candidates:
        normalized = init_candidate(rec["movie"])
        candidates[normalized]["genre_score"] = rec["score"]

    for rec in collaborative_candidates:
        normalized = init_candidate(rec["movie"])
        candidates[normalized]["collab_score"] = rec["score"]

    final_results = []

    for normalized_title, scores in candidates.items():

        if normalized_title in watched_movies:
            continue
        title = scores["movie_title"]

        actors = get_shared_actors(movie_title, title)
        directors = get_shared_directors(movie_title, title)
        genres = get_shared_genres(movie_title, title)

        actor_component = min(scores["actor_score"] / 4, 1.0)
        director_component = 1 if (scores["director_score"] > 0) else 0
        collab_component = min(scores["collab_score"] / 15, 1.0)
        genre_component = min(scores["genre_score"] / 3, 1.0)
        embedding_component = scores["embedding_score"]

        actor_bonus, user_bonus = 0, 0
        if scores["actor_score"] >= 10:
            actor_bonus += 4

        elif scores["actor_score"] >= 5:
            actor_bonus += 2

        elif scores["actor_score"] >= 3:
            actor_bonus += 1

        if scores["collab_score"] >= 35:
            user_bonus += 4

        elif scores["collab_score"] >= 10:
            user_bonus += 3

        elif scores["collab_score"] >= 8:
            user_bonus += 2

        elif scores["collab_score"] >= 1:
            user_bonus += 1

        franchise_bonus = get_franchise_bonus(movie_title, title)

        base_score = actor_component * 5 + director_component * 4 + collab_component * 3 + embedding_component * 2 + genre_component * 1

        base_score = base_score * (10 / 15)

        final_score = base_score + actor_bonus + user_bonus + franchise_bonus

        explanation = []

        if franchise_bonus:
            explanation.append("It's the same franchise")

        if user_bonus:
            explanation.append(f"{scores['collab_score']} similar users also watched this movie")

        if actors:
            explanation.append(f"Shared actors: {', '.join(actors)}")

        if directors:
            explanation.append(f"Shared directors: {', '.join(directors)}")

        if genres:
            explanation.append(f"Shared genres: {', '.join(genres)}")

        final_results.append({
            "recommended_movie": title,

            "shared_actor_count": scores["actor_score"],
            "shared_director_count": scores["director_score"],
            "shared_genre_count": scores["genre_score"],
            "shared_user_count": scores["collab_score"],

            "base_score": round(base_score, 4),
            "embedding_score": round(scores["embedding_score"], 4),

            "franchise_bonus": franchise_bonus,
            "actor_bonus": actor_bonus,
            "collab_bonus": user_bonus,

            "final_score": round(final_score, 4),

            "explanation": explanation
        })

    final_results = sorted(final_results, key=lambda x: x["final_score"], reverse=True)

    return final_results[:5]


def test_recommendation(user_Id, movie_title):
    print(f"\n======Start to recommend for USER: {user_Id}, {user_Id} has watched movie: {movie_title}")
    print("======So, what do you have?\n\n\n")

    results = recommend_movie_for_user(user_Id, movie_title)

    print("======Hello, the top 5 recommendation is shown below:")
    i = 1
    for r in results:
        print(f"\n------Option {i}:", r["recommended_movie"])

        # print("Shared Actors:", r["shared_actor_count"] )
        # print("Shared Directors:", r["shared_director_count"])
        # print("Shared Genres:", r["shared_genre_count"])
        # print("Shared Users:", r["shared_user_count"])
        print("Score break down as below: ")
        print("\tBase Score:", r["base_score"], "/ 10")
        print("\tBonus Score:", r["franchise_bonus"] + r["actor_bonus"] + r["collab_bonus"])
        if r["franchise_bonus"]:
            print("\t\tFranchise Bonus:", r["franchise_bonus"], "/ 4")
        if r["actor_bonus"]:
            print("\t\tSame Actor Bonus:", r["actor_bonus"], "/ 4")
        if r["collab_bonus"]:
            print("\t\tCollaborative Filtering Bonus:", r["collab_bonus"], "/ 4")

        print("\tEmbedding Score:", r["embedding_score"], "/ 1")
        print("\tFinal Score:", r["final_score"])

        print("\nRecommend Reason:")

        for e in r["explanation"]:
            print("-", e)
        i = i + 1


# write_normalized_titles()

# add_relationship_weights()
#
# drop_old_graph()
#
# create_graph_projection()
#
# run_fastrp()
#
# run_knn()

test_recommendation("u_527", "Star Trek: The Motion Picture")
