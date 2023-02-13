from asyncpg import Connection


class Repo:
    def __init__(self, conn):
        self.conn: Connection = conn
