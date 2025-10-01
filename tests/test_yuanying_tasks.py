"""
Tests for yuanying_tasks module
"""
import pytest
import time
from tg_signer.yuanying_tasks import YuanYingTasks, YuanYingState


class TestYuanYingTasks:
    """测试元婴任务模块"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.yuanying = YuanYingTasks(
            chat_id=-1001234567890,
            account="test_account",
            enabled=True
        )
    
    def test_parse_guiqiao_status(self):
        """测试解析元神归窍状态"""
        text = """【元神归窍】
你的元婴满载而归！
获得灵石: 1000
获得经验: 5000"""
        
        result = self.yuanying.parse_status_response(text)
        
        assert result is not None
        assert result["status"] == "归窍"
        assert ".元婴出窍" in result["next_actions"]
        assert result["cooldown_seconds"] == 30
    
    def test_parse_chuxiao_status_with_countdown(self):
        """测试解析元神出窍状态（带倒计时）"""
        text = """你的本命元婴
状态: 元神出窍
归来倒计时: 3小时20分钟"""
        
        result = self.yuanying.parse_status_response(text)
        
        assert result is not None
        assert result["status"] == "出窍"
        assert result["return_countdown_seconds"] == 12000  # 3*3600 + 20*60
        # 应该在归来前2分钟安排查询
        assert result["cooldown_seconds"] == 12000 - 120
    
    def test_parse_chuxiao_status_no_countdown(self):
        """测试解析元神出窍状态（无倒计时）"""
        text = """你的本命元婴
状态: 元神出窍
正在外游历中..."""
        
        result = self.yuanying.parse_status_response(text)
        
        assert result is not None
        assert result["status"] == "出窍"
        assert result["cooldown_seconds"] == 30 * 60  # 默认30分钟
    
    def test_parse_wenyang_status_can_chuxiao(self):
        """测试解析窍中温养状态（可以出窍）"""
        text = """你的本命元婴
状态: 窍中温养
已完成温养，可以出窍"""
        
        result = self.yuanying.parse_status_response(text)
        
        assert result is not None
        assert result["status"] == "温养"
        assert ".元婴出窍" in result["next_actions"]
        assert result["cooldown_seconds"] == 30
    
    def test_parse_wenyang_status_cooling(self):
        """测试解析窍中温养状态（冷却中）"""
        text = """你的本命元婴
状态: 窍中温养
请在 2小时30分钟 后再次出窍"""
        
        result = self.yuanying.parse_status_response(text)
        
        assert result is not None
        assert result["status"] == "温养"
        assert len(result["next_actions"]) == 0
        assert result["cooldown_seconds"] == 9000  # 2*3600 + 30*60
    
    def test_parse_chuxiao_success(self):
        """测试解析元婴出窍成功响应"""
        text = """元婴离体成功！
你的元婴开始云游 8 小时
预计收获丰厚"""
        
        result = self.yuanying.parse_chuxiao_response(text)
        
        assert result is not None
        assert result["success"] is True
        assert result["cooldown_seconds"] == 8 * 3600
        assert self.yuanying.state.status == "出窍"
    
    def test_parse_chuxiao_cooling(self):
        """测试解析元婴出窍冷却响应"""
        text = """你的元婴尚未归来
请在 5小时30分钟 后再试"""
        
        result = self.yuanying.parse_chuxiao_response(text)
        
        assert result is not None
        assert result["success"] is False
        assert result["cooldown_seconds"] == 19800  # 5*3600 + 30*60
    
    def test_should_check_status(self):
        """测试是否应该查询状态"""
        # 初始状态应该需要查询
        assert self.yuanying.should_check_status() is True
        
        # 设置未来的查询时间
        self.yuanying.state.next_check_ts = time.time() + 3600
        assert self.yuanying.should_check_status() is False
        
        # 设置过去的查询时间
        self.yuanying.state.next_check_ts = time.time() - 10
        assert self.yuanying.should_check_status() is True
    
    def test_should_chuxiao(self):
        """测试是否应该出窍"""
        # 初始状态不应该出窍（状态为unknown）
        assert self.yuanying.should_chuxiao() is False
        
        # 设置为归窍状态，且过了冷却时间
        self.yuanying.state.status = "归窍"
        self.yuanying.state.next_chuxiao_ts = time.time() - 10
        assert self.yuanying.should_chuxiao() is True
        
        # 设置为温养状态，且过了冷却时间
        self.yuanying.state.status = "温养"
        assert self.yuanying.should_chuxiao() is True
        
        # 设置为出窍状态，不应该出窍
        self.yuanying.state.status = "出窍"
        assert self.yuanying.should_chuxiao() is False
    
    def test_mark_guiqiao(self):
        """测试标记元婴归窍"""
        self.yuanying.mark_guiqiao()
        
        assert self.yuanying.state.status == "归窍"
        # 应该在30秒后可以出窍
        assert self.yuanying.state.next_chuxiao_ts > time.time()
        assert self.yuanying.state.next_chuxiao_ts < time.time() + 60
    
    def test_get_ready_tasks(self):
        """测试获取就绪任务"""
        # 初始状态应该有查询任务
        tasks = self.yuanying.get_ready_tasks()
        assert len(tasks) > 0
        assert any(".元婴状态" in task[0] for task in tasks)
        
        # 设置为归窍状态，应该有出窍任务
        self.yuanying.state.status = "归窍"
        self.yuanying.state.next_chuxiao_ts = time.time() - 10
        self.yuanying.state.next_check_ts = time.time() + 3600
        
        tasks = self.yuanying.get_ready_tasks()
        assert any(".元婴出窍" in task[0] for task in tasks)
    
    def test_state_persistence(self):
        """测试状态持久化"""
        # 设置一些状态
        self.yuanying.state.status = "出窍"
        self.yuanying.state.chuxiao_ts = time.time()
        self.yuanying.state.return_countdown_seconds = 28800
        
        # 保存状态
        state_data = self.yuanying.save_state()
        
        # 创建新实例并加载状态
        new_yuanying = YuanYingTasks(
            chat_id=-1001234567890,
            account="test_account",
            enabled=True
        )
        new_yuanying.load_state(state_data)
        
        # 验证状态是否正确加载
        assert new_yuanying.state.status == "出窍"
        assert new_yuanying.state.return_countdown_seconds == 28800


class TestYuanYingStateTransitions:
    """测试元婴状态转换"""
    
    def setup_method(self):
        self.yuanying = YuanYingTasks(
            chat_id=-1001234567890,
            account="test_account",
            enabled=True
        )
    
    def test_transition_guiqiao_to_chuxiao(self):
        """测试从归窍到出窍的转换"""
        # 解析归窍状态
        guiqiao_text = "【元神归窍】你的元婴满载而归！"
        result = self.yuanying.parse_status_response(guiqiao_text)
        assert self.yuanying.state.status == "归窍"
        
        # 应该有出窍动作
        assert ".元婴出窍" in result["next_actions"]
        
        # 解析出窍响应
        chuxiao_text = "元婴离体成功！云游 8 小时"
        result = self.yuanying.parse_chuxiao_response(chuxiao_text)
        assert result["success"] is True
        assert self.yuanying.state.status == "出窍"
    
    def test_transition_chuxiao_to_guiqiao(self):
        """测试从出窍到归窍的转换"""
        # 设置出窍状态
        self.yuanying.state.status = "出窍"
        self.yuanying.state.chuxiao_ts = time.time() - 8 * 3600
        
        # 标记归窍
        self.yuanying.mark_guiqiao()
        assert self.yuanying.state.status == "归窍"
        
        # 应该在30秒后可以出窍（mark_guiqiao设置了30秒延迟）
        # 检查next_chuxiao_ts是否在合理范围内
        assert self.yuanying.state.next_chuxiao_ts > time.time()
        assert self.yuanying.state.next_chuxiao_ts < time.time() + 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
