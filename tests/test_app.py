import pytest
from app import app

def test_home_page():
    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200
    assert b'Login' in response.data
