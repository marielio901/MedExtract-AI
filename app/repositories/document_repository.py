from app.extensions import db
from app.models import Document


class DocumentRepository:
    @staticmethod
    def create(**kwargs):
        document = Document(**kwargs)
        db.session.add(document)
        db.session.commit()
        return document

    @staticmethod
    def get(document_id):
        return Document.query.get(document_id)

    @staticmethod
    def get_or_404(document_id):
        return Document.query.get_or_404(document_id)

    @staticmethod
    def list_all(status=None, query=None):
        documents = Document.query
        if status:
            documents = documents.filter(Document.status == status)
        if query:
            like = f"%{query}%"
            documents = documents.filter(Document.source_file_name.ilike(like))
        return documents.order_by(Document.created_at.desc()).all()

    @staticmethod
    def update(document, **kwargs):
        for key, value in kwargs.items():
            setattr(document, key, value)
        db.session.commit()
        return document

    @staticmethod
    def delete(document):
        db.session.delete(document)
        db.session.commit()
