import pytest
from app import create_app
from app.extensions import db
from app.services.batch_processing_service import BatchProcessingService


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_queue_document_adds_to_queue(app):
    with app.app_context():
        # Ensure queue is clean
        while not BatchProcessingService._queue.empty():
            BatchProcessingService._queue.get()
            BatchProcessingService._queue.task_done()

        assert BatchProcessingService._queue.empty()

        # Queue a dummy document id
        BatchProcessingService.queue_document(42)

        # Verify it was added
        assert not BatchProcessingService._queue.empty()
        queued_id = BatchProcessingService._queue.get()
        assert queued_id == 42
        BatchProcessingService._queue.task_done()
