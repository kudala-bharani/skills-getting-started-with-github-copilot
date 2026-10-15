from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(app_module.activities))
    with TestClient(app_module.app, follow_redirects=False) as test_client:
        yield test_client


def test_root_redirects_to_static_index(client):
    # Arrange
    path = "/"

    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data(client):
    # Arrange
    path = "/activities"

    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == 200
    assert "Chess Club" in response.json()
    assert "participants" in response.json()["Chess Club"]


def test_signup_adds_participant(client):
    # Arrange
    activity = "Basketball Team"
    email = "student@mergington.edu"
    path = f"/activities/{quote(activity, safe='')}/signup"

    # Act
    response = client.post(path, params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity}"}
    assert email in activities_response.json()[activity]["participants"]


def test_signup_rejects_unknown_activity(client):
    # Arrange
    path = f"/activities/{quote('Unknown Activity', safe='')}/signup"

    # Act
    response = client.post(path, params={"email": "student@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity = "Chess Club"
    email = "michael@mergington.edu"
    path = f"/activities/{quote(activity, safe='')}/signup"

    # Act
    response = client.post(path, params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up for this activity"


def test_signup_requires_email(client):
    # Arrange
    path = f"/activities/{quote('Basketball Team', safe='')}/signup"

    # Act
    response = client.post(path)

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]


def test_unregister_removes_participant(client):
    # Arrange
    activity = "Basketball Team"
    email = "student@mergington.edu"
    path = f"/activities/{quote(activity, safe='')}/signup"
    client.post(path, params={"email": email})

    # Act
    response = client.delete(path, params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from {activity}"}
    assert email not in activities_response.json()[activity]["participants"]


def test_unregister_rejects_unknown_activity(client):
    # Arrange
    path = f"/activities/{quote('Unknown Activity', safe='')}/signup"

    # Act
    response = client.delete(path, params={"email": "student@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_unregistered_participant(client):
    # Arrange
    activity = "Basketball Team"
    path = f"/activities/{quote(activity, safe='')}/signup"

    # Act
    response = client.delete(path, params={"email": "student@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregister_requires_email(client):
    # Arrange
    path = f"/activities/{quote('Basketball Team', safe='')}/signup"

    # Act
    response = client.delete(path)

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]


def test_signup_unregister_round_trip_updates_activity_data(client):
    # Arrange
    activity = "Basketball Team"
    email = "student@mergington.edu"
    path = f"/activities/{quote(activity, safe='')}/signup"

    # Act
    signup_response = client.post(path, params={"email": email})
    signed_up_activity = client.get("/activities").json()[activity]
    unregister_response = client.delete(path, params={"email": email})
    unregistered_activity = client.get("/activities").json()[activity]

    # Assert
    assert signup_response.status_code == 200
    assert email in signed_up_activity["participants"]
    assert unregister_response.status_code == 200
    assert email not in unregistered_activity["participants"]