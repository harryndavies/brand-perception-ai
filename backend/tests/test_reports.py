from unittest.mock import patch, MagicMock

from app.models.report import Report


def test_list_reports_empty(client, auth_headers):
    response = client.get("/api/reports", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_reports(client, auth_headers, test_user, session):
    report = Report(user_id=test_user.id, brand="Nike", competitors=["Adidas"], status="complete")
    session.add(report)
    session.commit()

    response = client.get("/api/reports", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["brand"] == "Nike"


def test_get_report(client, auth_headers, test_user, session):
    report = Report(user_id=test_user.id, brand="Nike", competitors=[], status="complete")
    session.add(report)
    session.commit()
    session.refresh(report)

    response = client.get(f"/api/reports/{report.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["brand"] == "Nike"


def test_get_report_not_found(client, auth_headers):
    response = client.get("/api/reports/nonexistent", headers=auth_headers)
    assert response.status_code == 404


def test_get_report_unauthorized(client):
    response = client.get("/api/reports/some-id")
    assert response.status_code in (401, 403)


@patch("app.routes.reports.run_analysis")
def test_create_report(mock_analysis, client, auth_headers):
    response = client.post("/api/reports", headers=auth_headers, json={
        "brand": "Tesla",
        "competitors": ["Ford", "BMW"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["brand"] == "Tesla"
    assert data["competitors"] == ["Ford", "BMW"]
    assert data["status"] == "processing"


@patch("app.routes.reports.run_analysis")
def test_create_report_limits_competitors(mock_analysis, client, auth_headers):
    response = client.post("/api/reports", headers=auth_headers, json={
        "brand": "Tesla",
        "competitors": ["A", "B", "C", "D"],
    })
    assert response.status_code == 201
    assert len(response.json()["competitors"]) == 3


def test_list_reports_isolation(client, auth_headers, test_user, session):
    """Reports from other users should not be visible."""
    from app.core.auth import hash_password
    from app.models.user import User

    other = User(name="Other", email="other@example.com", hashed_password=hash_password("pass"))
    session.add(other)
    session.commit()
    session.refresh(other)

    report = Report(user_id=other.id, brand="Secret", competitors=[], status="complete")
    session.add(report)
    session.commit()

    response = client.get("/api/reports", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0
