import json
import logging
import websockets

from typing import Awaitable, Callable, Optional


logger = logging.getLogger("kiwoom_ws")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class KiwoomWS:
    """
    - websockets.connect 로 연결
    - 로그인 패킷 전송 (trnm=LOGIN, token)
    - 서버 PING 수신 시 그대로 에코
    - 임의 메시지 송신 API 제공 (send)
    - 수신 콜백(on_message) 훅 제공
    """

    def __init__(self, url: str, access_token: str, on_message: Optional[Callable[[dict], Awaitable[None]]] = None):
        self.url = url
        self.token = access_token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected: bool = False
        self.keep_running: bool = True
        self.on_message = on_message

    # --------------------------- lifecycle ---------------------------
    async def connect(self) -> None:
        try:
            self.ws = await websockets.connect(self.url, ping_interval=None, ping_timeout=None)
            self.connected = True
            logger.info("서버와 연결했습니다. (connect)")
            # 로그인 패킷 전송
            await self.send({"trnm": "LOGIN", "token": self.token})
            logger.info("로그인 패킷 전송 완료")
        except Exception as e:
            self.connected = False
            logger.error(f"Connection error: {e}")
            raise

    async def disconnect(self) -> None:
        self.keep_running = False
        if self.connected and self.ws:
            await self.ws.close()
        self.connected = False
        logger.info("WebSocket 연결을 종료했습니다.")

    async def send(self, message: dict | str) -> None:
        if not self.connected or not self.ws:
            await self.connect()
        if not isinstance(message, str):
            message = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        await self.ws.send(message)
        logger.debug(f"SEND: {message}")

    async def receive_loop(self) -> None:
        assert self.ws is not None
        try:
            while self.keep_running:
                raw = await self.ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    logger.warning(f"Invalid JSON: {str(raw)[:200]}")
                    continue

                trnm = msg.get("trnm")
                if trnm == "LOGIN":
                    if msg.get("return_code") != 0:
                        logger.error(f"로그인 실패: {msg.get('return_msg')}")
                        await self.disconnect()
                        break
                    logger.info("로그인 성공")
                elif trnm == "PING":
                    # 서버가 보낸 PING 은 그대로 에코
                    await self.send(msg)
                else:
                    if self.on_message:
                        await self.on_message(msg)
                    else:
                        logger.info(f"RECV: {msg}")
        except websockets.ConnectionClosed:
            logger.warning("Connection closed by server")
            self.connected = False

    async def run(self) -> None:
        await self.connect()
        await self.receive_loop()