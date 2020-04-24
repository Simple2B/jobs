""" Sqlalchemy session fabrics and engines for DB.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from threading import Lock

g_lock = Lock()

db_engine = create_engine('sqlite:///simple2b_jobs.db')

DbSession = sessionmaker(bind=db_engine)

@contextmanager
def db_session_ctx(read_only=False):
    global g_lock
    g_lock.acquire()
    session = DbSession()
    if read_only:
        try:
            yield session
        finally:
            session.close()
            g_lock.release()
    else:
        try:
            yield session
            session.commit()
        except (Exception):
            session.rollback()
            raise
        finally:
            session.close()
            g_lock.release()
