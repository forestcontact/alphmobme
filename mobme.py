#!/bin/python3.9
import base64
import logging
from aiohttp import web
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import mc_util
from forest import pghelp, utils, cryptography
from forest.payments_monitor import StatefulMobster

AccExpr = pghelp.PGExpressions(
    table="accounts",
    create_table="""
        create table {self.table} (
            id SERIAL PRIMARY KEY,
            username TEXT CONSTRAINT unique_username UNIQUE,
            email text,
            name text,
            password text,
            unique(username)
        );
    """,
    add_user="insert into {self.table} (username, email, name, password) values ($1, $2, $3, $4);",
    get_user="select * from {self.table} where username=$1",
)

app = web.Application()
# from cryptography import fernet
fernet_key = utils.get_secret("COOKIE_KEY")  # fernet.Fernet.generate_key()
secret_key = base64.urlsafe_b64decode(fernet_key)
setup(app, EncryptedCookieStorage(secret_key))


async def startup(app: web.Application) -> None:
    app["db"] = pghelp.PGInterface(
        query_strings=AccExpr,
        database=utils.get_secret("DATABASE_URL"),
    )
    app["mob"] = StatefulMobster()


app.on_startup.append(startup)


def resp(txt: str) -> web.Response:
    return web.Response(body=txt, content_type="text/html")


url = "localhost:8080"


async def index(request: web.Request) -> web.Response:
    sess = await get_session(request)
    if not sess.get("user"):
        return web.FileResponse("index.html")
    logging.info(sess.get("user"))
    u = await request.app["db"].get_user(sess["user"])
    if not u:
        return web.FileResponse("index.html")
    user = dict(u[0].items())
    bal = mc_util.pmob2mob(
        (await request.app["mob"].ledger_manager.get_pmob_balance(sess["user"]))[0][
            "balance"
        ]
    ).normalize()
    mobme = f"{url}/{user['username']}"
    logging.info(user)
    return resp(
        f"""<!DOCTYPE HTML>
        <div style="margin: 5%; float=left;">
        welcome {user['name']} <{user['email']}<br/><br/>
         your share link is <a href="{mobme}">{mobme}</a><br/><br/>
        your balance is {bal}
        </div>"""
    )
    # add withdraw button, but exclude airdrop from withdrawable balance


async def index_post(request: web.Request) -> web.Response:
    data = await request.post()
    app = request.app
    if await app["db"].get_user(data["username"]):
        return resp("username taken")
    await app["db"].add_user(
        data["username"],
        data["email"],
        data["name"],
        cryptography.hash_salt(data["password"]),
    )
    await app["mob"].ledger_manager.put_pmob_tx(
        data["username"], 100, int(0.5e12), "airdrop"
    )
    (await get_session(request))["user"] = data["username"]
    return resp("yeah <br/> <a href='javascript:window.history.back();'>back</a>")
    # keep a login cookie


async def login(request: web.Request) -> web.Response:
    if request.method == "GET":
        return resp(
            """
        <!DOCTYPE HTML>
        <form method="post">
          <div style = "margin: 5%; float: left">
            username: <input name="username" value=""><br/>
            password: <input name="password" type="password"><br/>
            <input type="submit">
          </div>
        </form>"""
        )
    data = await request.post()
    maybe_user = await request.app["db"].get_user(data["username"])
    if maybe_user and maybe_user[0].get("password") == cryptography.hash_salt(
        data["password"]
    ):
        (await get_session(request))["user"] = data["username"]
        return resp("success<br/> <a href='javascript:window.history.back();'>back</a>")
        # redirect to previous page
    logging.info("login as %s failed", data.get("username"))
    return resp("login failed")


async def user_tip_page(request: web.Request) -> web.Response:
    if request.method == "POST":
        logging.info(await request.post())
        # await app["mob"].ledger_manager.put_pmob_tx
        return resp("check back in tomorrow~!")
    username = request.match_info.get("username")
    maybe_profile = await request.app["db"].get_user(username)
    if not maybe_profile:
        return resp("user not found")
    profile = maybe_profile[0]
    sess = await get_session(request)
    if not sess.get("user"):
        blurb = '<a href="/">signup</a> or <a href="/login">login</a> to tip'
    else:
        blurb = f"""
        <form method="post">
            amount: <input name="amount" type="number" step="0.1" value="1">
            <input type="submit" value="tip {profile['name']}">
        </form>
        """
    return resp(
        f"""<!DOCTYPE HTML>
            <div style = "margin: 5%; float: left">
            tip {profile['name']}<br/><br/>
            {blurb}
        </div>"""
    )


async def main(request: web.Request) -> web.Response:
    pass
    # form for send to a username
    # form for wd to wallet


async def discover(request: web.Request) -> web.Response:
    # list people in db with links
    pass


app.add_routes(
    [
        web.get("/", index),
        web.post("/", index_post),
        web.get("/login", login),
        web.post("/login", login),
        web.route("*", "/{username}", user_tip_page),
    ]
)

if __name__ == "__main__":
    web.run_app(app, port=8080, host="0.0.0.0", access_log=None)
