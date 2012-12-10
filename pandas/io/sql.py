"""
Collection of query wrappers / abstractions to both facilitate data
retrieval and to reduce dependency on DB-specific API.
"""
from datetime import datetime, date

import numpy as np
import traceback

from pandas.core.datetools import format as date_format
from pandas.core.api import DataFrame, isnull

#------------------------------------------------------------------------------
# Helper execution function


def execute(sql, con, retry=True, cur=None, params=None):
    """
    Execute the given SQL query using the provided connection object.

    Parameters
    ----------
    sql: string
        Query to be executed

    Returns
    -------
    Cursor object
    """
    try:
        if cur is None:
            cur = con.cursor()

        if params is None:
            cur.execute(sql)
        else:
            cur.execute(sql, params)
        return cur
    except Exception:
        try:
            con.rollback()
        except Exception:  # pragma: no cover
            pass

        print 'Error on sql %s' % sql
        raise


def _safe_fetch(cur):
    try:
        result = cur.fetchall()
        if not isinstance(result, list):
            result = list(result)
        return result
    except Exception, e:  # pragma: no cover
        excName = e.__class__.__name__
        if excName == 'OperationalError':
            return []


def tquery(sql, con=None, cur=None, retry=True):
    """
    Returns list of tuples corresponding to each row in given sql
    query.

    If only one column selected, then plain list is returned.

    Parameters
    ----------
    sql: string
        SQL query to be executed
    con: SQLConnection or DB API 2.0-compliant connection
    cur: DB API 2.0 cursor

    Provide a specific connection or a specific cursor if you are executing a
    lot of sequential statements and want to commit outside.
    """
    cur = execute(sql, con, cur=cur)
    result = _safe_fetch(cur)

    if con is not None:
        try:
            cur.close()
            con.commit()
        except Exception, e:
            excName = e.__class__.__name__
            if excName == 'OperationalError':  # pragma: no cover
                print 'Failed to commit, may need to restart interpreter'
            else:
                raise

            traceback.print_exc()
            if retry:
                return tquery(sql, con=con, retry=False)

    if result and len(result[0]) == 1:
        # python 3 compat
        result = list(list(zip(*result))[0])
    elif result is None:  # pragma: no cover
        result = []

    return result


def uquery(sql, con=None, cur=None, retry=True, params=()):
    """
    Does the same thing as tquery, but instead of returning results, it
    returns the number of rows affected.  Good for update queries.
    """
    cur = execute(sql, con, cur=cur, retry=retry, params=params)

    result = cur.rowcount
    try:
        con.commit()
    except Exception, e:
        excName = e.__class__.__name__
        if excName != 'OperationalError':
            raise

        traceback.print_exc()
        if retry:
            print 'Looks like your connection failed, reconnecting...'
            return uquery(sql, con, retry=False)
    return result


def read_frame(sql, con, index_col=None, coerce_float=True):
    """
    Returns a DataFrame corresponding to the result set of the query
    string.

    Optionally provide an index_col parameter to use one of the
    columns as the index. Otherwise will be 0 to len(results) - 1.

    Parameters
    ----------
    sql: string
        SQL query to be executed
    con: DB connection object, optional
    index_col: string, optional
        column name to use for the returned DataFrame object.
    """
    cur = execute(sql, con)
    rows = _safe_fetch(cur)
    columns = [col_desc[0] for col_desc in cur.description]

    cur.close()
    con.commit()

    result = DataFrame.from_records(rows, columns=columns,
                                    coerce_float=coerce_float)

    if index_col is not None:
        result = result.set_index(index_col)

    return result

frame_query = read_frame


def write_frame(frame, name, con, flavor='sqlite', if_exists='fail', **kwargs):
    """
    Write records stored in a DataFrame to a SQL database.

    Parameters
    ----------
    frame: DataFrame
    name: name of SQL table
    conn: an open SQL database connection object
    flavor: {'sqlite', 'mysql', 'oracle'}, default 'sqlite'
    if_exists: {'fail', 'replace', 'append'}, default 'fail'
        fail: If table exists, do nothing.
        replace: If table exists, drop it, recreate it, and insert data.
        append: If table exists, insert data. Create if does not exist.
    """

    if 'append' in kwargs:
        import warnings
        warnings.warn("append is deprecated, use if_exists instead",
                      FutureWarning)
        if kwargs['append']:
            if_exists='append'
        else:
            if_exists='fail'
    exists = table_exists(name, con, flavor)
    if if_exists == 'fail' and exists:
        raise ValueError, "Table '%s' already exists." % name

    #create or drop-recreate if necessary
    create = None
    if exists and if_exists == 'replace':
        create = "DROP TABLE %s" % name
    elif not exists:
        create = get_schema(frame, name, flavor)

    if create is not None:
        cur = con.cursor()
        cur.execute(create)
        cur.close()

    cur = con.cursor()
    # Replace spaces in DataFrame column names with _.
    safe_names = [s.replace(' ', '_').strip() for s in frame.columns]
    flavor_picker = {'sqlite' : _write_sqlite,
                     'mysql' : _write_mysql}

    func = flavor_picker.get(flavor, None)
    if func is None:
        raise NotImplementedError
    func(frame, name, safe_names, cur)
    cur.close()
    con.commit()

def _write_sqlite(frame, table, names, cur):
    bracketed_names = ['[' + column + ']' for column in names]
    col_names = ','.join(bracketed_names)
    wildcards = ','.join(['?'] * len(names))
    insert_query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table, col_names, wildcards)
    data = [tuple(x) for x in frame.values]
    cur.executemany(insert_query, data)

def _write_mysql(frame, table, names, cur):
    bracketed_names = ['`' + column + '`' for column in names]
    col_names = ','.join(bracketed_names)
    wildcards = ','.join([r'%s'] * len(names))
    insert_query = "INSERT INTO %s (%s) VALUES (%s)" % (
        table, col_names, wildcards)
    data = [tuple(x) for x in frame.values]
    cur.executemany(insert_query, data)

def table_exists(name, con, flavor):
    flavor_map = {
        'sqlite': ("SELECT name FROM sqlite_master "
                   "WHERE type='table' AND name='%s';") % name,
        'mysql' : "SHOW TABLES LIKE '%s'" % name}
    query = flavor_map.get(flavor, None)
    if query is None:
        raise NotImplementedError
    return len(tquery(query, con)) > 0

def get_sqltype(pytype, flavor):
    sqltype = {'mysql': 'VARCHAR (63)',
               'sqlite': 'TEXT'}

    if issubclass(pytype, np.floating):
        sqltype['mysql'] = 'FLOAT'
        sqltype['sqlite'] = 'REAL'

    if issubclass(pytype, np.integer):
        #TODO: Refine integer size.
        sqltype['mysql'] = 'BIGINT'
        sqltype['sqlite'] = 'INTEGER'

    if issubclass(pytype, np.datetime64) or pytype is datetime:
        # Caution: np.datetime64 is also a subclass of np.number.
        sqltype['mysql'] = 'DATETIME'
        sqltype['sqlite'] = 'TIMESTAMP'

    if pytype is datetime.date:
        sqltype['mysql'] = 'DATE'
        sqltype['sqlite'] = 'TIMESTAMP'

    if issubclass(pytype, np.bool_):
        sqltype['sqlite'] = 'INTEGER'

    return sqltype[flavor]

def get_schema(frame, name, flavor, keys=None):
    "Return a CREATE TABLE statement to suit the contents of a DataFrame."
    lookup_type = lambda dtype: get_sqltype(dtype.type, flavor)
    # Replace spaces in DataFrame column names with _.
    safe_columns = [s.replace(' ', '_').strip() for s in frame.dtypes.index]
    column_types = zip(safe_columns, map(lookup_type, frame.dtypes))
    if flavor == 'sqlite':
        columns = ',\n  '.join('[%s] %s' % x for x in column_types)
    else:
        columns = ',\n  '.join('`%s` %s' % x for x in column_types)

    keystr = ''
    if keys is not None:
        if isinstance(keys, basestring):
            keys = (keys,)
        keystr = ', PRIMARY KEY (%s)' % ','.join(keys)
    template = """CREATE TABLE %(name)s (
                  %(columns)s
                  %(keystr)s
                  );"""
    create_statement = template % {'name': name, 'columns': columns,
                                   'keystr': keystr}
    return create_statement

def sequence2dict(seq):
    """Helper function for cx_Oracle.

    For each element in the sequence, creates a dictionary item equal
    to the element and keyed by the position of the item in the list.
    >>> sequence2dict(("Matt", 1))
    {'1': 'Matt', '2': 1}

    Source:
    http://www.gingerandjohn.com/archives/2004/02/26/cx_oracle-executemany-example/
    """
    d = {}
    for k,v in zip(range(1, 1 + len(seq)), seq):
        d[str(k)] = v
    return d
<<<<<<< HEAD
=======

def test_sqlite(name, testdf):
    print '\nsqlite, using detect_types=sqlite3.PARSE_DECLTYPES for datetimes'
    import sqlite3
    with sqlite3.connect('test.db', detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        #conn.row_factory = sqlite3.Row
        write_frame(testdf, name, con=conn, flavor='sqlite', if_exists='replace')
        df_sqlite = read_db('select * from '+name, con=conn)    
        print 'loaded dataframe from sqlite', len(df_sqlite)   
    print 'done with sqlite'


def test_oracle(name, testdf):
    print '\nOracle'
    import cx_Oracle
    with cx_Oracle.connect('YOURCONNECTION') as ora_conn:
        testdf['d64'] = np.datetime64( testdf['hire_date'] )
        write_frame(testdf, name, con=ora_conn, flavor='oracle', if_exists='replace')    
        df_ora2 = read_db('select * from '+name, con=ora_conn)    

    print 'done with oracle'
    return df_ora2
   
    
def test_postgresql(name, testdf):
    #from pg8000 import DBAPI as pg
    import psycopg2 as pg
    print '\nPostgresQL, Greenplum'    
    pgcn = pg.connect(YOURCONNECTION)
    print 'df frame_query'
    try:
        write_frame(testdf, name, con=pgcn, flavor='postgresql', if_exists='replace')   
        print 'pg copy_from'    
        postgresql_copy_from(testdf, name, con=pgcn)    
        df_gp = read_db('select * from '+name, con=pgcn)    
        print 'loaded dataframe from greenplum', len(df_gp)
    finally:
        pgcn.commit()
        pgcn.close()
    print 'done with greenplum'

 
def test_mysql(name, testdf):
    import MySQLdb
    print '\nmysql'
    cn= MySQLdb.connect(YOURCONNECTION)    
    try:
        write_frame(testdf, name='test_df', con=cn, flavor='mysql', if_exists='replace')
        df_mysql = read_db('select * from '+name, con=cn)    
        print 'loaded dataframe from mysql', len(df_mysql)
    finally:
        cn.close()
    print 'mysql done'


##############################################################################

if __name__=='__main__':

    print """sqlite should work out of the box. For the other test, you must
             install the driver and provide a connection string."""
    
    test_data = {
        "name": [ 'Joe', 'Bob', 'Jim', 'Suzy', 'Cathy', 'Sarah' ],
        "hire_date": [ datetime(2012,1,1), datetime(2012,2,1), datetime(2012,3,1), datetime(2012,4,1), datetime(2012,5,1), datetime(2012,6,1) ],
        "erank": [ 1,   2,   3,   4,   5,   6  ],
        "score": [ 1.1, 2.2, 3.1, 2.5, 3.6, 1.8]
    }
    df = DataFrame(test_data)

    name='test_df'
    test_sqlite(name, df)
    #test_oracle(name, df)
    #test_postgresql(name, df)    
    #test_mysql(name, df)        
    
    print 'done'
>>>>>>> by default, only sqlite tests are run
