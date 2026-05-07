import csv
from movielens_db import driver

BATCH_SIZE = 1000


def batch_import_watched(tx, rows):
    query = """
    UNWIND $rows AS row
    MATCH (u:User {userId: row.userId})
    MATCH (m:Movie {movieId: row.movieId})
    MERGE (u)-[r:WATCHED]->(m)
    SET r.rating = row.rating
    """
    tx.run(query, rows=rows)


def load_watched(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "userId": row["userId"],
                    "movieId": str(row["movieId"]),
                    "rating": float(row["rating"]) if row["rating"] else None
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_watched, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_watched, batch)


load_watched("../data/user_watched_movies.csv")
# driver.close()
