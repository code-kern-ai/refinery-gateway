import os

import pytest
from submodules.model import Organization
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool


@pytest.fixture
def db_session(postgresql):
    """Session for SQLAlchemy."""
    from submodules.model.models import Base

    connection = f"postgresql+psycopg2://{postgresql.info.user}:@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"

    # overwriting for drone ci setup
    if os.getenv("DB_CONN") is not None:
        connection = os.environ["DB_CONN"]

    engine = create_engine(connection, echo=False, poolclass=NullPool)
    db = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
    Base.metadata.create_all(engine)
    yield db

    db.commit()
    Base.metadata.drop_all(engine)


@pytest.fixture
def default_setup(db_session):
    db = db_session
    db.add(Organization(name="default"))
    db.commit()
    yield db
