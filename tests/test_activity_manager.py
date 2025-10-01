"""
Tests for activity_manager module
"""
import pytest
from unittest.mock import Mock, AsyncMock
from tg_signer.activity_manager import ActivityManager, ActivityPattern


class TestActivityManager:
    """测试活动管理模块"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.manager = ActivityManager(
            chat_id=-1001234567890,
            account="test_account",
            xiaozhi_client=None
        )
    
    def test_load_activity_patterns(self):
        """测试活动模式加载"""
        patterns = self.manager._load_activity_patterns()
        
        # 应该有多个活动模式
        assert len(patterns) >= 5
        
        # 检查各种活动是否存在
        pattern_names = [p.name for p in patterns]
        assert "魂魄献祭" in pattern_names
        assert "天机考验_选择题" in pattern_names
        assert "天机考验_指令题" in pattern_names
        assert "虚天殿问答" in pattern_names
        assert "洞府访客_查看" in pattern_names
        assert "洞府访客_接待" in pattern_names
    
    def test_match_hunpo_xiansi(self):
        """测试匹配魂魄献祭活动"""
        text = """@iwweonoji！你感到一股无法抗拒的意志锁定了你的神魂！
一个沙哑的声音在你脑海中响起："小辈，让老夫看看你的成色..."
你必须在 3 分钟 内做出抉择：
回复本消息 .献上魂魄 (高风险，高回报)
回复本消息 .收敛气息 (低风险，低回报)"""
        
        message = Mock()
        result = self.manager.match_activity(text, message, enable_ai=False)
        
        # 应该匹配到魂魄献祭
        assert result is not None
        assert result[0] == ".收敛气息"
        assert result[1] == "command"
    
    def test_match_xutian_dian_wenda(self):
        """测试匹配虚天殿问答 - 使用in操作符"""
        text = """神念直入脑海，一个苍老的声音向 @thezhang98 提问：
"在虚天殿中，韩立最终获得的"补天丹"有何奇效？"
A. 令人死而复生 B. 白日飞升灵界 C. 增加结婴几率 D. 大幅增加寿元
小辈，你有 300秒 的时间，回复本消息并使用 .作答 <选项> 给出你的答案。"""
        
        message = Mock()
        result = self.manager.match_activity(text, message, enable_ai=False)
        
        # 应该匹配到虚天殿问答，但由于enable_ai=False且需要AI，所以返回None
        assert result is None
    
    def test_match_dongfu_fangke_jiedai(self):
        """测试匹配洞府访客接待 - 使用in操作符"""
        text = """【洞府传音】
有道友来访，请问是否接待？
你必须在5分钟内 ，使用 .接待访客 或 .驱逐访客 做出决定。"""
        
        message = Mock()
        result = self.manager.match_activity(text, message, enable_ai=False)
        
        # 应该匹配到洞府访客
        assert result is not None
        assert result[0] == ".接待访客"
        assert result[1] == "command"
    
    def test_match_dongfu_fangke_chakan(self):
        """测试匹配洞府访客查看 - 使用in操作符"""
        text = """【洞府传音】
你的洞府有访客到来
使用 .查看访客 查看详情"""
        
        message = Mock()
        result = self.manager.match_activity(text, message, enable_ai=False)
        
        # 应该匹配到查看访客
        assert result is not None
        assert result[0] == ".查看访客"
        assert result[1] == "command"
    
    def test_tianji_kaoyan_zhiling_ti(self):
        """测试天机考验指令题 - 提取指令"""
        text = """【天机考验】 @5688335060 道友，天机阁长老发现你近期气息异常，特降下考验以辨明正身！
请在 2分钟 内，根据以下问题，直接回复本消息 给出你的答案：
天机有感，你的道心似乎有所蒙尘。请在60秒内，使用.我的宗门指令自省，以证清白。
回答错误或超时，将被视为心怀叵测之徒，后果自负！"""
        
        message = Mock()
        # 这个需要AI处理，但我们可以测试指令提取逻辑
        # 由于xiaozhi_client为None，应该返回None
        result = self.manager.match_activity(text, message, enable_ai=True)
        assert result is None  # 因为没有xiaozhi_client
    
    def test_no_match(self):
        """测试不匹配任何活动"""
        text = "这是一条普通的消息，不包含任何活动关键词"
        message = Mock()
        
        result = self.manager.match_activity(text, message, enable_ai=False)
        assert result is None
    
    def test_enable_ai_parameter(self):
        """测试enable_ai参数控制"""
        # 天机考验需要AI
        text = """【天机考验】
以下四件物品中，哪一件是炼制【金蚨子母刃】的核心材料？
A. 百年铁木 B. 凝血草 C. 金精矿 D. 一阶妖丹
直接回复本消息 给出你的答案"""
        
        message = Mock()
        
        # enable_ai=False时应该返回None
        result = self.manager.match_activity(text, message, enable_ai=False)
        assert result is None
        
        # enable_ai=True但没有xiaozhi_client也返回None
        result = self.manager.match_activity(text, message, enable_ai=True)
        assert result is None
    
    def test_hunpo_removed_prefix_matching(self):
        """测试魂魄献祭不匹配开头描述"""
        # 只有开头描述，没有回复指令
        text = "你感到一股无法抗拒的意志锁定了你的神魂！"
        message = Mock()
        
        result = self.manager.match_activity(text, message, enable_ai=False)
        # 不应该匹配（因为没有"回复本消息"部分）
        assert result is None


class TestActivityPatternMatching:
    """测试活动模式匹配逻辑"""
    
    def test_in_operator_for_zuoda(self):
        """测试使用in操作符匹配.作答"""
        manager = ActivityManager(
            chat_id=-1001234567890,
            account="test",
            xiaozhi_client=None
        )
        
        # 包含.作答的文本
        text1 = "回复本消息并使用 .作答 <选项> 给出答案"
        text2 = "请使用.作答 A来回答"
        text3 = "命令：.作答 B"
        
        message = Mock()
        
        for text in [text1, text2, text3]:
            # 应该能识别（但因为没有AI客户端会返回None）
            result = manager.match_activity(text, message, enable_ai=False)
            # 虽然识别了，但因为需要AI且enable_ai=False，所以返回None
            assert result is None
    
    def test_in_operator_for_dongfu(self):
        """测试使用in操作符匹配洞府访客"""
        manager = ActivityManager(
            chat_id=-1001234567890,
            account="test",
            xiaozhi_client=None
        )
        
        message = Mock()
        
        # 包含.接待访客
        text1 = "使用 .接待访客 或 .驱逐访客"
        result = manager.match_activity(text1, message, enable_ai=False)
        assert result is not None
        assert ".接待访客" in result[0]
        
        # 包含.查看访客
        text2 = "使用 .查看访客 查看详情"
        result = manager.match_activity(text2, message, enable_ai=False)
        assert result is not None
        assert ".查看访客" in result[0]


@pytest.mark.asyncio
class TestActivityManagerAsync:
    """测试活动管理器的异步方法"""
    
    async def test_query_xiaozhi_async_command_extraction(self):
        """测试异步查询小智 - 指令提取"""
        manager = ActivityManager(
            chat_id=-1001234567890,
            account="test",
            xiaozhi_client=None  # 没有客户端也能测试指令提取
        )
        
        text = "使用.我的宗门指令自省"
        pattern = ActivityPattern(
            name="天机考验_指令题",
            patterns=[],
            response_type="ai_query",
            response_value="command"
        )
        
        result = await manager.query_xiaozhi_async(text, pattern)
        # 应该提取到.我的宗门指令
        assert result == ".我的宗门"
    
    async def test_query_xiaozhi_async_no_client(self):
        """测试没有AI客户端时的异步查询"""
        manager = ActivityManager(
            chat_id=-1001234567890,
            account="test",
            xiaozhi_client=None
        )
        
        text = "这是一个问题"
        pattern = ActivityPattern(
            name="天机考验_选择题",
            patterns=[],
            response_type="ai_query",
            response_value=None
        )
        
        result = await manager.query_xiaozhi_async(text, pattern)
        # 没有客户端应该返回None
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
