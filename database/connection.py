from sqlalchemy import create_engine


DATABASE_URL = (
    "postgresql+psycopg2://"
    "morpho:morpho@localhost:5433/morpho"
)

engine = create_engine(DATABASE_URL)