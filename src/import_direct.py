import csv
from movielens_db import driver

BATCH_SIZE = 500


def batch_import_directed(tx, rows):
    query = """
    UNWIND $rows AS row
    MATCH (p:Person {peopleId: row.peopleId})
    MATCH (m:Movie {movieId: row.movieId})
    MERGE (p)-[:DIRECTED]->(m)
    """
    tx.run(query, rows=rows)


def load_directed(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "peopleId": row["peopleId"],
                    "movieId": str(row["movieId"])
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_directed, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_directed, batch)


load_directed("../data/directed_by.csv")
