import sys
import threading
import queue


class ThreadSafeConsole(object):
    """
    A thread-safe file-like object to replace sys.stdout and sys.stderr.
    It writes to a queue that the main GUI thread reads from.
    """

    def __init__(self, callback):
        self.callback = callback
        self.queue = queue.Queue()
        self._start_reader()

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass

    def _start_reader(self):
        def reader():
            while True:
                msg = self.queue.get()
                if msg is None:
                    break
                self.callback(msg)
                self.queue.task_done()

        t = threading.Thread(target=reader, daemon=True)
        t.start()
