import csv
from movielens_db import driver

BATCH_SIZE = 1000


def batch_import_movies(tx, rows):
    query = """
    UNWIND $rows AS row
    MERGE (m:Movie {movieId: row.movieId})
    SET m.title = row.title
    """
    tx.run(query, rows=rows)


def load_movies(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "movieId": row["movieId"],
                    "title": row["title"]
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_movies, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_movies, batch)


load_movies("../data/movies.csv")
