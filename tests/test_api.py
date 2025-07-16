def test_admin_page(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Панель администратора" in response.text

def test_progress_check(client):
    response = client.get("/admin/progress")
    assert response.status_code == 200
    data = response.json()
    assert "progress" in data
    assert "status" in data

def test_update_trigger(client):
    response = client.post("/admin/update")
    assert response.status_code == 200
    assert "message" in response.json()