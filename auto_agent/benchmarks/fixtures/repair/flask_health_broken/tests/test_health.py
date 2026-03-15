# Test Health Endpoint
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test health endpoint returns 200"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_status_endpoint(client):
    """Test status endpoint returns health status"""
    response = client.get('/api/status')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
