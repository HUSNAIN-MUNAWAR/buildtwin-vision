from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_database
Base.metadata.create_all(engine)
with SessionLocal() as db:
    print(seed_database(db, reset=True))
