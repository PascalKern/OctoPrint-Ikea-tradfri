import asyncio
import concurrent
import logging
import concurrent.futures
import threading
import uuid
from asyncio import AbstractEventLoop, BaseEventLoop
from typing import Optional, Coroutine


class ThreadedWorker:

    def __init__(self, logger=logging.getLogger(__name__)):
        # self._loop: Optional[BaseEventLoop] = None  # TODO Why does this (currently) break the things!?
        self.TIMEOUT_IN_SEC = 0.1
        self._logger = logger
        self._is_running = False
        self._init_thread()

    def _init_thread(self):
        self.name = f"{ThreadedWorker.__name__}-{uuid.uuid1().hex[:4]}"
        self._thread = threading.Thread(target=self._run, name=self.name)
        self._thread.daemon = True
        self._thread.start()

    def _run(self):
        self._logger.debug(f"Starting the loop on worker thread: {self.name}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=2))
        self._logger.debug(f"1 Still self is: {self.name} - {self.__class__.__name__}")
        self._loop = loop
        self._logger.debug(f"Created loop from worker thread and added to asyncio! Now running forever")
        self._logger.debug(f"2 Still self is: {self.name} - {self.__class__.__name__}")
        self._is_running = True
        loop.run_forever()
        self._logger.debug(f"Loop run forever - SHOULD NEVER BE SEEN! :)")

    def is_initializing(self):
        _retry_counter = 10
        if _retry_counter > 0:
            _retry_counter -= 1
            return not hasattr(self, '_loop')
        raise ThreadedWorkerException(f"Retried 10 times to get running loop!")

    def get_loop(self) -> AbstractEventLoop:
        if self._is_running and hasattr(self, '_loop') and self._loop is None:
            raise ThreadedWorkerException(f"The current worker ({self.name}) does not have a loop available!")
        if not self._loop.is_running():
            raise ThreadedWorkerException(f"The current worker ({self.name}) is not Running!")
        return self._loop

    def close(self):
        if self._is_running:
            try:
                pending = asyncio.all_tasks(self._loop)
                self._logger.debug(f"Worker in close has {len(pending)} pending tasks!")
                self._loop.stop()  # Should also close underlying thread?!
            except Exception as e:
                self._logger.error(f"Could not close the loop on thread: {self._thread.name}", e)
            finally:
                self._is_running = False
                # self._loop = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ThreadedWorkerException(Exception):
    pass
