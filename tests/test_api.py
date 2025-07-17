def test_admin_page(client):
    """
    Тестирует доступность страницы админ-панели.

    Проверяется:
    - статус ответа 200 OK;
    - наличие в HTML текста 'Панель администратора'.
    """
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Панель администратора" in response.text


def test_progress_check(client):
    """
    Тестирует эндпоинт получения прогресса обновления.

    Проверяется:
    - статус ответа 200 OK;
    - в ответе JSON присутствуют ключи 'progress' и 'status'.
    """
    response = client.get("/admin/progress")
    assert response.status_code == 200
    data = response.json()
    assert "progress" in data
    assert "status" in data


def test_update_trigger(client):
    """
    Тестирует запуск фонового процесса обновления данных.

    Проверяется:
    - статус ответа 200 OK;
    - в JSON-ответе есть ключ 'message', подтверждающий запуск процесса.
    """
    response = client.post("/admin/update")
    assert response.status_code == 200
    assert "message" in response.json()