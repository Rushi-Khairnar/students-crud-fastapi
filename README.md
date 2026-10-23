# Students Database CRUD API

A Python backend to manage student records (Create, Read, Update, Delete) using **FastAPI** and **SQLite**, with an optional local AI extension using **Ollama**.

> Only dummy data is used. Never commit real student information, passwords or secrets.

## Features
- Full CRUD on `/students` with input validation and clear error codes (404, 409, 422)
- Filtering: by partial name, course, birth year, plus pagination
- SQLite persistence (file `students.db`, created automatically)
- Automated tests (`pytest`)
- Optional `/ask` endpoint: natural-language questions answered by a local Ollama model, grounded in records fetched by safe, fixed queries (the model never runs SQL)

## Prerequisites
- Python 3.10+
- (Optional) [Ollama](https://ollama.com) with the `llama3.2:1b` model

## Installation
```bash
git clone <https://github.com/Rushi-Khairnar/students-crud-fastapi>
cd students-crud
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python seed.py                  # optional: load 5 dummy students
uvicorn main:app --reload
```
Open interactive docs at **http://127.0.0.1:8000/docs** (Swagger UI).

## Run tests
```bash
python -m pytest -q
```

## Student fields
| Field | Required | Notes |
|---|---|---|
| id | auto | unique, auto-generated |
| name | yes | 1-100 chars |
| date_of_birth | yes | `YYYY-MM-DD`, not in the future |
| email | one of email/phone | valid email, unique |
| phone | one of email/phone | 7-15 digits, optional leading `+` |
| course, address, enrollment_date | no | |

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/students` | Create a student |
| GET | `/students` | List / filter (`name`, `course`, `born_after`, `limit`, `offset`) |
| GET | `/students/{id}` | View a student |
| PUT / PATCH | `/students/{id}` | Update details (send only fields to change) |
| DELETE | `/students/{id}` | Delete a student |
| POST | `/ask` | (Optional) Ask the local AI about the data |

## Sample requests (curl)
```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Asha Rao","date_of_birth":"2005-04-10","email":"asha@example.com","course":"Data Science"}'

# List all / filter
curl http://127.0.0.1:8000/students
curl "http://127.0.0.1:8000/students?course=Data%20Science&born_after=2004"

# View one
curl http://127.0.0.1:8000/students/1

# Update
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" \
  -d '{"course":"Statistics"}'

# Delete
curl -X DELETE http://127.0.0.1:8000/students/1
```

## Optional: AI with Ollama
```bash
ollama pull llama3.2:1b
ollama serve                    # keep running in another terminal
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"List students born after 2005"}'
```
How it works: the backend picks matching records with fixed, parameterised queries, sends them to the model as context, and returns the model's answer. If Ollama is not running, `/ask` returns a 503 with instructions.

## Architecture
- `main.py` – FastAPI app, validation models (Pydantic), SQLite access, endpoints
- `seed.py` – inserts dummy data
- `test_main.py` – pytest tests using a temporary database
- Every SQL query is parameterised to prevent SQL injection

## Project structure
```
students-crud/
├── main.py
├── seed.py
├── test_main.py
├── requirements.txt
├── README.md
└── .gitignore
```
