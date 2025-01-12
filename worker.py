import argparse

from rq import Worker

from app.core.logger import logger
from app.core.queue import QUEUE


def start_worker(queue_names: list[str] | None = None) -> None:
    """
    Start a worker that listens to specified queues
    If no queues specified, listen to all queues
    """
    queue_list = [QUEUE[queue_name] for queue_name in (queue_names or QUEUE.keys())]
    worker = Worker(queue_list)

    logger.info(
        f"Starting worker listening to queues: {', '.join(queue_names or QUEUE.keys())}"
    )
    worker.work()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RQ worker with specified queues")
    parser.add_argument(
        "queues",
        nargs="*",
        default=list(QUEUE.keys()),
        help="Queue names to process (space-separated)",
    )

    args = parser.parse_args()
    start_worker(args.queues)
