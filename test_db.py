from database.connection import engine

with engine.connect() as conn:
    print("Connected!")