from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from uuid import uuid4
import asyncio
import time

app = FastAPI()

fake_db: Dict[str, dict] = {}

class TaskCreate(BaseModel):
    title: str
    description: str = ""

class TaskResponce(BaseModel):
    id: str
    title: str
    description: str = ""
    completed: bool = False

@app.get('/')
def root():
    return {"message": "Hello, World!"}

@app.get('/health')
def health():
    return {"status": "alive"}

@app.post('/tasks', response_model=TaskResponce)
def create_task(task: TaskCreate):
    task_id = str(uuid4())
    new_task = {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "completed": False,
    }

    fake_db[task_id] = new_task

    return new_task

@app.get('/tasks', response_model=List[TaskResponce])
def list_tasks():
    return list(fake_db.values())

@app.get('/tasks/{task_id}')
def get_task(task_id: str):
    if task_id not in fake_db:
        raise HTTPException(status_code=404, detail="Task not Found!")
    return fake_db[task_id]

@app.delete('/tasks/{task_id}')
def delete_task(task_id: str):
    if task_id not in fake_db:
        raise HTTPException(status_code=404, detail="Task not Found!(Deleting not possible)")
    del fake_db[task_id]
    return {"message": "Task deleted"}


# СИНХРОННЫЙ (блокирующий) — плохо для многих запросов
@app.get("/sync-slow")
def sync_slow():
    time.sleep(2)  # блокирует весь сервер на 2 секунды
    return {"message": "sync done", "timestamp": time.time()}

# АСИНХРОННЫЙ (неблокирующий) — хорошо
@app.get("/async-slow")
async def async_slow():
    await asyncio.sleep(2)  # не блокирует, сервер может обрабатывать другие запросы
    return {"message": "async done", "timestamp": time.time()}