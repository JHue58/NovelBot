import sqlite3

DB_NAME = "NovelDB/novel.db"
TABLE_NAME = "TAG_TABLE"
LOG_NAME = "log.log"


def default():
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    cursorObj.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}(id integer,tags text,count integer)"
    )
    con.commit()
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


def getTagsCount(qq: int) -> dict:
    if type(qq) != type(0):
        raise Exception("q must be int")
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
    tag = tag.replace('{','')
    tag = tag.replace('}', '')
    tag = tag.replace('[', '')
    tag = tag.replace(']', '')
    tag = tag.replace('(', '')
    tag = tag.replace(')', '')

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
