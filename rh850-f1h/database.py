#https://github.com/raelize/TAoFI-FaultLib/blob/main/RaelizeFaultLib.py

import os
import time
import sys
import sqlite3
import datetime


class Database():
    def __init__(self, argv, extra_params=['delay', 'length']):
        script_name = os.path.basename(sys.argv[0])
        self.dbname = f"{script_name}_%s.sqlite" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if os.path.isdir('databases') == False:
            os.mkdir("databases")

        self.con = sqlite3.connect("databases/" + self.dbname)
        self.cur = self.con.cursor()
        self.argv = argv

        statement = "CREATE TABLE experiments(id integer, color text, response blob,"
        for p in extra_params:
            if p == 'voltage':
                statement += f"{p} real,"
            else:
                statement += f"{p} integer,"

        statement = statement.rstrip(',')  # Remove trailing comma
        statement += ")"
        print(statement)

        self.cur.execute(statement)
        self.cur.execute("CREATE TABLE metadata (stime_seconds integer, argv blob)")


    def insert(self, experiment_id, **params):
        if experiment_id == 0:
            s_argv = ' '.join(self.argv[1:])
            self.cur.execute("INSERT INTO metadata (stime_seconds,argv) VALUES (?,?)", [int(time.time()), s_argv])

        to_insert = {
            'id': experiment_id,
        }
        to_insert.update(params)

        statement = "INSERT INTO experiments ("
        statement += ','.join(to_insert.keys())
        statement += ") VALUES ("
        statement += ','.join(['?'] * len(to_insert))
        statement += ")"

        self.cur.execute(statement, list(to_insert.values()))
        self.con.commit()

    def close(self):
        self.con.close()


def query(fn, query):
    con = sqlite3.connect(fn)
    con.row_factory = sqlite3.Row
    cur = con.cursor()


    results = cur.execute(query)
    # print(results.description)
    results = results.fetchall()

    con.close()
    return results
