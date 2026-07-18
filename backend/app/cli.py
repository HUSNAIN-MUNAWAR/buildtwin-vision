import argparse

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_database


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("command",choices=["init-db","seed","reset-seed"]); args=parser.parse_args()
    Base.metadata.create_all(engine)
    if args.command in {"seed","reset-seed"}:
        with SessionLocal() as db: print(seed_database(db,reset=True))
    else: print("Database initialized")

if __name__=="__main__": main()
