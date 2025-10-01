"""
Xiaozhi AI Client - WebSocket integration
Ported from https://github.com/AlexYao521/py-xiaozhi
"""
import asyncio
import json
import logging
import time
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger("tg-signer.xiaozhi")

# Try to import websockets, fallback gracefully if not available
try:
    import websockets
    from websockets.exceptions import WebSocketException
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    logger.warning("websockets library not available, WebSocket features will be disabled")
    WEBSOCKETS_AVAILABLE = False
    WebSocketException = Exception


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
        self._message_loop_task = None
        
    async def connect(self):
        """Connect to Xiaozhi WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library is not installed. Install with: pip install websockets")
            return
        
        try:
            # Create WebSocket connection with auth header
            extra_headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            logger.info(f"Connecting to Xiaozhi AI at {self.websocket_url}")
            
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    extra_headers=extra_headers,
                    ping_interval=20,
                    ping_timeout=10
                ),
                timeout=self.connect_timeout
            )
            
            self._connected = True
            self._reconnect_count = 0
            logger.info(f"Connected to Xiaozhi AI at {self.websocket_url}")
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout after {self.connect_timeout} seconds")
            await self._handle_connection_failure()
        except Exception as e:
            logger.error(f"Failed to connect to Xiaozhi AI: {e}")
            await self._handle_connection_failure()
    
    async def _handle_connection_failure(self):
        """Handle connection failure with exponential backoff"""
        if self.auto_reconnect and self._reconnect_count < self.max_reconnect_attempts:
            self._reconnect_count += 1
            backoff_time = min(2 ** self._reconnect_count, 60)
            logger.info(f"Reconnecting in {backoff_time} seconds (attempt {self._reconnect_count}/{self.max_reconnect_attempts})")
            await asyncio.sleep(backoff_time)
            await self.connect()
        else:
            logger.error("Max reconnection attempts reached or auto-reconnect disabled")
            raise ConnectionError("Failed to connect to Xiaozhi AI")
    
    async def disconnect(self):
        """Disconnect from Xiaozhi WebSocket server"""
        self._running = False
        self._connected = False
        
        if self._message_loop_task:
            self._message_loop_task.cancel()
            try:
                await self._message_loop_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
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
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library is not installed")
            return "Error: WebSocket support not available"
        
        if not self._connected:
            await self.connect()
        
        if not self._connected:
            return "Error: Not connected to Xiaozhi AI"
        
        try:
            # Create message payload
            message = {
                "type": "query",
                "text": text,
                "session_id": session_id or f"session_{int(time.time())}",
                "timestamp": time.time()
            }
            
            logger.debug(f"Sending message: {text}")
            
            # Send message
            await self._ws.send(json.dumps(message))
            
            # Wait for response (with timeout)
            response = await asyncio.wait_for(
                self._wait_for_response(message["session_id"]),
                timeout=30
            )
            
            logger.debug(f"Received response: {response}")
            return response
            
        except asyncio.TimeoutError:
            logger.error("Response timeout after 30 seconds")
            return "Error: Response timeout"
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            if self.auto_reconnect:
                await self.connect()
                # Retry once
                return await self.send_message(text, session_id)
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error sending message to Xiaozhi AI: {e}")
            return f"Error: {e}"
    
    async def _wait_for_response(self, session_id: str) -> str:
        """Wait for response from Xiaozhi AI"""
        future = asyncio.Future()
        self._response_futures[session_id] = future
        
        try:
            response = await future
            return response
        finally:
            self._response_futures.pop(session_id, None)
    
    async def start(self):
        """Start the WebSocket connection and message loop"""
        self._running = True
        await self.connect()
        
        if self._connected:
            # Start background task to handle incoming messages
            self._message_loop_task = asyncio.create_task(self._message_loop())
    
    async def stop(self):
        """Stop the WebSocket connection"""
        await self.disconnect()
    
    async def _message_loop(self):
        """Background task to handle incoming WebSocket messages"""
        while self._running and self._connected:
            try:
                if not self._ws:
                    break
                
                # Receive message with timeout
                message = await asyncio.wait_for(self._ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                # Create XiaozhiMessage
                xiaozhi_msg = XiaozhiMessage(
                    text=data.get("text", ""),
                    is_final=data.get("is_final", True),
                    session_id=data.get("session_id"),
                    timestamp=data.get("timestamp", time.time())
                )
                
                logger.debug(f"Received message: {xiaozhi_msg.text}")
                
                # Handle streaming response
                session_id = xiaozhi_msg.session_id
                if session_id in self._response_futures:
                    if xiaozhi_msg.is_final:
                        # Complete the future with final response
                        future = self._response_futures.get(session_id)
                        if future and not future.done():
                            future.set_result(xiaozhi_msg.text)
                    # For streaming, we could accumulate partial responses here
                
                # Call callback if provided
                if self.on_message_callback:
                    try:
                        if asyncio.iscoroutinefunction(self.on_message_callback):
                            await self.on_message_callback(xiaozhi_msg)
                        else:
                            self.on_message_callback(xiaozhi_msg)
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")
                
            except asyncio.TimeoutError:
                # No message received, continue
                continue
            except WebSocketException as e:
                logger.error(f"WebSocket error in message loop: {e}")
                if self.auto_reconnect:
                    await self.connect()
                else:
                    break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                await asyncio.sleep(1)


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
