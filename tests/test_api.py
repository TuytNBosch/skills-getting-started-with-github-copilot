"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Check Chess Club details
        chess_club = data["Chess Club"]
        assert chess_club["description"] == "Learn strategies and compete in chess tournaments"
        assert chess_club["max_participants"] == 12
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]

    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=alice@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up alice@mergington.edu for Chess Club"
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alice@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_user(self, client):
        """Test that signing up the same user twice fails"""
        email = "bob@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response2.status_code == 400
        assert response2.json()["detail"] == "Student already signed up"

    def test_signup_activity_not_found(self, client):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/NonExistentActivity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_activity_full(self, client):
        """Test signing up when activity is full"""
        # Create a small activity with 2 max participants and fill it
        activities["Small Club"] = {
            "description": "A small club",
            "schedule": "Anytime",
            "max_participants": 2,
            "participants": ["user1@mergington.edu", "user2@mergington.edu"]
        }
        
        response = client.post(
            "/activities/Small%20Club/signup?email=user3@mergington.edu"
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is full"

    def test_signup_multiple_activities(self, client):
        """Test that a user can sign up for multiple activities"""
        email = "multi@mergington.edu"
        
        response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Programming%20Class/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify user is in both activities
        activities_data = client.get("/activities").json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"
        
        # Verify user is initially registered
        activities_data = client.get("/activities").json()
        assert email in activities_data["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Unregistered {email} from Chess Club"
        
        # Verify user was removed
        activities_data = client.get("/activities").json()
        assert email not in activities_data["Chess Club"]["participants"]

    def test_unregister_activity_not_found(self, client):
        """Test unregistering from a non-existent activity"""
        response = client.delete(
            "/activities/NonExistentActivity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_user_not_registered(self, client):
        """Test unregistering a user who is not registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student is not registered for this activity"

    def test_unregister_and_resign_up(self, client):
        """Test that a user can unregister and then sign up again"""
        email = "michael@mergington.edu"
        
        # Unregister
        response1 = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert response1.status_code == 200
        
        # Sign up again
        response2 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify user is registered again
        activities_data = client.get("/activities").json()
        assert email in activities_data["Chess Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity management"""

    def test_capacity_tracking(self, client):
        """Test that capacity is properly tracked"""
        activities_data = client.get("/activities").json()
        chess_club = activities_data["Chess Club"]
        
        max_participants = chess_club["max_participants"]
        current_participants = len(chess_club["participants"])
        spots_available = max_participants - current_participants
        
        assert spots_available > 0
        assert current_participants == 2
        assert max_participants == 12

    def test_fill_activity_to_capacity(self, client):
        """Test filling an activity to capacity"""
        # Create activity with 3 max participants and 2 current
        activities["Test Activity"] = {
            "description": "Test",
            "schedule": "Test",
            "max_participants": 3,
            "participants": ["user1@mergington.edu", "user2@mergington.edu"]
        }
        
        # Add one more participant (should succeed)
        response1 = client.post(
            "/activities/Test%20Activity/signup?email=user3@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Try to add another (should fail)
        response2 = client.post(
            "/activities/Test%20Activity/signup?email=user4@mergington.edu"
        )
        assert response2.status_code == 400
        assert response2.json()["detail"] == "Activity is full"


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_email_with_special_characters(self, client):
        """Test signup with special characters in email"""
        email = "test+special@mergington.edu"
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 200

    def test_activity_name_with_spaces(self, client):
        """Test that activity names with spaces work correctly"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200

    def test_empty_participants_list(self, client):
        """Test activity with no participants"""
        activities["Empty Activity"] = {
            "description": "No participants yet",
            "schedule": "TBD",
            "max_participants": 10,
            "participants": []
        }
        
        activities_data = client.get("/activities").json()
        assert len(activities_data["Empty Activity"]["participants"]) == 0
