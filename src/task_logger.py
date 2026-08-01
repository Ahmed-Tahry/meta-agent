import os
from contextvars import ContextVar
from datetime import UTC, datetime

LOG_DIR = "logs"
current_task_id: ContextVar[str] = ContextVar("current_task_id", default="")


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class TaskLogger:
    def __init__(self, task_id: str, goal: str) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)
        self.task_id = task_id
        self.goal = goal
        self.path = os.path.join(LOG_DIR, f"{task_id}.log")
        self._file = open(self.path, "w", encoding="utf-8")
        self._write_line("=" * 70)
        self._write_line(f"PIPELINE START  |  task_id={task_id}")
        self._write_line(f"GOAL            |  {goal}")
        self._write_line("=" * 70)
        self._write_line("")
        self._file.flush()

    def _write_line(self, text: str = "") -> None:
        self._file.write(text + "\n")

    def log(self, section: str, message: str, detail: str | None = None) -> None:
        self._write_line(f"--- [{_ts()}] {section} ---")
        if message:
            self._write_line(f"    {message}")
        if detail:
            for line in detail.strip().split("\n"):
                self._write_line(f"    {line}")
        self._write_line("")

    def log_multiline(self, section: str, message: str, body: str) -> None:
        self._write_line(f"--- [{_ts()}] {section} ---")
        if message:
            self._write_line(f"    {message}")
        self._write_line("    " + "-" * 60)
        for line in body.strip().split("\n"):
            self._write_line(f"    | {line}")
        self._write_line("    " + "-" * 60)
        self._write_line("")

    def close(self) -> None:
        self._write_line("=" * 70)
        self._write_line(f"PIPELINE END    |  task_id={self.task_id}")
        self._write_line("=" * 70)
        self._file.flush()
        self._file.close()


_loggers: dict[str, TaskLogger] = {}


def get_logger(task_id: str, goal: str = "") -> TaskLogger:
    existing = _loggers.get(task_id)
    if existing:
        return existing
    logger = TaskLogger(task_id, goal)
    _loggers[task_id] = logger
    return logger


def get_current_logger() -> TaskLogger | None:
    task_id = current_task_id.get()
    if not task_id:
        return None
    return _loggers.get(task_id)


def close_logger(task_id: str) -> None:
    logger = _loggers.pop(task_id, None)
    if logger:
        logger.close()
