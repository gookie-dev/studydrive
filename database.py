from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    file = Column(Boolean, default=None)
    preview = Column(Boolean, default=None)
    title = Column(String)
    user = Column(String)
    description = Column(String)
    course = Column(String)
    date = Column(String)
    pages = Column(Integer)
    type = Column(String)
    cached = Column(String, default="Not cached")
    file_name = Column(String)


class Counter(Base):
    __tablename__ = 'counters'

    id = Column(String, primary_key=True)
    count = Column(Integer, default=0)


class Download(Base):
    __tablename__ = 'downloads'

    id = Column(String, primary_key=True)
    document_id = Column(Integer, nullable=False)
    expires = Column(Integer, nullable=False)


def create_session():
    engine = create_engine('sqlite:///studydrive.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    session = create_session()
    session.close()


init_db()