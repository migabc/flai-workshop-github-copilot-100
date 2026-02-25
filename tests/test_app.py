"""
Tests for the Mergington High School Activities API.

Structured using the AAA (Arrange-Act-Assert) pattern.
"""

import copy
import pytest
import src.app as app_module
from fastapi.testclient import TestClient
from src.app import app

# Snapshot of the original activities taken at import time.
# Used by reset_activities to restore clean state before each test.
_original_activities = copy.deepcopy(app_module.activities)


@pytest.fixture(scope="session")
def client():
    """A TestClient that persists for the entire test session."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_activities():
    """Restore the in-memory activities store before every test."""
    app_module.activities.clear()
    app_module.activities.update(copy.deepcopy(_original_activities))


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_redirects_to_index(self, client):
        # Arrange – no setup needed; default app state is sufficient

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


# ---------------------------------------------------------------------------
# GET /activities
# ---------------------------------------------------------------------------

class TestGetActivities:
    def test_returns_200_with_all_activities(self, client):
        # Arrange – default seeded data (9 activities)

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9

    def test_each_activity_has_required_fields(self, client):
        # Arrange
        required_keys = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")

        # Assert
        data = response.json()
        for name, details in data.items():
            assert required_keys.issubset(details.keys()), (
                f"Activity '{name}' is missing required fields"
            )

    def test_participants_is_a_list(self, client):
        # Arrange – nothing extra needed

        # Act
        response = client.get("/activities")

        # Assert
        data = response.json()
        for name, details in data.items():
            assert isinstance(details["participants"], list), (
                f"Activity '{name}' participants should be a list"
            )


# ---------------------------------------------------------------------------
# POST /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_success(self, client):
        # Arrange
        activity = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity}/signup?email={email}")

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]
        participants = client.get("/activities").json()[activity]["participants"]
        assert email in participants

    def test_signup_unknown_activity_returns_404(self, client):
        # Arrange
        activity = "Unknown Activity"
        email = "student@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity}/signup?email={email}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_email_returns_400(self, client):
        # Arrange – sign up once first
        activity = "Chess Club"
        email = "duplicate@mergington.edu"
        client.post(f"/activities/{activity}/signup?email={email}")

        # Act – sign up again with the same email
        response = client.post(f"/activities/{activity}/signup?email={email}")

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"

    def test_signup_full_activity_returns_400(self, client):
        # Arrange – fill Chess Club (max_participants=12; 2 pre-seeded)
        activity = "Chess Club"
        for i in range(10):
            client.post(f"/activities/{activity}/signup?email=filler{i}@mergington.edu")

        # Act – try to add one more beyond the limit
        response = client.post(f"/activities/{activity}/signup?email=overflow@mergington.edu")

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is full"


# ---------------------------------------------------------------------------
# DELETE /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

class TestUnregister:
    def test_unregister_success(self, client):
        # Arrange – Chess Club is pre-seeded with michael@mergington.edu
        activity = "Chess Club"
        email = "michael@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity}/signup?email={email}")

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]
        participants = client.get("/activities").json()[activity]["participants"]
        assert email not in participants

    def test_unregister_unknown_activity_returns_404(self, client):
        # Arrange
        activity = "Nonexistent Club"
        email = "michael@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity}/signup?email={email}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_enrolled_returns_404(self, client):
        # Arrange
        activity = "Chess Club"
        email = "notenrolled@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity}/signup?email={email}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not signed up for this activity"
