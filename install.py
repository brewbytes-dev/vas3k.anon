from sqlalchemy import create_engine
from src import config
from db.model import Base


engine = create_engine(config.DATABASE_URL)

with engine.connect():
    Base.metadata.create_all(engine)
#
# conn = engine.connect()
# conn.close()
