import logging
import threading
from queue import Empty, Queue
from app.extensions import db
from app.repositories import DocumentRepository
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)


class BatchProcessingService:
    _queue = Queue()
    _worker_thread = None
    _lock = threading.Lock()
    _app = None

    @classmethod
    def initialize(cls, app):
        """Initializes the background worker and enqueues any pending documents for recovery."""
        with cls._lock:
            if cls._worker_thread is None:
                cls._app = app
                cls._worker_thread = threading.Thread(
                    target=cls._worker_loop, name="BatchProcessingWorker", daemon=True
                )
                cls._worker_thread.start()
                logger.info("Batch processing background worker started.")
                cls._recover_pending_documents(app)

    @classmethod
    def queue_document(cls, document_id):
        """Queues a document ID to be processed by the background thread."""
        cls._queue.put(document_id)
        logger.info(f"Document {document_id} queued for background processing.")

    @classmethod
    def _worker_loop(cls):
        if not cls._app:
            return

        while True:
            from_queue = False
            try:
                try:
                    document_id = cls._queue.get(timeout=cls._poll_seconds())
                    from_queue = True
                except Empty:
                    document_id = cls._next_pending_document_id()
                    if document_id is None:
                        continue

                with cls._app.app_context():
                    cls._process_single_document(document_id)
            except Exception as exc:
                logger.exception("Error in BatchProcessingWorker loop.")
            finally:
                if from_queue:
                    cls._queue.task_done()

    @classmethod
    def _poll_seconds(cls):
        if not cls._app:
            return 5.0
        return float(cls._app.config.get("BACKGROUND_WORKER_POLL_SECONDS", 5.0))

    @classmethod
    def _recover_pending_documents(cls, app):
        try:
            with app.app_context():
                from app.models import Document
                pending_docs = (
                    Document.query.filter_by(status="pending")
                    .order_by(Document.created_at.asc())
                    .all()
                )
                for doc in pending_docs:
                    cls.queue_document(doc.id)
                if pending_docs:
                    logger.info(
                        f"Enqueued {len(pending_docs)} existing pending documents on startup for recovery."
                    )
        except Exception:
            logger.exception("Failed to recover pending documents on startup.")

    @classmethod
    def _next_pending_document_id(cls):
        if not cls._app:
            return None
        try:
            with cls._app.app_context():
                from app.models import Document
                document = (
                    Document.query.filter_by(status="pending")
                    .order_by(Document.created_at.asc())
                    .first()
                )
                return document.id if document else None
        except Exception:
            logger.exception("Failed to poll pending documents.")
            return None

    @classmethod
    def _process_single_document(cls, document_id):
        logger.info(f"Background worker starting processing of document {document_id}.")
        # Retrieve the document in the current session
        document = DocumentRepository.get(document_id)
        if not document:
            logger.warning(f"Document {document_id} not found, skipping background processing.")
            return

        if document.status != "pending":
            logger.info(
                f"Document {document_id} is already in status '{document.status}', skipping background processing."
            )
            return

        try:
            extraction_service = ExtractionService(cls._app.config)
            extraction_service.process_document(document)
            logger.info(f"Document {document_id} successfully processed in background.")
        except Exception as exc:
            logger.exception(f"Background processing failed for document {document_id}: {exc}")
            # Ensure status is updated to error if not done already
            try:
                db.session.refresh(document)
                if document.status == "pending":
                    DocumentRepository.update(document, status="error", error_message=str(exc))
            except Exception as inner_exc:
                logger.exception(
                    f"Failed to update document {document_id} error status: {inner_exc}"
                )
