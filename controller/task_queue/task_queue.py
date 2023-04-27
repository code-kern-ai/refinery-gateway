from threading import Lock, Thread
from typing import List, Tuple, Dict, Any, Callable, Optional
from uuid import uuid4
import os
import time
from submodules.model.models import TaskQueue as TaskQueueDBObj
from . import manager  # import parse_task_to_dict, get_task_function_by_type
from submodules.model.business_objects import general, task_queue as task_queue_db_bo
import traceback


# custom class wrapping a list in order to make it thread safe
class ThreadSafeList:
    def __init__(self):
        self._list = list()
        self._lock = Lock()

    def append(self, value):
        with self._lock:
            self._list.append(value)

    def extend(self, value):
        with self._lock:
            self._list.extend(value)

    def pop(self, index=-1):
        with self._lock:
            return self._list.pop(index)

    def get(self, index: int):
        with self._lock:
            return self._list[index]

    def length(self):
        with self._lock:
            return len(self._list)

    def print(self):
        with self._lock:
            return print(self._list, flush=True)


class CustomTaskQueue:
    class TaskInfo:
        def __init__(
            self,
            task: TaskQueueDBObj,
            start_function: Callable[[Dict[str, Any]], bool],
            check_finished_function: Callable[[Dict[str, Any]], bool],
            check_every: int,
        ):
            self.task_dict = manager.parse_task_to_dict(task)
            self.start_function = start_function
            self.check_finished_function = check_finished_function
            self.check_every = check_every

    def __init__(self, max_normal: int, max_priority: int):
        self._lock = Lock()
        self._max_normal = max_normal
        self._fifo_queue_normal = ThreadSafeList()
        self._active_normal = ThreadSafeList()
        self._max_priority = max_priority
        self._fifo_queue_priority = ThreadSafeList()
        self._active_priority = ThreadSafeList()
        self._checker_thread = Thread(
            target=self.__thread_checker,
            daemon=True,
        )
        self._checker_thread.start()

    def add_task(
        self,
        task: TaskQueueDBObj,
        start_function: Callable[[Dict[str, Any]], bool],
        check_finished_function: Callable[[Dict[str, Any]], bool],
        check_every: int = 1,
    ):
        with self._lock:
            active = self._active_priority if task.priority else self._active_normal
            max = self._max_priority if task.priority else self._max_normal

            task_info = self.TaskInfo(
                task, start_function, check_finished_function, check_every
            )
            add_to_prio = task.priority
            # ensure prio tasks can be added to none prio queue if fits
            if active.length() >= max:
                if task.priority and self._active_normal.length() < self._max_normal:
                    add_to_prio = False
                else:
                    append_to = (
                        self._fifo_queue_priority
                        if task.priority
                        else self._fifo_queue_normal
                    )
                    append_to.append(task_info)
                    return
            self.__start_task(task_info, add_to_prio)

    def __start_task(self, task_info: TaskInfo, to_prio: bool) -> bool:
        if not task_info:
            return False

        active = self._active_priority if to_prio else self._active_normal
        # since multiple gateway container can exist the start can "fail" if the task is already active
        if not task_info.start_function(task_info.task_dict):
            return False
        active.append(task_info)
        task_info.task_dict["is_active"] = True
        return True

    def __thread_checker(self):
        ctx_token = general.get_ctx_token()

        seconds = 0
        while True:
            seconds += 1
            if seconds >= 120:
                seconds = 0
                ctx_token = general.remove_and_refresh_session(ctx_token, True)
            try:
                self.__check_task_queue(True, seconds)
                self.__check_task_queue(False, seconds)
            except:
                print(traceback.format_exc(), flush=True)
            time.sleep(1)

    def __check_task_queue(self, priority: bool, seconds: int):
        to_check = self._active_priority if priority else self._active_normal

        to_remove = []
        for idx in range(to_check.length()):
            task = to_check.get(idx)
            if seconds % task.check_every == 0:
                if task.check_finished_function(task.task_dict):
                    task.task_dict["is_active"] = False
                    to_remove.append(idx)

        # cleanup
        for idx in reversed(to_remove):
            finished = to_check.pop(idx)
            task_queue_db_bo.remove_task_from_queue(
                finished.task_dict["project_id"], finished.task_dict["id"]
            )
            next_task, p = None, False
            while not self.__start_task(next_task, p):
                next_task, p = self.__get_next_item(priority)
                if not next_task:
                    break
        if len(to_remove) > 0:
            general.commit()

    def __get_next_item(self, priority: bool) -> Tuple[TaskInfo, bool]:
        # normal queue can solve priority tasks but not the other way around
        if priority:
            if self._fifo_queue_priority.length() > 0:
                return self._fifo_queue_priority.pop(0), True
        else:
            if self._fifo_queue_normal.length() > 0:
                return self._fifo_queue_normal.pop(0), False
            if self._fifo_queue_priority.length() > 0:
                return self._fifo_queue_priority.pop(0), False
        return None, False


task_queue = None


def init_task_queue() -> CustomTaskQueue:
    global task_queue
    # init task queue class
    max_normal = int(os.getenv("TASK_QUEUE_SLOTS", "2"))
    max_priority = int(os.getenv("PRIORITY_TASK_QUEUE_SLOTS", "1"))
    task_queue = CustomTaskQueue(max_normal, max_priority)

    # reset old tasks that weren't finished properly
    task_queue_db_bo.set_all_tasks_inactive(True)

    # queue tasks
    existing_tasks = task_queue_db_bo.get_all_tasks()
    for task in existing_tasks:
        start_func, check_func, check_every = manager.get_task_function_by_type(
            task.type
        )
        task_queue.add_task(task, start_func, check_func, check_every)
    return task_queue


def get_task_queue() -> CustomTaskQueue:
    global task_queue
    if task_queue is None:
        raise Exception("Task queue not initialized")

    return task_queue
