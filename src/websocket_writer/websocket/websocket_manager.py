import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import websockets

from . import auth_manager
from ..settings import settings

logger = logging.getLogger(__name__)


class WebSocketClient:
    def __init__(self, on_message, worker_stack_size=5):
        self.on_message = on_message
        self.worker_stack_size = worker_stack_size

        self.main_topic = settings.stomp.main_topic
        self.sub_topic = settings.stomp.sub_topic
        self.single_topic = False
        if not self.sub_topic:
            self.single_topic = True

        self.ws = None
        self.connected = asyncio.Event()

        self.message_queue = asyncio.Queue(maxsize=max(100, worker_stack_size * 100))

        self.subscription_queue = asyncio.Queue(maxsize=worker_stack_size * 10)
        self.subscription_live = set()
        self.subscription_live_lock = asyncio.Lock()

        self.executor = ThreadPoolExecutor(max_workers=max(1, worker_stack_size))

    async def run(self):
        for i in range(max(1, self.worker_stack_size)):
            asyncio.create_task(self.message_queue_consumer())

        asyncio.create_task(self.subscription_queue_consumer())
        # VBO to remove@
        asyncio.create_task(self.test_publisher_worker())

        while True:
            try:
                _drain_queue(self.subscription_queue)
                _drain_queue(self.message_queue)
                self.subscription_live.clear()

                logger.info("Connecting to WebSocket")
                async with websockets.connect(settings.websocket.url) as ws:
                    logger.info("WebSocket connected")
                    self.ws = ws

                    token = await auth_manager.get_token()
                    logger.info("Sending STOMP authentication frame")
                    await self._connect_stomp(settings.stomp.remote_host, token)

                    consumer_task = asyncio.create_task(self._consumer())

                    await self.connected.wait()
                    logger.info("STOMP connected")

                    logger.info("Subscribing to main topic")
                    await self._subscribe(settings.stomp.main_topic, "main_topic_sub")

                    try:
                        await consumer_task
                    except Exception as e:
                        logger.error(f"Consumer error: {e}")

            except Exception as e:
                logger.error(f"Connection error: {e}")

            self.connected.clear()
            await asyncio.sleep(3)

    async def _connect_stomp(self, remote_host, token):
        frame = (
            "CONNECT\n"
            "accept-version:1.2\n"
            f"host:{remote_host}\n"
            f"Authorization:Bearer {token}\n\n\x00"
        )
        await self.ws.send(frame)

    async def _consumer(self):
        async for message in self.ws:
            if message.startswith("CONNECTED"):
                self.connected.set()

            elif message.startswith("MESSAGE"):
                await self._enqueue_message(message)

            elif message.startswith("ERROR"):
                logger.error(f"STOMP ERROR: {message}")

            else:
                logger.warning(f"STOMP UNCATEGORIZED FRAME: {message}")

    async def _subscribe(self, destination, subscription_id):
        frame = (
            "SUBSCRIBE\n"
            f"id:{subscription_id}\n"
            f"destination:{destination}\n\n\x00"
        )

        await self.ws.send(frame)
        logger.debug(f"Subscribed to topic {destination}")

    async def subscription_queue_consumer(self):
        while True:
            await self.connected.wait()
            topic, message = await self.subscription_queue.get()

            object_id = message.get("id")
            subscription_id = f"{self.sub_topic}-{object_id}"
            destination = f"{self.main_topic}/{object_id}{self.sub_topic}"

            if not self.connected.is_set():
                self.subscription_queue.task_done()
                continue

            should_subscribe = False
            async with self.subscription_live_lock:
                if subscription_id not in self.subscription_live:
                    self.subscription_live.add(subscription_id)
                    should_subscribe = True

            if should_subscribe:
                await self._subscribe(destination, subscription_id)
            else:
                logger.debug(f"Sub topic {destination} already subscribed")

            self.subscription_queue.task_done()

    async def _enqueue_message(self, message: str):
        try:
            headers, body_raw = message.split("\n\n", 1)
            logger.debug(f"Received headers: {headers}")
            body = body_raw.strip("\x00")
            logger.debug(f"Received body: {body}")

            message_body = json.loads(body)

            topic_line = next(
                (h for h in headers.split("\n") if h.startswith("destination:")),
                None,
            )
            topic = topic_line.split("destination:", 1)[1] if topic_line else ""

            if topic == self.main_topic and not self.single_topic:
                subscription_id = f"{self.sub_topic}-{message_body.get('id')}"

                should_enqueue = False
                async with self.subscription_live_lock:
                    if subscription_id not in self.subscription_live:
                        should_enqueue = True

                if should_enqueue:
                    if self.subscription_queue.full():
                        logger.warning(f"Subscription Queue FULL dropping subscription for {subscription_id}")
                    else:
                        await self.subscription_queue.put((topic, message_body))
            else:
                if self.message_queue.full():
                    logger.warning(f"Message Queue FULL dropping oldest")
                    self.message_queue.get_nowait()
                    self.message_queue.task_done()

                await self.message_queue.put((topic, message_body))

            logger.debug(f"MSG Queue size: {self.message_queue.qsize()}")
            logger.debug(f"SUBSCRIPTION Queue size: {self.subscription_queue.qsize()}")

        except Exception as e:
            logger.error(f"Parse error (enqueue): {e}")

    async def message_queue_consumer(self):
        loop = asyncio.get_running_loop()

        while True:
            topic, message = await self.message_queue.get()

            try:
                await loop.run_in_executor(
                    self.executor,
                    self.on_message,
                    message,
                    topic

                )
            except Exception as e:
                logger.error(f"Worker error: {e}")

            finally:
                self.message_queue.task_done()

    # VBO to remove
    async def test_publisher_worker(self):
        while True:
            await self.connected.wait()
            await asyncio.sleep(2)

            try:
                payload = {
                    "id": "id_tracker_1",
                    "deviceId": "003F004A4652501420303231",
                    "name": "Forklift 1",
                    "siteId": "123e4567-e89b-12d3-a456-426614174000",
                    "siteName": "Warehouse A",
                    "status": "ONLINE",
                    "battery": 91
                }

                frame = (
                    "SEND\n"
                    f"destination:{self.main_topic}\n"
                    "content-type:application/json\n\n"
                    f"{json.dumps(payload)}\x00"
                )
                payload2 = {
                    "id": "id_tracker_2",
                    "deviceId": "003F004A4652501420303232",
                    "name": "Forklift 2",
                    "siteId": "123e4567-e89b-12d3-a456-426614174000",
                    "siteName": "Warehouse B",
                    "status": "ONLINE",
                    "battery": 92
                }

                frame2 = (
                    "SEND\n"
                    f"destination:{self.main_topic}\n"
                    "content-type:application/json\n\n"
                    f"{json.dumps(payload2)}\x00"
                )

                await self.ws.send(frame)
                logger.debug("📤 SENT tracker 1 payload")
                await self.ws.send(frame2)
                logger.debug("📤 SENT tracker 2 payload")

                await asyncio.sleep(2)

                p_payload = {
                    "trackerId": "id_tracker_1",
                    "trackerDeviceId": "WH-TRK-12345",
                    "siteId": "123e4567-e89b-12d3-a456-426614174000",
                    "latitude": 41.1111,
                    "longitude": 2.3521,
                    "altitude": 35.1,
                    "timestamp": "2025-10-14T10:15:30.123Z"
                }

                p_frame = (
                    "SEND\n"
                    f"destination:{self.main_topic}/id_tracker_1{self.sub_topic}\n"
                    "content-type:application/json\n\n"
                    f"{json.dumps(p_payload)}\x00"
                )

                p_payload2 = {
                    "trackerId": "id_tracker_2",
                    "trackerDeviceId": "WH-TRK-123456",
                    "siteId": "123e4567-e89b-12d3-a456-426614174000",
                    "latitude": 42.2222,
                    "longitude": 2.3522,
                    "altitude": 35.2,
                    "timestamp": "2025-10-14T10:15:30.123Z"
                }

                p_frame2 = (
                    "SEND\n"
                    f"destination:{self.main_topic}/id_tracker_2{self.sub_topic}\n"
                    "content-type:application/json\n\n"
                    f"{json.dumps(p_payload2)}\x00"
                )

                await self.ws.send(p_frame)
                logger.debug("📤 SENT tracker POSITION 1 payload")
                await self.ws.send(p_frame2)
                logger.debug("📤 SENT tracker POSITION 2 payload")

                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Publisher error: {e}")
                await asyncio.sleep(1)


def _drain_queue(queue):
    while True:
        try:
            queue.get_nowait()
            queue.task_done()
        except asyncio.QueueEmpty:
            break
