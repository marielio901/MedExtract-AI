from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename


class FileService:
    def __init__(self, config):
        self.config = config

    def _config_value(self, key):
        if hasattr(self.config, key):
            return getattr(self.config, key)
        return self.config[key]

    def allowed_file(self, filename):
        return (
            "." in filename
            and self.extension(filename) in self._config_value("ALLOWED_EXTENSIONS")
        )

    @staticmethod
    def extension(filename):
        return filename.rsplit(".", 1)[1].lower()

    def save_upload(self, file_storage):
        original_name = secure_filename(file_storage.filename or "")
        if not original_name or not self.allowed_file(original_name):
            raise ValueError("Tipo de arquivo nao permitido.")

        upload_dir = Path(self._config_value("UPLOAD_ORIGINAL_FOLDER"))
        upload_dir.mkdir(parents=True, exist_ok=True)

        ext = self.extension(original_name)
        stored_name = f"{uuid4().hex}_{original_name}"
        destination = upload_dir / stored_name
        file_storage.save(destination)

        return {
            "source_file_name": original_name,
            "stored_file_path": str(destination),
            "file_type": ext,
            "file_size": destination.stat().st_size,
        }

    @staticmethod
    def delete_file(path):
        if path:
            file_path = Path(path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
