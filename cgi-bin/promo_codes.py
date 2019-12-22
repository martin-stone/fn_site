#!/usr/local/bin/python3

import cgi
import re
import os
import sys
import sqlite3
import datetime
from os.path import abspath, normpath, dirname, join, exists
from http import cookies

def response():
    try:
        params = cgi.FieldStorage()
        promo_id = sanitize(params.getfirst("promoId"))
        package_id = sanitize(params.getfirst("packageId"))
        disclaim_code = params.getfirst("disclaim")
        #print(disclaim_code, file=sys.stderr)

        response_template = """Status: 200
            Content-Type: text/plain
            Set-Cookie: {package_id}={code}; Max-Age={max_age}; SameSite=Strict

            {code}""".replace(" "*4, "")

        if disclaim_code:
            free_code(package_id, promo_id, disclaim_code)
            return response_template.format(package_id=package_id, code="", max_age=0)
        else:
            try:
                #raise KeyError()
                code = read_previous_from_cookie(package_id)
                #print("from cookie", file=sys.stderr)
            except (cookies.CookieError, KeyError):
                code = allocate_code(package_id, promo_id)
                #print("from db " + code, file=sys.stderr)
            return response_template.format(package_id=package_id, code=code, max_age=60000000)

    except Exception as e:
        # empty body
        return "Status: 404\nContent-Type: text/plain\n\n"


def read_previous_from_cookie(package_id):
    cookie = cookies.SimpleCookie(os.environ["HTTP_COOKIE"])
    return cookie[package_id].value


def allocate_code(package_id, promo_id):
    codes_path = build_path(package_id, promo_id)

    if not exists(codes_path + ".sqlite"):
        init_db(codes_path)

    with sqlite3.connect(codes_path + ".sqlite") as conn:
        #print(conn, file=sys.stderr)
        cursor = conn.execute("select code from codes where taken_date is null limit 1")
        code = cursor.fetchone()[0]
        print(code, file=sys.stderr)
        conn.execute("update codes set taken_date=? where code=?", (datetime.datetime.now(), code))
        return code


def init_db(codes_path):
    with open(codes_path + ".csv", encoding="utf8") as f:
        quoted_code_list = ",".join("('{}')".format(code.strip()) for code in f if code.strip())

    with sqlite3.connect(codes_path + ".sqlite") as conn:
        conn.execute("""CREATE TABLE "codes"(
            [code] TEXT PRIMARY KEY NOT NULL UNIQUE, 
            [taken_date] DATETIME);""")
        conn.execute("insert into codes (code) values {}".format(quoted_code_list))
    print("created " + codes_path + ".sqlite", file=sys.stderr)


def free_code(package_id, promo_id, code):
    codes_path = build_path(package_id, promo_id)
    with sqlite3.connect(codes_path + ".sqlite") as conn:
        print("returning " + code, file=sys.stderr)
        conn.execute("update codes set taken_date=null where code=?", (code,))
    print("freed code " + code, file=sys.stderr)


def build_path(package_id, promo_id):
    codes_file = "_".join(("promotion", package_id, promo_id))
    codes_dir = normpath(join(
        abspath(dirname(__file__)), 
        "../../figmentanova_promo_codes"))
    return join(codes_dir, codes_file)


def sanitize(param):
    return re.sub(r"[^\w\.]", "", str(param), flags=re.ASCII)


if __name__ == '__main__':
    print(response())