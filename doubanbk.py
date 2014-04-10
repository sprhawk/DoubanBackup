#!/usr/bin/env python3.4

import sys
import urllib.request
from urllib.request import Request 
from urllib import parse
from http.client import HTTPResponse as response

import json

import sqlite3 as sq

from keys import API_KEY, SECRET, REDIRECT_URI

# 由dex2jar + JD-GUI 从 com.douban.group.apk文件中获取
DB_ANDROID_GROUP_APP_API_KEY = "00a0951fbec80b0501e1bf5f3c58210f"
DB_ANDROID_GROUP_APP_SECRET = "77faec137e9bda16"
DB_ANDROID_GROUP_APP_REDIRECT_URI = "http://group.douban.com/!service/android"

API_KEY = DB_ANDROID_GROUP_APP_API_KEY
SECRET = DB_ANDROID_GROUP_APP_SECRET
REDIRECT_URI = DB_ANDROID_GROUP_APP_REDIRECT_URI

SQLITE_DB = "doubanbak.db"

sqlite_conn = None

def sqlitedb():
    global sqlite_conn
    if sqlite_conn is None:
        sqlite_conn = sq.connect(SQLITE_DB)
        initdb()
    return sqlite_conn

def initdb():
    db = sqlitedb()
    c = db.cursor()
    c.execute("create table if not exists settings (name text unique not null, value text);")
    c.execute("""create table if not exists shuo 
                (shuoid text, userid text, attachment text, source text, 
                 reshared_count integer, like_count integer, comments_count integer, can_reply integer, liked integer, created_at text, reshared_status text, fts_docid integer);""")
    c.execute("""create virtual table if not exists shuo_fts USING fts4(title, text)""")
    c.execute("create table if not exists douban_user (user_id text, user_uid text, name text, small_avatar text, large_avatar text, description);")
    db.commit()

def insert_shuo(shuo):
    db = sqlitedb()
    c = db.cursor()

    shuoid = shuo["id"]
    user = shuo["user"]
    userid = user["id"]
    title = shuo["title"]
    text = shuo["text"]

    attachments = shuo.get("attachments")
    if attachments is not None:
        attachments = json.dumps(attachments)

    source = shuo.get("source")
    if source is not None:
        source = json.dumps(source)

    reshared_count = shuo.get("reshared_count")
    if reshared_count is not None:
        reshared_count = int(reshared_count)

    like_count = shuo.get("like_count")
    if like_count is not None:
        like_count = int(like_count)

    comments_count = shuo.get("comments_count")
    if comments_count is not None:
        comments_count = int(comments_count)

    can_reply = shuo.get("can_reply")
    if can_reply is not None:
        can_reply = int(can_reply)

    liked = shuo.get("liked")
    if liked is not None:
        liked = int(liked)

    created_at = shuo["created_at"]

    reshared_status = shuo.get("reshared_status")
    if reshared_status is not None:
        reshared_status = json.dumps(reshared_status)
    
    c.execute("select count() from shuo where shuoid = ?", (shuoid, ))
    row = c.fetchone()

    if 0 == row[0]:
        c.execute("select count() from douban_user where user_id = ?", (userid, ))
        row = c.fetchone()
        if 0 == row[0]:
            c.execute("""insert into douban_user (user_id, user_uid, name, small_avatar, large_avatar, description) 
                values (?, ?, ?, ?, ?, ?);""", (userid, user["uid"], user["screen_name"], user["small_avatar"], user["large_avatar"], user["description"]))
            print("inserted user:" + user["screen_name"])
        p = (title, text)
        c.execute("insert into shuo_fts (title, text) values (?, ?)", p)
        c.execute("select last_insert_rowid();")
        row = c.fetchone()
        docid = row[0]
        p = (shuoid, userid, attachments,source, reshared_count, like_count, comments_count, can_reply, liked, created_at,reshared_status, docid)
        c.execute("""insert into shuo (shuoid, userid, attachment, source, reshared_count, like_count, comments_count, can_reply, liked, created_at, reshared_status, fts_docid) 
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", p)
        print("inserted shuo(" + created_at + "): " + text)
        db.commit()

def sqlitedb_close():
    db = sqlitedb()
    db.close()

def db_settings_set(key, value):
    db = sqlitedb()
    c = db.cursor()
    pairs = (key, )
    c.execute("select count() from settings where name = ?", pairs)
    row = c.fetchone()
    count = row[0]
    if 0 == count:
        pairs = (key, value)
        c.execute("insert into settings (name, value) values (?, ?)", pairs)
    else:
        pairs = (value, key,)
        c.execute("update settings set value = ? where name = ?", pairs)
    db.commit()

def db_settings_get(key):
    db = sqlitedb()
    c = db.cursor()
    pairs = (key, )
    c.execute("select value from settings where name = ?", pairs)
    row = c.fetchone()
    if row is not None:
        value = row[0]
        return value
    return None
        
def post(url, parameters, token=None):
    data = parse.urlencode(parameters).encode('utf-8')
    req = Request(url, data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    if token is not None:
        req.add_header("Authorization", "Bearer " + token) 
    resp = urllib.request.urlopen(req)
    return resp

def get(url, parameters, token=None):
    if parameters is not None:
        p = parse.urlencode(parameters)
        url = url + "?%s" % p
    print("GET " + url)
    req = Request(url)
    if token is not None:
        req.add_header("Authorization", "Bearer " + token) 
    req.add_header("User-Agent", "api-client/2.0 com.douban.group/2.22(222) Android/18 Group Douban x86")
    resp = urllib.request.urlopen(req)
    return resp

def auth(api_key, redirect_uri, response_type, scope=None):
    import webbrowser as wb
    url = "https://www.douban.com/service/auth2/auth?client_id=" + api_key + "&redirect_uri=" + redirect_uri + "&response_type=" + response_type
    if scope:
        url = url + "&scope=" + scope
    wb.open(url)

def token(client_id, secret, redirect_uri, grant_type, code):
    params = {"client_id":client_id,
                "client_secret":secret,
                "redirect_uri":redirect_uri,
                "grant_type":grant_type,
                "code":code
             }
    resp = post("https://www.douban.com/service/auth2/token", params)
    resp = resp.read().decode('utf-8')
    print(resp)
    obj = json.loads(resp)
    db_settings_set("access_token", obj["access_token"])
    db_settings_set("username", obj["douban_user_name"])
    db_settings_set("userid", obj["douban_user_id"])
    db_settings_set("expires_in", obj["expires_in"])
    db_settings_set("refresh_token", obj["refresh_token"])

def save_access_token(token):
    db_settings_set("access_token", token) 

def retrieve_timeline(timeline, start, count):
    token = db_settings_get("access_token")
    parameters = {"start":start,
                  "count":count}
    resp = get("https://api.douban.com/shuo/v2/statuses/" + timeline, parameters, token)
    obj = json.loads(resp.read().decode('utf-8'))
    # print(obj)
    db = sqlitedb()
    c = db.cursor()
    for shuo in obj:
        insert_shuo(shuo)        
    return len(obj)

def retrieve_home_timeline(start = 0, count = 0):
    return retrieve_timeline("home_timeline", start, count)
    
def retrieve_user_timeline(userid, start = 0, count = 0):
    return retrieve_timeline("user_timeline/" + userid, start, count)

def retrieve_my_timeline(start = 0, count = 0):
    db = sqlitedb()
    c = db.cursor()
    userid = db_settings_get("userid")
    return retrieve_user_timeline(userid, start, count)

def retrieve_all_shuo():
    import time
    start = 0
    count = retrieve_my_timeline(start, 200) 
    while 200 == count:
        time.sleep(1) 
        start += 200
        count = retrieve_my_timeline(start, 200) 

def retrieve_group_my_topics():
    token = db_settings_get("access_token")
    parameters = {"start": 0,
                  "count": 1}
    resp = get("https://api.douban.com/v2/group/my_topics", parameters, token)
    print(resp.read().decode('utf-8'))

if __name__ == "__main__":
    print("test")

    command = sys.argv[1]
    if command == "auth":
        scope = """douban_basic_common,movie_basic,movie_basic_r,travel_basic_r,community_basic_note,community_basic_user,community_basic_photo,community_basic_online,book_basic_r,music_basic_r,music_artist_r,shuo_basic_r,event_basic_r,event_drama_r"""

        auth(API_KEY, REDIRECT_URI, "code", None)
    elif command == "token":
        if len(sys.argv) >=3 :
            code = sys.argv[2]
            token(API_KEY, SECRET, REDIRECT_URI, "authorization_code", code)
        else:
            print("missing token code")
    elif command == "save_access_token":
        if len(sys.argv) >= 3:
            token = sys.argv[2]
            save_access_token(token)
        else:
            print("missing access token")
    elif command == "get":
        if len(sys.argv) >= 3:
            subcommand = sys.argv[2]
            if subcommand == "shuo":
                retrieve_all_shuo()
            elif subcommand == "group":
                retrieve_group_my_topics()
            else:
                print("not support " + subcommand)
        else:
            print("missing subcommand")




