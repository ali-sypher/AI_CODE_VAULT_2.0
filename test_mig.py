import sqlite3
import os
from sqlalchemy import create_engine, Column, Integer, String, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# V1 Schema
class UserV1(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(50))

engine = create_engine('sqlite:///test_mig.db')
Base.metadata.create_all(engine)

# Add dummy user
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (email) VALUES ('test@test.com')"))

Base2 = declarative_base()
# V2 Schema
class UserV2(Base2):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(50))
    scan_status = Column(String(255), default='')
    scan_progress = Column(Integer, default=0)

inspector = inspect(engine)
columns = [c['name'] for c in inspector.get_columns('users')]
with engine.begin() as conn:
    if 'scan_status' not in columns:
        conn.execute(text("ALTER TABLE users ADD COLUMN scan_status VARCHAR(255) DEFAULT ''"))
    if 'scan_progress' not in columns:
        conn.execute(text("ALTER TABLE users ADD COLUMN scan_progress INTEGER DEFAULT 0"))

Session = sessionmaker(bind=engine)
session = Session()
u = session.query(UserV2).first()
print('SUCCESS! User scan_status:', u.scan_status)
if os.path.exists('test_mig.db'):
    os.remove('test_mig.db')
