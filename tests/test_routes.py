from io import BytesIO

import pytest

from app import create_app
from app.extensions import db
from app.models import Document


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_dashboard_route_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"MedExtract AI" in response.data


def test_healthcheck_route_loads(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_api_dashboard_summary(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    assert "summary" in response.get_json()


def test_api_upload_rejects_invalid_extension(client):
    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"not-medical"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_document_preview_serves_original_image(app, client, tmp_path):
    image_path = tmp_path / "statement.jpg"
    image_path.write_bytes(b"fake-image")

    with app.app_context():
        document = Document(
            source_file_name="statement.jpg",
            stored_file_path=str(image_path),
            file_type="jpg",
            file_size=image_path.stat().st_size,
            status="processed",
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id

    response = client.get(f"/documents/{document_id}/preview")

    assert response.status_code == 200
    assert response.data == b"fake-image"
    assert response.mimetype == "image/jpeg"


def test_ai_correction_requires_openrouter_key(app, client, tmp_path):
    image_path = tmp_path / "statement.jpg"
    image_path.write_bytes(b"fake-image")

    with app.app_context():
        document = Document(
            source_file_name="statement.jpg",
            stored_file_path=str(image_path),
            file_type="jpg",
            file_size=image_path.stat().st_size,
            status="processed",
            raw_ocr_text="Patient Name: Jane Doe",
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id

    response = client.post(f"/documents/{document_id}/ai-correction", follow_redirects=True)

    assert response.status_code == 200
    assert b"IA nao configurada" in response.data
