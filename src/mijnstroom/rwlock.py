from contextlib import contextmanager
from threading import RLock


class RWLock:
    def __init__(self):
        self._w = RLock()
        self._r = RLock()
        self.readers = 0

    @contextmanager
    def lock_for_read(self):
        try:
            self._reader_acquire()
            yield
        finally:
            self._reader_release()

    @contextmanager
    def lock_for_write(self):
        try:
            self._w.acquire()
            yield
        finally:
            self._w.release()

    def _reader_acquire(self):
        with self._r:
            self.readers += 1
            if self.readers == 1:
                self._w.acquire()

    def _reader_release(self):
        with self._r:
            self.readers -= 1
            if self.readers == 0:
                self._w.release()
