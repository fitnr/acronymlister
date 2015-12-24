import sys
from acrobot import Acrobot

def main(db):
    '''Init the acrobot by downloading AAA'''
    A = Acrobot(db)
    curs = A.conn.execute("SELECT COUNT(*) FROM acronyms WHERE acronym='AAA'")
    result = curs.fetchone()

    if result[0] == 0:
        print("fetching AAA")
        A.get_acronyms('AAA')
    else:
        print("not fetching AAA")

if __name__ == '__main__':
    main(sys.argv[1])
