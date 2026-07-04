import asyncio
import json
from collections import defaultdict

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


def subscribe(candidate_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers[candidate_id].append(queue)
    return queue


def unsubscribe(candidate_id: str, queue: asyncio.Queue) -> None:
    if queue in _subscribers[candidate_id]:
        _subscribers[candidate_id].remove(queue)


async def publish(candidate_id: str, event: str, data: dict) -> None:
    message = json.dumps(data)
    for queue in list(_subscribers.get(candidate_id, [])):
        await queue.put((event, message))
