# Task API

A small CRUD API for managing a to-do list, built with FastAPI. Data lives in a Postgres database that runs in Docker — the whole stack (app + database) starts with a single command.

## Run it

```bash
cp .env.example .env
docker compose up
```

That's it — no manual database setup. The API runs at `http://localhost:8000`. Interactive docs (Swagger UI) are available at `http://localhost:8000/docs`.

To stop everything: `docker compose down` (add `-v` if you also want to wipe the database volume).

## Environment variables

The app reads its database connection string from `DATABASE_URL`, set in a `.env` file (not committed — see `.env.example` for the keys you need):

```
DATABASE_URL=postgres://postgres:dev@localhost:5432/tasks
```

Note: `docker compose` overrides this internally so the app reaches the database by its service name (`db`) instead of `localhost` — you don't need to change anything, it's handled in `compose.yaml`.

## Endpoints

| CRUD operation | Method | Path             | Description                          |
|-----------------|--------|-------------------|--------------------------------------|
| —               | GET    | `/`               | API info                             |
| —               | GET    | `/health`         | Health check                         |
| Read            | GET    | `/tasks`          | List all tasks                       |
| Read            | GET    | `/tasks/{id}`     | Get one task by id (404 if missing)  |
| Create          | POST   | `/tasks`          | Create a task (400 if title missing) |
| Update          | PUT    | `/tasks/{id}`     | Update title and/or done status      |
| Delete          | DELETE | `/tasks/{id}`     | Delete a task (204 on success)       |

## Example request

```
$ curl -i http://localhost:8000/tasks
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"title":"Buy milk","done":false},{"id":2,"title":"Write README","done":false},{"id":3,"title":"Push to GitHub","done":true}]
```

## Swagger UI

![Swagger UI showing all endpoints](screenshots/swagger-ui.png)

## Database

Data lives in PostgreSQL, running as its own container (not a file on disk anymore). The `tasks` table is created automatically on first run, along with 3 seed tasks — a fresh clone just needs `docker compose up`, nothing manual.

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

## Storage history

This project has swapped its storage engine twice while keeping the same API on top:
1. In-memory list (gone on restart)
2. SQLite file (`tasks.db`)
3. **Postgres in Docker** (current) — a real database server, running the same way on any machine

Only the database module changed each time; the routes stayed the same.