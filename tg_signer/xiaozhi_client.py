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
        },
        "TG_SIGNER": {
            "XIAOZHI_AI": {
                "enabled": true,
                "protocol_type": "websocket",
                "auto_reconnect": true,
                "max_reconnect_attempts": 5,
                "connect_timeout": 10
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
        self._receive_task = None
        
    async def connect(self):
        """Connect to Xiaozhi WebSocket server"""
        try:
            # Check if websockets library is available
            try:
                import websockets
            except ImportError:
                logger.warning("websockets library not installed. WebSocket connection disabled.")
                logger.warning("Install with: pip install websockets")
                # Use mock mode
                self._connected = True
                self._reconnect_count = 0
                logger.info(f"小智AI 连接模拟模式 (未安装 websockets 库)")
                return
            
            # Real WebSocket connection
            logger.info(f"Connecting to Xiaozhi AI at {self.websocket_url}")
            
            # Connect with headers
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    extra_headers={"Authorization": f"Bearer {self.access_token}"}
                ),
                timeout=self.connect_timeout
            )
            
            self._connected = True
            self._reconnect_count = 0
            logger.info(f"小智AI WebSocket 连接成功")
            
            # Start receive loop
            if self._running:
                self._receive_task = asyncio.create_task(self._message_loop())
            
        except asyncio.TimeoutError:
            logger.error(f"连接小智AI超时 ({self.connect_timeout}秒)")
            await self._handle_reconnect()
        except Exception as e:
            logger.error(f"连接小智AI失败: {e}")
            await self._handle_reconnect()
    
    async def _handle_reconnect(self):
        """Handle reconnection logic"""
        if self.auto_reconnect and self._reconnect_count < self.max_reconnect_attempts:
            self._reconnect_count += 1
            backoff = min(2 ** self._reconnect_count, 60)
            logger.info(f"小智AI 将在 {backoff} 秒后重试连接 (尝试 {self._reconnect_count}/{self.max_reconnect_attempts})")
            await asyncio.sleep(backoff)
            await self.connect()
        else:
            logger.error(f"小智AI 重连失败，已达到最大重试次数")
            # Fallback to mock mode
            self._connected = True
    
    async def disconnect(self):
        """Disconnect from Xiaozhi WebSocket server"""
        self._running = False
        self._connected = False
        
        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket
        if self._ws:
            try:
                await self._ws.close()
            except:
                pass
            self._ws = None
        
        logger.info("小智AI 已断开连接")
    
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
        
        # If not really connected (mock mode), return placeholder
        if not self._ws:
            logger.info(f"小智AI 查询 (模拟模式): {text[:50]}")
            return f"小智AI回复 (模拟): 收到您的消息「{text[:30]}」"
        
        try:
            # Create message payload
            session_id = session_id or f"session_{int(time.time())}"
            message = {
                "type": "query",
                "text": text,
                "session_id": session_id,
                "timestamp": time.time()
            }
            
            # Create future for response
            future = asyncio.Future()
            self._response_futures[session_id] = future
            
            # Send message
            await self._ws.send(json.dumps(message))
            logger.debug(f"小智AI 发送消息: {text[:50]}")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(future, timeout=30.0)
                return response
            except asyncio.TimeoutError:
                logger.warning(f"小智AI 响应超时")
                # Clean up future
                self._response_futures.pop(session_id, None)
                return "小智AI暂时无法响应，请稍后再试"
            
        except Exception as e:
            logger.error(f"小智AI 发送消息失败: {e}")
            if self.auto_reconnect:
                await self.connect()
                return await self.send_message(text, session_id)
            raise
    
    async def start(self):
        """Start the WebSocket connection and message loop"""
        self._running = True
        await self.connect()
    
    async def stop(self):
        """Stop the WebSocket connection"""
        await self.disconnect()
    
    async def _message_loop(self):
        """Background task to handle incoming WebSocket messages"""
        while self._running and self._connected and self._ws:
            try:
                # Receive message
                message = await self._ws.recv()
                data = json.loads(message)
                
                # Parse message
                xiaozhi_msg = XiaozhiMessage(
                    text=data.get("text", ""),
                    is_final=data.get("is_final", True),
                    session_id=data.get("session_id"),
                    timestamp=data.get("timestamp", time.time())
                )
                
                # Handle response
                session_id = xiaozhi_msg.session_id
                if session_id and session_id in self._response_futures:
                    future = self._response_futures.pop(session_id)
                    if not future.done():
                        future.set_result(xiaozhi_msg.text)
                
                # Call callback if provided
                if self.on_message_callback:
                    if asyncio.iscoroutinefunction(self.on_message_callback):
                        await self.on_message_callback(xiaozhi_msg)
                    else:
                        self.on_message_callback(xiaozhi_msg)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"小智AI 消息循环错误: {e}")
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
            logger.info("小智AI 在配置中已禁用")
            return None
        
        websocket_url = network.get("WEBSOCKET_URL")
        access_token = network.get("WEBSOCKET_ACCESS_TOKEN")
        
        if not websocket_url or not access_token:
            logger.warning("小智AI 配置不完整，跳过初始化")
            return None
        
        protocol_type = xiaozhi_config.get("protocol_type", "websocket")
        if protocol_type != "websocket":
            logger.warning(f"不支持的协议类型: {protocol_type}，仅支持 websocket")
            return None
        
        client = XiaozhiClient(
            websocket_url=websocket_url,
            access_token=access_token,
            auto_reconnect=xiaozhi_config.get("auto_reconnect", True),
            max_reconnect_attempts=xiaozhi_config.get("max_reconnect_attempts", 5),
            connect_timeout=xiaozhi_config.get("connect_timeout", 10)
        )
        
        logger.info("小智AI 客户端创建成功")
        return client
        
    except Exception as e:
        logger.error(f"创建小智AI客户端失败: {e}")
        return None
