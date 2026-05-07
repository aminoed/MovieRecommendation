import csv
from movielens_db import driver

BATCH_SIZE = 1000


def batch_import_genre(tx, rows):
    query = """
    UNWIND $rows AS row
    MATCH (m:Movie {movieId: row.movieId})
    MATCH (g:Genre {genreId: row.genreId})
    MERGE (m)-[:HAS_GENRE]->(g)
    """
    tx.run(query, rows=rows)


def load_genre(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "movieId": str(row["movieId"]),
                    "genreId": row["genreId"]
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_genre, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_genre, batch)


load_genre("../data/with_genre.csv")
