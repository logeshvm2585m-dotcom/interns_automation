import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['mode'] == 'demo'

def test_seeded_candidates(client):
    response = client.get('/api/candidates')
    assert response.status_code == 200
    assert [item['candidate_id'] for item in response.json()] == [f'INT{i:03}' for i in range(2, 9)] + ['INT009']

def test_dashboard_is_database_backed(client):
    response = client.get('/api/dashboard')
    assert response.status_code == 200
    assert response.json()['total_candidates'] == 8
    assert response.json()['upcoming_reviews'] == 6

def test_demo_feedback_requires_review_and_stays_pending(client):
    response = client.post('/api/feedback/1/generate')
    assert response.status_code == 200
    assert response.json()['status'] == 'pending_approval'
    assert response.json()['demo_generated'] is True

def test_simulated_email_never_reports_sent(client):
    response = client.post('/api/emails/simulate/INT003')
    assert response.status_code == 200
    assert response.json()['status'] == 'simulated'
    assert response.json()['integration_mode'] == 'demo'
