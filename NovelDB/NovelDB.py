import sqlite3
import time

DB_NAME = "NovelDB/novel.db"
TABLE_NAME = "TAG_TABLE"
USE_COUNT_TABLE_NAME = "USE_COUNT_TABLE"
LOG_NAME = "log.log"


def default():
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    cursorObj.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(id integer,tags text,count integer)"
    )
    con.commit()
    cursorObj.execute(
        f"CREATE TABLE IF NOT EXISTS {USE_COUNT_TABLE_NAME}(id integer PRIMARY KEY,count integer,lastTime text)"
    )
    con.close()


def logToDB():
    with open(LOG_NAME, 'r', encoding='utf-8') as logFile:
        lines = logFile.readlines()
    for line in lines:
        if line[:6] == "请求QQ号:":
            qq = line[6:]
        if line[:6] == "请求关键字:":
            tags = line[6:]
            insertTagsToDB(int(qq), tags)


def getUseCount(qq: int) -> int:
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"SELECT count,lastTime FROM {USE_COUNT_TABLE_NAME} WHERE id={qq}"
    cursorObj.execute(sql)
    rows = cursorObj.fetchall()
    day_str = time.strftime("%Y-%m-%d")
    if len(rows) == 0:
        sql = f"INSERT INTO {USE_COUNT_TABLE_NAME} VALUES(?,0,?)"
        cursorObj.execute(sql, [qq, day_str])
        con.commit()
        con.close()
        return 0

    count = rows[0][0]
    last_day = rows[0][1]
    if last_day != day_str:
        sql = f"UPDATE {USE_COUNT_TABLE_NAME} SET count = 0,lastTime=? WHERE id=?"
        cursorObj.execute(sql, [day_str, qq])
        con.commit()
        count = 0
    con.close()
    return count


def addUseCount(qq: int, add_value: int):
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    day_str = time.strftime("%Y-%m-%d")
    sql = f"UPDATE {USE_COUNT_TABLE_NAME} SET count=count+?,lastTime=? WHERE id=?"
    cursorObj.execute(sql, [add_value, day_str, qq])
    con.commit()
    con.close()


def deleteUseCount(qq: int):
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"UPDATE {USE_COUNT_TABLE_NAME} SET count=0 WHERE id=?"
    cursorObj.execute(sql, [qq])
    con.commit()
    con.close()


def getAllUseCount() -> list:
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    day_str = time.strftime("%Y-%m-%d")
    sql = f"SELECT id,count,lastTime FROM {USE_COUNT_TABLE_NAME} ORDER BY count DESC"
    cursorObj.execute(sql)
    rows = cursorObj.fetchall()
    userList = []
    for row in rows:
        if row[2] == day_str:
            userList.append((row[0], row[1]))
    return userList


def getTagsCount(qq: int) -> dict:
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"SELECT tags,count FROM {TABLE_NAME} WHERE id={qq} ORDER BY count DESC LIMIT 5"
    cursorObj.execute(sql)
    rows = cursorObj.fetchall()
    dicts = {}
    if len(rows) == 0:
        return None
    for row in rows:
        dicts[row[0]] = row[1]
    return dicts


def insertTagsToDB(qq: int, tags: str):
    if type(qq) != type(0):
        raise Exception("q must be int")
    tags = tags.replace('，', ',')
    tags_list = tags.split(',')
    if tags_list[0].lower() == 'gen':
        del tags_list[0]

    for tag in tags_list:
        insertOneTag(qq, tag)


def insertOneTag(qq: int, tag: str):
    tag = tag.strip()
    tag = tag.replace('\n', '')
    tag = tag.replace('{', '')
    tag = tag.replace('}', '')
    tag = tag.replace('[', '')
    tag = tag.replace(']', '')
    tag = tag.replace('(', '')
    tag = tag.replace(')', '')
    if tag == "":
        return

    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"SELECT * FROM {TABLE_NAME} WHERE id=? AND tags=?"
    cursorObj.execute(sql, [qq, tag])
    rows = cursorObj.fetchall()
    if len(rows) == 0:
        sql = f"INSERT INTO {TABLE_NAME} VALUES(?,?,1)"
        cursorObj.execute(sql, [qq, tag])
        con.commit()
        print(f"INSERT {tag} FROM {qq}")
    else:
        for row in rows:
            count = row[2]
            break
        count = str(int(count) + 1)
        sql = f"UPDATE {TABLE_NAME} SET count = ? WHERE id=? AND tags=?"
        cursorObj.execute(sql, [count, qq, tag])
        con.commit()
        print(f"UPDATE {tag} COUNT={count} FROM {qq}")
    con.close()


default()
