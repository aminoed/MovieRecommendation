import csv
from movielens_db import driver

BATCH_SIZE = 500


def batch_import_people(tx, rows):
    query = """
        UNWIND $rows AS row
        MERGE (p:Person {peopleId: row.peopleId})
        SET p.name = row.name,
            p.birthdate = CASE 
                WHEN row.birthdate IS NOT NULL AND row.birthdate <> "" 
                THEN date(row.birthdate) 
                ELSE NULL 
            END
        """
    tx.run(query, rows=rows)


def load_people(file_path):
    batch = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        with driver.session() as session:
            for row in reader:
                batch.append({
                    "peopleId": row["peopleId"],
                    "name": row["personName"],
                    "birthdate": row["personBirthdate"]
                })

                if len(batch) == BATCH_SIZE:
                    session.execute_write(batch_import_people, batch)
                    batch = []

            if batch:
                session.execute_write(batch_import_people, batch)
                print("===one batch===")


load_people("../data/people.csv")
