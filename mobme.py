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


async def create_account(request: web.Request) -> web.Response:
    return web.FileResponse("index.html")


async def create_account_post(request: web.Request) -> web.Response:
    data = await request.post()
    await app["db"].add_user(data["username"], data["email"], data["name"])
    await app["mob"].ledger_manager.put_pmob_tx(
        data["username"], int(0.5e12), "airdrop"
    )
    return "yeah"
    # keep a login cookie


async def login(request: web.Request) -> web.Response:
    pass


async def user_donate_page(request: web.Request) -> web.Response:
    pass
    # serve pages for mob.me links
    # donate to user x if they exist and you're loged in


async def main(request: web.Request) -> web.Response:
    pass
    # form for send to a username
    # form for wd to wallet


async def discover(request: web.Request) -> web.Response:
    # list people in db with links
    pass


app.add_routes([web.get("/", create_account), web.post("/", create_account_post)])

if __name__ == "__main__":
    web.run_app(app, port=8080, host="0.0.0.0", access_log=None)
