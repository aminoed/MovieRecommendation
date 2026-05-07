import csv
from movielens_db import driver

BATCH_SIZE = 1000


def batch_import_genres(tx, rows):
    query = """
    UNWIND $rows AS row
    MERGE (g:Genre {genreId: row.genreId})
    SET g.name = row.name
    """
    tx.run(query, rows=rows)


def load_genres(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "genreId": row["genreId"],
                    "name": row["genreName"]
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_genres, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_genres, batch)


load_genres("../data/genres.csv")

