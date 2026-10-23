import os

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    main.init_db()
    return TestClient(main.app)


STUDENT = {"name": "Test User", "date_of_birth": "2004-05-05", "email": "t@example.com"}


def test_full_crud(client):
    r = client.post("/students", json=STUDENT)
    assert r.status_code == 201
    sid = r.json()["id"]

    assert client.get("/students").json()[0]["id"] == sid
    assert client.get(f"/students/{sid}").json()["name"] == "Test User"

    r = client.patch(f"/students/{sid}", json={"course": "Data Science"})
    assert r.status_code == 200 and r.json()["course"] == "Data Science"

    assert client.delete(f"/students/{sid}").status_code == 200
    assert client.get(f"/students/{sid}").status_code == 404


def test_validation(client):
    assert client.post("/students", json={"name": "X", "date_of_birth": "2004-01-01"}).status_code == 422
    assert client.post("/students", json={**STUDENT, "email": "bad"}).status_code == 422
    assert client.post("/students", json={**STUDENT, "date_of_birth": "2999-01-01"}).status_code == 422


def test_duplicate_email_and_missing(client):
    client.post("/students", json=STUDENT)
    assert client.post("/students", json=STUDENT).status_code == 409
    assert client.put("/students/999", json={"name": "Z"}).status_code == 404
    assert client.delete("/students/999").status_code == 404


def test_filters(client):
    client.post("/students", json=STUDENT)
    client.post("/students", json={"name": "Young One", "date_of_birth": "2007-02-02", "phone": "9000000009"})
    assert len(client.get("/students?born_after=2005").json()) == 1
    assert len(client.get("/students?name=Test").json()) == 1
