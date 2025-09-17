# threading_utils.py
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from typing import Callable, Any

class WorkerSignals(QObject):
    success = pyqtSignal(object)   # émet la valeur de retour
    error = pyqtSignal(str)        # émet message d'erreur
    finished = pyqtSignal()        # indique la fin (utile pour UI cleanup)

class Worker(QRunnable):
    """
    QRunnable simple qui appelle `fn(*args, **kwargs)` dans un thread séparé.
    Émet success(result) ou error(str).
    """
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.success.emit(res)
        except Exception as e:
            # format simple de l'erreur
            try:
                msg = str(e)
            except Exception:
                msg = "Unknown error"
            self.signals.error.emit(msg)
        finally:
            self.signals.finished.emit()

# helper singleton for convenience
_thread_pool = QThreadPool.globalInstance()

def run_in_thread(fn: Callable, on_success: Callable[[Any], None]=None,
                  on_error: Callable[[str], None]=None, on_finished: Callable[[], None]=None,
                  *args, **kwargs):
    worker = Worker(fn, *args, **kwargs)
    if on_success:
        worker.signals.success.connect(on_success)
    if on_error:
        worker.signals.error.connect(on_error)
    if on_finished:
        worker.signals.finished.connect(on_finished)
    _thread_pool.start(worker)
    return worker
