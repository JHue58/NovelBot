import sqlite3
import time

DB_NAME = "NovelDB/novel.db"
TABLE_NAME = "TAG_TABLE"
USE_COUNT_TABLE_NAME = "USE_COUNT_TABLE"
USER_BLACK_TABLE_NAME = "USER_BLACK_TABLE"
CUSTOM_TAG_TABLE_NAME = "CUSTOM_TAG_TABLE"
LOG_NAME = "log.log"


class CustomTagsError(Exception):
    def __init__(self, error):
        super().__init__(self)  # 初始化父类
        self.errorinfo = f"CustomTagsError: {error}"

    def __str__(self):
        return self.errorinfo


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
    con.commit()
    cursorObj.execute(
        f"CREATE TABLE IF NOT EXISTS {USER_BLACK_TABLE_NAME}(id integer PRIMARY KEY,addTime integer,banTime integer)"
    )
    con.commit()
    cursorObj.execute(
        f"CREATE TABLE IF NOT EXISTS {CUSTOM_TAG_TABLE_NAME}(id integer ,name text PRIMARY KEY,parm text) "
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


def addBlack(qq: int, banTime: int):
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    addTime = int(time.time())
    sql = f"INSERT INTO {USER_BLACK_TABLE_NAME} VALUES(?,?,?) ON CONFLICT (id) DO UPDATE SET addTime=?,banTime=?"
    res = cursorObj.execute(sql, [qq, addTime, banTime, addTime, banTime])
    con.commit()
    con.close()


def removeBlack(qq: int):
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"DELETE FROM {USER_BLACK_TABLE_NAME} WHERE id=?"
    cursorObj.execute(sql, [qq])
    con.commit()
    con.close()


def getBanTime(qq: int):
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    nowTime = int(time.time())
    sql = f"SELECT addTime,banTime FROM {USER_BLACK_TABLE_NAME} WHERE id={qq}"
    cursorObj.execute(sql)
    rows = cursorObj.fetchall()
    if len(rows) == 0:
        con.close()
        return 0
    row = rows[0]
    addTime = row[0]
    banTime = row[1]

    remainingTime = banTime - (nowTime - addTime)

    if remainingTime <= 0:
        sql = f"DELETE FROM {USER_BLACK_TABLE_NAME} WHERE id = ?"
        cursorObj.execute(sql, [qq])
        con.commit()
        con.close()
        return 0
    else:
        con.close()
        return remainingTime


def addCustomTags(qq: int, name: str, parm: str, max_add: int):
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"SELECT name FROM {CUSTOM_TAG_TABLE_NAME} WHERE id={qq}"
    cursorObj.execute(sql)
    rows = cursorObj.fetchall()
    if len(rows) >= max_add:
        con.close()
        raise CustomTagsError(f"您的自定义数据已达到最大数量 {max_add} 个")
    sql = f"INSERT INTO {CUSTOM_TAG_TABLE_NAME} VALUES(?,?,?)"
    try:
        cursorObj.execute(sql, [qq, name, parm])
        con.commit()
    except:
        con.close()
        raise CustomTagsError(f"自定义数据名称 {name} 已存在")
    con.close()


def removeCustomTags(qq: int, name: str):
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    sql = f"SELECT parm,id FROM {CUSTOM_TAG_TABLE_NAME} WHERE name=? AND id=?"
    rows = con.execute(sql, [name, qq]).fetchall()
    if len(rows) == 0:
        con.close()
        raise CustomTagsError(f"名为 {name} 的自定义数据不存在或该数据是由他人创建")
    cursorObj = con.cursor()
    try:
        sql = f"DELETE FROM {CUSTOM_TAG_TABLE_NAME} WHERE id=? AND name=?"
        cursorObj.execute(sql, [qq, name])
        con.commit()
    except:
        con.close()
        raise CustomTagsError(f"名为 {name} 的自定义数据不存在或该数据是由他人创建")
    con.close()


def getAllCustomTags(qq: int):
    if type(qq) != type(0):
        raise Exception("qq must be int")
    con = sqlite3.connect(DB_NAME)
    cursorObj = con.cursor()
    sql = f"SELECT name FROM {CUSTOM_TAG_TABLE_NAME} WHERE id={qq}"
    cursorObj.execute(sql)
    rows = cursorObj.fetchall()
    con.close()
    custom_tags_list = []
    for row in rows:
        custom_tags_list.append(row[0])
    return custom_tags_list


def getCustomTags(name: str):
    con = sqlite3.connect(DB_NAME)
    sql = f"SELECT parm,id FROM {CUSTOM_TAG_TABLE_NAME} WHERE name=?"
    rows = con.execute(sql, [name]).fetchall()
    con.close()
    if len(rows) == 0:
        raise CustomTagsError(f"名为 {name} 的自定义数据不存在")
    row = rows[0]

    return row


default()
