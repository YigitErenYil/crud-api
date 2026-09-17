from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from auth import supabase
from enrich import EnrichRequest, EnrichResponse, STUB_RESPONSE, parse_model_json, call_model_with_retry
import json
from pathlib import Path
from llm import client
from datetime import datetime, timezone
import time as time_module


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()
bearer_scheme = HTTPBearer()

class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


class AuthCredentials(BaseModel):
    email: str
    password: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_response.user


@app.exception_handler(HTTPException)
def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    errors = exc.errors()
    if errors:
        field = ".".join(str(x) for x in errors[0]["loc"] if x != "body")
        message = f"{field}: {errors[0]['msg']}"
    else:
        message = "Invalid request body"
    return JSONResponse(status_code=400, content={"error": message})

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Write README", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": True},
]
next_id = 4


@app.get("/", summary="API info")
def read_root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
def list_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks")
    rows = cur.fetchall()
    conn.close()
    return [row_to_task(r) for r in rows]

@app.get("/tasks/{task_id}", summary="Get one task by id")
def get_task(task_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(payload: TaskCreate):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
        (payload.title, False),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return row_to_task(row)

@app.post("/auth/signup", status_code=201, summary="Create a new account")
def signup(payload: AuthCredentials):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        result = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"user": result.user}


@app.post("/auth/login", summary="Log in and get an access token")
def login(payload: AuthCredentials):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }

@app.post("/auth/logout", status_code=204, summary="Log out the current user")
def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return

@app.get("/public/info", summary="Public info, no auth required")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", summary="Get profile (token verified via Supabase)")
def get_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }
@app.get("/protected/dashboard", summary="Dashboard (reuses the same guard)")
def get_dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}"}

@app.put("/tasks/{task_id}", summary="Update a task's title and/or done status")
def update_task(task_id: int, payload: TaskUpdate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    new_title = row["title"]
    new_done = row["done"]

    if payload.title is not None:
        if not payload.title.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="title cannot be empty")
        new_title = payload.title
    if payload.done is not None:
        new_done = payload.done

    cur.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
        (new_title, new_done, task_id),
    )
    conn.commit()
    conn.close()
    return {"id": task_id, "title": new_title, "done": bool(new_done)}

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()
    return


def get_db():
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    cur.execute("SELECT COUNT(*) AS count FROM tasks")
    count = cur.fetchone()["count"]
    if count == 0:
        cur.executemany(
            "INSERT INTO tasks (title, done) VALUES (%s, %s)",
            [("Buy milk", False), ("Write README", False), ("Push to GitHub", True)],
        )
    conn.commit()
    conn.close()


init_db()

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"

def load_enrich_prompt():
    return PROMPT_PATH.read_text(encoding="utf-8")

QUARANTINE_PATH = Path(__file__).parent / "logs" / "quarantine.jsonl"


def log_quarantine(input_payload: dict, error: Exception, raw_output: str):
    QUARANTINE_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": "enrich-v1",
        "input": input_payload,
        "error": str(error),
        "raw_output": raw_output,
    }
    with open(QUARANTINE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def row_to_task(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

@app.post("/enrich", response_model=EnrichResponse, summary="Enrich a scraped book record with category, summary and quality flags")
def enrich(payload: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return STUB_RESPONSE

    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        raise HTTPException(status_code=503, detail="LLM enrichment is currently disabled")

    system_prompt = load_enrich_prompt()
    user_content = json.dumps(payload.model_dump())
    model_name = os.getenv("LLM_MODEL")

    def call_model(messages, repair_count):
        start = time_module.monotonic()
        response = call_model_with_retry(client, model_name, messages)
        duration_ms = int((time_module.monotonic() - start) * 1000)
        usage = response.usage
        print(json.dumps({
            "prompt_version": "enrich-v1",
            "model": model_name,
            "input_tokens": usage.prompt_tokens if usage else None,
            "output_tokens": usage.completion_tokens if usage else None,
            "duration_ms": duration_ms,
            "repair_count": repair_count,
        }))
        return response.choices[0].message.content

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    raw_text = call_model(messages, repair_count=0)

    try:
        parsed = parse_model_json(raw_text)
        return EnrichResponse.model_validate(parsed)
    except Exception as first_error:
        repair_messages = messages + [
            {"role": "assistant", "content": raw_text},
            {"role": "user", "content": f"Your previous answer was rejected for this reason: {first_error}. Return only corrected JSON matching the schema."},
        ]
        raw_text_2 = call_model(repair_messages, repair_count=1)
        try:
            parsed_2 = parse_model_json(raw_text_2)
            return EnrichResponse.model_validate(parsed_2)
        except Exception as second_error:
            log_quarantine(payload.model_dump(), second_error, raw_text_2)
            raise HTTPException(status_code=422, detail="Model output failed validation after one repair attempt")