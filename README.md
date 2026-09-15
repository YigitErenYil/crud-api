# Task API

A small CRUD API for managing a to-do list, built with FastAPI. Data lives in a Postgres database that runs in Docker, and user accounts are handled by Supabase Auth — signup, login, logout, and bearer-token-protected routes. The whole stack (app + database) starts with a single command.

## Run it

```bash
cp .env.example .env
docker compose up
```

That's it for the database and app — no manual Postgres setup. The API runs at `http://localhost:8000`. Interactive docs (Swagger UI) are available at `http://localhost:8000/docs`.

**Auth setup (required once):** this project uses Supabase as its Identity Provider, so you need your own free Supabase project to test signup/login:
1. Create a free project at [supabase.com](https://supabase.com) (no credit card).
2. In **Project Settings → API**, copy your **Project URL** and **anon key** (never the `service_role` key).
3. In **Authentication → Sign In / Providers → Email**, turn off "Confirm email" so a fresh signup can log in immediately (fine for local testing; you'd leave this on in production).
4. Paste your Project URL and anon key into `.env` as `SUPABASE_URL` and `SUPABASE_KEY` (see `.env.example`).

To stop everything: `docker compose down` (add `-v` if you also want to wipe the database volume).

## Environment variables

Set in a `.env` file (not committed — see `.env.example` for the keys you need):

```
DATABASE_URL=postgres://postgres:dev@localhost:5432/tasks
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
PORT=8000
```

Note: `docker compose` overrides `DATABASE_URL` internally so the app reaches the database by its service name (`db`) instead of `localhost` — you don't need to change anything, it's handled in `compose.yaml`.

## Endpoints

| CRUD operation | Method | Path                  | Auth required | Description                          |
|-----------------|--------|-------------------------|:---:|--------------------------------------|
| —               | GET    | `/`                     | — | API info                             |
| —               | GET    | `/health`               | — | Health check                         |
| Read            | GET    | `/tasks`                | — | List all tasks                       |
| Read            | GET    | `/tasks/{id}`           | — | Get one task by id (404 if missing)  |
| Create          | POST   | `/tasks`                | — | Create a task (400 if title missing) |
| Update          | PUT    | `/tasks/{id}`           | — | Update title and/or done status      |
| Delete          | DELETE | `/tasks/{id}`           | — | Delete a task (204 on success)       |
| —               | POST   | `/auth/signup`          | — | Create an account (400 if email/password missing) |
| —               | POST   | `/auth/login`           | — | Log in, returns an access token (401 on bad credentials) |
| —               | POST   | `/auth/logout`          | ✅ | Log out the current user (204 on success) |
| —               | GET    | `/public/info`          | — | Public info, no auth needed |
| —               | GET    | `/protected/profile`    | ✅ | Get the current user's profile |
| —               | GET    | `/protected/dashboard`  | ✅ | Dashboard route (reuses the same auth guard) |

Routes marked ✅ require an `Authorization: Bearer <access_token>` header. The token comes from `/auth/login`, and is verified against Supabase on every request.

## Example request

```
$ curl -i http://localhost:8000/tasks
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"title":"Buy milk","done":false},{"id":2,"title":"Write README","done":false},{"id":3,"title":"Push to GitHub","done":true}]
```

## Authentication flow

```
$ curl -i -X POST http://localhost:8000/auth/signup \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"password123"}'
HTTP/1.1 201 Created

$ curl -i -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"password123"}'
HTTP/1.1 200 OK
{"access_token":"eyJ...","refresh_token":"..."}

$ curl -i http://localhost:8000/protected/profile \
    -H "Authorization: Bearer eyJ..."
HTTP/1.1 200 OK
{"id":"...","email":"test@example.com","created_at":"..."}
```

An invalid or tampered token on `/protected/profile` returns `401 {"error":"Invalid or expired token"}`.

## Swagger UI

Protected routes show a lock icon, and the "Authorize" button lets you paste a token once and reuse it across every protected route — no repeated `curl` commands needed.

![Swagger UI with lock icons on protected routes](screenshots/swagger-ui.png)

![Successful authorized request to /protected/profile](screenshots/swagger-auth.png)

## Database

Data lives in PostgreSQL, running as its own container (not a file on disk). The `tasks` table is created automatically on first run, along with 3 seed tasks — a fresh clone just needs `docker compose up`, nothing manual.

Data survives a full `docker compose down` + `docker compose up`, because it's stored in a named Docker volume (`taskdata`) that lives independently of the containers — killing and recreating the containers doesn't touch the volume.

### Verifying the data in Postgres

```
$ docker exec -it crud-api-db-1 psql -U postgres -d tasks -c "\dt"
        List of relations
 Schema | Name  | Type  |  Owner
--------+-------+-------+----------
 public | tasks | table | postgres

$ docker exec -it crud-api-db-1 psql -U postgres -d tasks -c "SELECT * FROM tasks;"
 id |     title       | done
----+------------------+------
  1 | Buy milk         | f
  2 | Write README     | f
  3 | Push to GitHub   | t
```

![Tasks table listed via psql \dt](screenshots/db-tables.png)

![Tasks data via psql SELECT *](screenshots/db-data.png)

## Project history

This project has grown across several assignments while keeping the same API on top:
1. In-memory list (gone on restart)
2. SQLite file (`tasks.db`)
3. Postgres in Docker — a real database server, running the same way on any machine
4. **Supabase Auth** (current) — signup/login/logout, bearer token verification via a reusable auth guard, and Swagger bearer authorization

Only the relevant module changed each time; the core route shapes stayed the same.