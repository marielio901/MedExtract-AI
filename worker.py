import os
import signal
import threading

from app import create_app


stop_event = threading.Event()


def _handle_shutdown(signum, frame):
    stop_event.set()


signal.signal(signal.SIGINT, _handle_shutdown)
signal.signal(signal.SIGTERM, _handle_shutdown)

os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("ENABLE_BACKGROUND_WORKER", "true")

app = create_app(os.getenv("FLASK_ENV", "production"))


if __name__ == "__main__":
    while not stop_event.wait(1):
        pass
