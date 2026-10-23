"""Students Database CRUD API - FastAPI + SQLite (+ optional Ollama AI extension)."""
import json
import re
import sqlite3
import urllib.error
import urllib.request
from contextlib import asynccontextmanager, contextmanager
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, model_validator

DB_PATH = "students.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Students Database CRUD API", version="1.0.0", lifespan=lifespan)


# ---------- Database helpers ----------
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT
            )
            """
        )


# ---------- Schemas ----------
class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9 \-]{7,15}$")
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None

    @model_validator(mode="after")
    def check_contact_and_dob(self):
        if not self.email and not self.phone:
            raise ValueError("Provide at least one contact: email or phone")
        if self.date_of_birth > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return self


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    """All fields optional so PUT/PATCH can change only some of them."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9 \-]{7,15}$")
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


class Student(StudentBase):
    id: int


class Question(BaseModel):
    question: str = Field(..., min_length=3)


def row_to_student(row: sqlite3.Row) -> dict:
    return dict(row)


def to_db_values(data: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in data.items()}


def get_or_404(db: sqlite3.Connection, student_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    return row


# ---------- CRUD endpoints ----------
@app.post("/students", response_model=Student, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate):
    values = to_db_values(student.model_dump())
    try:
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO students
                   (name, date_of_birth, email, phone, course, address, enrollment_date)
                   VALUES (:name, :date_of_birth, :email, :phone, :course, :address, :enrollment_date)""",
                values,
            )
            return row_to_student(get_or_404(db, cur.lastrowid))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")


@app.get("/students", response_model=List[Student])
def list_students(
    name: Optional[str] = Query(None, description="Partial name match"),
    course: Optional[str] = Query(None, description="Exact course match"),
    born_after: Optional[int] = Query(None, description="Born after this year"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    sql, params = "SELECT * FROM students WHERE 1=1", []
    if name:
        sql += " AND name LIKE ?"
        params.append(f"%{name}%")
    if course:
        sql += " AND course = ?"
        params.append(course)
    if born_after is not None:
        sql += " AND CAST(substr(date_of_birth, 1, 4) AS INTEGER) > ?"
        params.append(born_after)
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_db() as db:
        return [row_to_student(r) for r in db.execute(sql, params).fetchall()]


@app.get("/students/{student_id}", response_model=Student)
def get_student(student_id: int):
    with get_db() as db:
        return row_to_student(get_or_404(db, student_id))


def apply_update(student_id: int, update: StudentUpdate):
    changes = to_db_values(update.model_dump(exclude_unset=True))
    if not changes:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    if "date_of_birth" in changes and changes["date_of_birth"] is None:
        raise HTTPException(status_code=400, detail="date_of_birth cannot be null")
    if "name" in changes and changes["name"] is None:
        raise HTTPException(status_code=400, detail="name cannot be null")
    if changes.get("date_of_birth") and changes["date_of_birth"] > date.today().isoformat():
        raise HTTPException(status_code=400, detail="date_of_birth cannot be in the future")
    set_clause = ", ".join(f"{col} = :{col}" for col in changes)  # column names come from the schema, not user input
    changes["id"] = student_id
    try:
        with get_db() as db:
            get_or_404(db, student_id)
            db.execute(f"UPDATE students SET {set_clause} WHERE id = :id", changes)
            row = get_or_404(db, student_id)
            if not row["email"] and not row["phone"]:
                raise HTTPException(status_code=400, detail="Student must keep at least one contact (email or phone)")
            return row_to_student(row)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")


@app.put("/students/{student_id}", response_model=Student)
def put_student(student_id: int, update: StudentUpdate):
    return apply_update(student_id, update)


@app.patch("/students/{student_id}", response_model=Student)
def patch_student(student_id: int, update: StudentUpdate):
    return apply_update(student_id, update)


@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    with get_db() as db:
        get_or_404(db, student_id)
        db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return {"message": f"Student {student_id} deleted"}


# ---------- Optional bonus: local AI with Ollama ----------
def retrieve_context(question: str) -> List[dict]:
    """Fixed, safe queries only - the model never writes or runs SQL."""
    q = question.lower()
    with get_db() as db:
        match = re.search(r"born (after|before|in)\s+(\d{4})", q)
        if match:
            op = {"after": ">", "before": "<", "in": "="}[match.group(1)]
            rows = db.execute(
                f"SELECT * FROM students WHERE CAST(substr(date_of_birth,1,4) AS INTEGER) {op} ?",
                (int(match.group(2)),),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM students").fetchall()
    return [row_to_student(r) for r in rows]


@app.post("/ask")
def ask(body: Question):
    records = retrieve_context(body.question)
    prompt = (
        "You answer questions about student records. Use ONLY the records below. "
        "If the answer is not in them, say you don't know.\n\n"
        f"Total records provided: {len(records)}\n"
        f"Records (JSON): {json.dumps(records)}\n\n"
        f"Question: {body.question}\nAnswer:"
    )
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            answer = json.loads(resp.read())["response"].strip()
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(
            status_code=503,
            detail="Ollama is not reachable. Start it with 'ollama serve' and run 'ollama pull llama3.2:1b'.",
        )
    return {"question": body.question, "records_used": len(records), "answer": answer}
