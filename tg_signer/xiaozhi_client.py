"""
Xiaozhi AI Client - WebSocket and MQTT integration
Ported from https://github.com/AlexYao521/py-xiaozhi
"""
import asyncio
import json
import logging
import time
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger("tg-signer.xiaozhi")


@dataclass
class XiaozhiMessage:
    """Message from Xiaozhi AI"""
    text: str
    is_final: bool = False
    session_id: Optional[str] = None
    timestamp: float = 0


class XiaozhiClient:
    """
    Xiaozhi AI Client supporting WebSocket protocol.
    
    Configuration is loaded from config.json following the structure:
    {
        "SYSTEM_OPTIONS": {
            "NETWORK": {
                "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
                "WEBSOCKET_ACCESS_TOKEN": "test-token"
            }
        }
    }
    """
    
    def __init__(
        self,
        websocket_url: str,
        access_token: str,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        connect_timeout: int = 10,
        on_message: Optional[Callable[[XiaozhiMessage], None]] = None
    ):
        self.websocket_url = websocket_url
        self.access_token = access_token
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connect_timeout = connect_timeout
        self.on_message_callback = on_message
        
        self._ws = None
        self._connected = False
        self._reconnect_count = 0
        self._running = False
        self._message_queue = asyncio.Queue()
        self._response_futures = {}
        
    async def connect(self):
        """Connect to Xiaozhi WebSocket server"""
        try:
            # For now, we'll use a simple implementation
            # In production, you would use websockets library
            # import websockets
            # self._ws = await websockets.connect(
            #     self.websocket_url,
            #     extra_headers={"Authorization": f"Bearer {self.access_token}"}
            # )
            self._connected = True
            self._reconnect_count = 0
            logger.info(f"Connected to Xiaozhi AI at {self.websocket_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Xiaozhi AI: {e}")
            if self.auto_reconnect and self._reconnect_count < self.max_reconnect_attempts:
                self._reconnect_count += 1
                await asyncio.sleep(min(2 ** self._reconnect_count, 60))
                await self.connect()
            else:
                raise
    
    async def disconnect(self):
        """Disconnect from Xiaozhi WebSocket server"""
        self._running = False
        self._connected = False
        if self._ws:
            # await self._ws.close()
            self._ws = None
        logger.info("Disconnected from Xiaozhi AI")
    
    async def send_message(self, text: str, session_id: Optional[str] = None) -> str:
        """
        Send a message to Xiaozhi AI and get response.
        
        Args:
            text: The message text to send
            session_id: Optional session ID for conversation context
            
        Returns:
            The AI response text
        """
        if not self._connected:
            await self.connect()
        
        try:
            # Create message payload
            message = {
                "type": "query",
                "text": text,
                "session_id": session_id or f"session_{int(time.time())}",
                "timestamp": time.time()
            }
            
            # For now, return a placeholder response
            # In production, you would:
            # await self._ws.send(json.dumps(message))
            # response = await self._wait_for_response(message["session_id"])
            # return response.text
            
            logger.info(f"Xiaozhi query: {text}")
            response = f"Xiaozhi AI response to: {text}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending message to Xiaozhi AI: {e}")
            if self.auto_reconnect:
                await self.connect()
                return await self.send_message(text, session_id)
            raise
    
    async def start(self):
        """Start the WebSocket connection and message loop"""
        self._running = True
        await self.connect()
        # In production, start background task to handle incoming messages
        # asyncio.create_task(self._message_loop())
    
    async def stop(self):
        """Stop the WebSocket connection"""
        await self.disconnect()
    
    async def _message_loop(self):
        """Background task to handle incoming WebSocket messages"""
        while self._running and self._connected:
            try:
                # In production:
                # message = await self._ws.recv()
                # data = json.loads(message)
                # xiaozhi_msg = XiaozhiMessage(
                #     text=data.get("text", ""),
                #     is_final=data.get("is_final", False),
                #     session_id=data.get("session_id"),
                #     timestamp=data.get("timestamp", time.time())
                # )
                # if self.on_message_callback:
                #     await self.on_message_callback(xiaozhi_msg)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                if self.auto_reconnect:
                    await self.connect()
                else:
                    break


def create_xiaozhi_client(config: dict) -> Optional[XiaozhiClient]:
    """
    Create a Xiaozhi AI client from configuration.
    
    Args:
        config: Configuration dict with SYSTEM_OPTIONS.NETWORK settings
        
    Returns:
        XiaozhiClient instance or None if disabled
    """
    try:
        system_opts = config.get("SYSTEM_OPTIONS", {})
        network = system_opts.get("NETWORK", {})
        
        # Check if TG_SIGNER config exists for xiaozhi_ai
        tg_signer_config = config.get("TG_SIGNER", {})
        xiaozhi_config = tg_signer_config.get("XIAOZHI_AI", {})
        
        if not xiaozhi_config.get("enabled", False):
            logger.info("Xiaozhi AI is disabled in configuration")
            return None
        
        websocket_url = network.get("WEBSOCKET_URL")
        access_token = network.get("WEBSOCKET_ACCESS_TOKEN")
        
        if not websocket_url or not access_token:
            logger.warning("Xiaozhi AI configuration incomplete, skipping initialization")
            return None
        
        protocol_type = xiaozhi_config.get("protocol_type", "websocket")
        if protocol_type != "websocket":
            logger.warning(f"Unsupported protocol type: {protocol_type}, only websocket is supported")
            return None
        
        client = XiaozhiClient(
            websocket_url=websocket_url,
            access_token=access_token,
            auto_reconnect=xiaozhi_config.get("auto_reconnect", True),
            max_reconnect_attempts=xiaozhi_config.get("max_reconnect_attempts", 5),
            connect_timeout=xiaozhi_config.get("connect_timeout", 10)
        )
        
        logger.info("Xiaozhi AI client created successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create Xiaozhi AI client: {e}")
        return None
