"""Insert DUMMY students (fake data only) so you can try the API quickly."""
from main import get_db, init_db

DUMMY = [
    ("Aarav Sharma", "2004-03-12", "aarav@example.com", "9000000001", "Data Science"),
    ("Diya Patil", "2006-07-25", "diya@example.com", "9000000002", "Computer Science"),
    ("Kabir Singh", "2005-11-02", "kabir@example.com", None, "Data Science"),
    ("Meera Nair", "2007-01-18", None, "9000000004", "Statistics"),
    ("Rohan Desai", "2003-09-30", "rohan@example.com", "9000000005", "Computer Science"),
]

init_db()
with get_db() as db:
    for name, dob, email, phone, course in DUMMY:
        db.execute(
            "INSERT OR IGNORE INTO students (name, date_of_birth, email, phone, course) VALUES (?,?,?,?,?)",
            (name, dob, email, phone, course),
        )
print("Seeded dummy students.")
