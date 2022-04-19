from aiohttp import web
from forest import pghelp, utils
from forest.payments_monitor import StatefulMobster

AccExpr = pghelp.PGExpressions(
    table="accounts",
    create_table="""
        create table {self.table} (
            id SERIAL PRIMARY KEY,
            username text unique,
            email text,
            name text
        );
    """,
    add_user="insert into {self.table} (username, email, name) values ($1, $2, $3);",
)


app = web.Application()

async def startup(app: web.Application) -> None:
    app["db"] = pghelp.PGInterface(
        query_strings=AccExpr,
        database=utils.get_secret("DATABASE_URL"),
    )
    app["mob"] = StatefulMobster()

app.on_startup.append(startup)


async def index(request: web.Request) -> web.Response:
    return web.FileResponse("index.html")


async def index_post(request: web.Request) -> web.Response:
    data = await request.post()
    await app["db"].add_user(data["username"], data["email"], data["name"])
    await app["mob"].ledger_manager.put_pmob_tx(data["username"], int(0.5e12), "airdrop")
    return "yeah"
    # keep a login cookie


async def main(request: web.Request) -> web.Response:
    pass
    # form for send to a username
    # form for wd to wallet

# serve pages for mob.me links

app.add_routes([web.get("/", index), web.post("/", index_post)])

if __name__ == "__main__":
    web.run_app(app, port=8080, host="0.0.0.0", access_log=None)
