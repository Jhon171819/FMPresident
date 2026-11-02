"""Índice SQLite descartável de registros observados; não identifica carreira."""
import sqlite3
import unicodedata

def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold().strip()) if not unicodedata.combining(c))

class ClubIndex:
    def __init__(self,path):
        self.db=sqlite3.connect(str(path),timeout=5)
        self.db.execute('CREATE TABLE IF NOT EXISTS clubs (pid INTEGER NOT NULL, started TEXT NOT NULL, digest TEXT NOT NULL, address INTEGER NOT NULL, uid INTEGER NOT NULL, name TEXT NOT NULL, name_key TEXT NOT NULL, PRIMARY KEY(pid,started,digest,address))')
        self.db.execute('CREATE INDEX IF NOT EXISTS clubs_name ON clubs(pid,started,digest,name_key)')
        self.db.execute('CREATE INDEX IF NOT EXISTS clubs_uid ON clubs(pid,started,digest,uid)')
        self.db.commit()
    def put(self,process,digest,options):
        rows=[(process['pid'],str(process['started']),digest,o.address,o.club.uid,o.club.name,normalize(o.club.name)) for o in options]
        with self.db:self.db.executemany('INSERT OR REPLACE INTO clubs VALUES (?,?,?,?,?,?,?)',rows)
    def find(self,process,digest,query='',limit=200):
        key=normalize(query);args=[process['pid'],str(process['started']),digest]
        where='pid=? AND started=? AND digest=?'
        if key:
            if key.isdecimal():
                if len(key)>10 or int(key)>4294967295:return []
                where+=' AND uid=?';args.append(int(key))
            else:where+=' AND name_key>=? AND name_key<?';args.extend([key,key+'\U0010ffff'])
        args.append(limit)
        return self.db.execute('SELECT address,uid,name FROM clubs WHERE '+where+' ORDER BY name_key,uid,address LIMIT ?',args).fetchall()
    def close(self):self.db.close()
