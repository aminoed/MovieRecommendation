import csv
from movielens_db import driver

BATCH_SIZE = 1000


def batch_import_users(tx, rows):
    query = """
    UNWIND $rows AS row
    MERGE (u:User {userId: row.userId})
    """
    tx.run(query, rows=rows)


def load_users(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "userId": row["userId"]
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_users, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_users, batch)


load_users("../data/user.csv")
