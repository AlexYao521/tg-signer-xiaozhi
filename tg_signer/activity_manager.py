"""
活动管理模块 (Activity Manager Module)
处理频道活动识别和响应
"""
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("tg-signer.activity")


@dataclass
class ActivityPattern:
    """活动模式定义"""
    name: str
    patterns: List[str]  # 正则表达式列表
    response_type: str  # 响应类型：reply_text, reply_command, ai_query
    response_value: Optional[str] = None
    priority: int = 2


class ActivityManager:
    """
    活动管理器
    
    根据 活动回复词.md 定义的规则识别和响应活动
    """
    
    def __init__(self, chat_id: int, account: str, xiaozhi_client=None):
        self.chat_id = chat_id
        self.account = account
        self.xiaozhi_client = xiaozhi_client
        
        # 定义活动模式（基于活动回复词.md）
        self.activity_patterns = self._load_activity_patterns()
    
    def _load_activity_patterns(self) -> List[ActivityPattern]:
        """加载活动模式定义"""
        patterns = []
        
        # 第一种：魂魄献祭活动
        patterns.append(ActivityPattern(
            name="魂魄献祭",
            patterns=[
                r"你感到一股无法抗拒的意志锁定了你的神魂",
                r"回复本消息\s+\.献上魂魄",
                r"回复本消息\s+\.收敛气息"
            ],
            response_type="reply_command",
            response_value=".收敛气息",
            priority=0  # 高优先级
        ))
        
        # 第二种：天机考验（选择题）
        patterns.append(ActivityPattern(
            name="天机考验_选择题",
            patterns=[
                r"【天机考验】.*请在.*根据以下问题.*直接回复本消息",
                r"以下.*件物品中.*哪一件.*核心材料",
                r"A\..*B\..*C\..*D\."
            ],
            response_type="ai_query",
            response_value=None,  # 需要AI回答
            priority=0
        ))
        
        # 第三种：天机考验（指令题）
        patterns.append(ActivityPattern(
            name="天机考验_指令题",
            patterns=[
                r"【天机考验】.*请在.*使用\.我的宗门指令自省",
                r"天机有感.*道心.*蒙尘"
            ],
            response_type="reply_command",
            response_value=".我的宗门",
            priority=0
        ))
        
        # 第四种：虚天殿问答
        patterns.append(ActivityPattern(
            name="虚天殿问答",
            patterns=[
                r"神念直入脑海.*向.*提问",
                r"回复本消息并使用\s+\.作答\s+<选项>",
                r"A\..*B\..*C\..*D\."
            ],
            response_type="ai_query",
            response_value="作答",  # 特殊标记
            priority=0
        ))
        
        # 第五种：洞府访客
        patterns.append(ActivityPattern(
            name="洞府访客_查看",
            patterns=[
                r"【洞府传音】",
                r"\.查看访客"
            ],
            response_type="reply_command",
            response_value=".查看访客",
            priority=0
        ))
        
        patterns.append(ActivityPattern(
            name="洞府访客_接待",
            patterns=[
                r"使用\s+\.接待访客\s+或\s+\.驱逐访客"
            ],
            response_type="reply_command",
            response_value=".接待访客",
            priority=0
        ))
        
        return patterns
    
    def match_activity(self, text: str, message) -> Optional[tuple[str, str, int]]:
        """
        匹配活动模式
        
        Args:
            text: 消息文本
            message: Telegram消息对象
            
        Returns:
            (response_command, response_type, priority) 如果匹配成功
        """
        if not text:
            return None
        
        # 检查消息是否@了机器人
        # 注意：message.entities 可能包含mention信息
        
        for pattern in self.activity_patterns:
            # 检查所有模式是否匹配
            match_count = 0
            for regex in pattern.patterns:
                if re.search(regex, text, re.IGNORECASE):
                    match_count += 1
            
            # 至少匹配一个模式即可
            if match_count > 0:
                logger.info(f"[活动] 识别到活动: {pattern.name}")
                
                if pattern.response_type == "reply_command":
                    return (pattern.response_value, "command", pattern.priority)
                
                elif pattern.response_type == "ai_query":
                    # 需要调用小智AI获取答案
                    response = self._query_xiaozhi(text, pattern)
                    if response:
                        return (response, "text", pattern.priority)
                    else:
                        logger.warning(f"[活动] 小智AI查询失败: {pattern.name}")
                        return None
        
        return None
    
    def _query_xiaozhi(self, text: str, pattern: ActivityPattern) -> Optional[str]:
        """
        查询小智AI获取答案
        
        Args:
            text: 原始问题文本
            pattern: 活动模式
            
        Returns:
            答案文本
        """
        if not self.xiaozhi_client:
            logger.warning("[活动] 未配置小智AI客户端")
            return None
        
        # 构造查询文本（添加前缀）
        query = f"获取问题答案：{text}"
        
        try:
            # 同步调用（需要改为异步版本）
            answer = self._sync_query_xiaozhi(query)
            
            # 对于虚天殿问答，需要格式化为 .作答 X
            if pattern.name == "虚天殿问答" and pattern.response_value == "作答":
                # 假设AI返回的是选项字母（A、B、C、D）
                answer = f".作答 {answer.strip()}"
            
            logger.info(f"[活动] 小智AI回答: {answer}")
            return answer
            
        except Exception as e:
            logger.error(f"[活动] 查询小智AI失败: {e}", exc_info=True)
            return None
    
    def _sync_query_xiaozhi(self, query: str) -> str:
        """
        同步查询小智（占位实现）
        实际使用时需要根据xiaozhi_client的实际接口调整
        """
        # 这里需要根据实际的xiaozhi_client接口实现
        # 暂时返回占位符
        return "A"
    
    def should_respond_to_message(self, message) -> bool:
        """
        判断是否应该响应此消息
        
        检查条件：
        1. 必须是频道机器人消息
        2. 如果是回复消息，回复ID必须匹配
        3. 必须@了机器人
        
        Args:
            message: Telegram消息对象
            
        Returns:
            是否应该响应
        """
        # 检查是否是机器人消息
        if not message.from_user:
            return False
        
        # 检查是否在配置的频道中
        if message.chat.id != self.chat_id:
            return False
        
        # 检查是否@了机器人（通过entities检测）
        if message.entities:
            for entity in message.entities:
                if entity.type.name == "MENTION":
                    # 检查mention的用户是否是机器人自己
                    # 这里需要传入bot的username进行比较
                    return True
        
        # 检查文本中是否包含@机器人
        if message.text and "@" in message.text:
            # 简化判断：文本中包含@
            return True
        
        # 如果是活动消息，也应该响应
        if message.text and "【" in message.text:
            return True
        
        return False
    
    def filter_message_by_thread(self, message, excluded_thread_ids: List[int] = None) -> bool:
        """
        根据message_thread_id过滤消息
        
        Args:
            message: Telegram消息对象
            excluded_thread_ids: 需要排除的话题ID列表
            
        Returns:
            是否应该处理此消息（True=处理，False=忽略）
        """
        if not excluded_thread_ids:
            return True
        
        # 检查消息是否在排除的话题中
        if hasattr(message, 'message_thread_id') and message.message_thread_id:
            if message.message_thread_id in excluded_thread_ids:
                logger.debug(f"[活动] 消息在排除的话题中: {message.message_thread_id}")
                return False
        
        return True
