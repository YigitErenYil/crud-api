from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
app = FastAPI()

class TaskCreate(BaseModel):
    title: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

@app.exception_handler(HTTPException)
def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

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
    return tasks

@app.get("/tasks/{task_id}", summary="Get one task by id")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(payload: TaskCreate):
    global next_id
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    task = {"id": next_id, "title": payload.title, "done": False}
    tasks.append(task)
    next_id += 1
    return task

@app.put("/tasks/{task_id}", summary="Update a task's title and/or done status")
def update_task(task_id: int, payload: TaskUpdate):
    for task in tasks:
        if task["id"] == task_id:
            if payload.title is not None:
                if not payload.title.strip():
                    raise HTTPException(status_code=400, detail="title cannot be empty")
                task["title"] = payload.title
            if payload.done is not None:
                task["done"] = payload.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")