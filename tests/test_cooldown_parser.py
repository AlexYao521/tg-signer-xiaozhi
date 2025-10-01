"""
Tests for cooldown parser module
"""
import pytest
from tg_signer.cooldown_parser import (
    _extract_cooldown_seconds,
    extract_cooldown_with_fallback,
    parse_time_remaining,
    format_cooldown,
)


class TestExtractCooldownSeconds:
    """Test _extract_cooldown_seconds function"""
    
    @pytest.mark.parametrize("text,expected", [
        # 标准格式测试
        ("请在 12小时30分钟 后再来", 45000),
        ("需要 3分钟20秒 方可", 200),
        ("冷却中，剩余 45秒", 45),
        ("请在 2小时 后再试", 7200),
        ("需要 30分钟 冷却", 1800),
        
        # 组合格式
        ("12小时30分钟45秒", 45045),
        ("1小时1分钟1秒", 3661),
        
        # 单一单位
        ("24小时", 86400),
        ("60分钟", 3600),
        ("120秒", 120),
        
        # 全角字符
        ("１２小时３０分钟", 45000),
        
        # 带空格
        ("请在   12  小时  30  分钟   后再来", 45000),
        
        # 中文变体
        ("12时30分", 45000),
        ("3分20秒", 200),
    ])
    def test_valid_formats(self, text, expected):
        """测试有效的冷却时间格式"""
        result = _extract_cooldown_seconds(text)
        assert result == expected
    
    @pytest.mark.parametrize("text", [
        # 无效格式
        "",
        "无法解析",
        "冷却中",
        "请稍后再试",
        "abc小时",
    ])
    def test_invalid_formats(self, text):
        """测试无效格式返回None"""
        result = _extract_cooldown_seconds(text)
        assert result is None
    
    def test_threshold_check(self):
        """测试阈值检查（小于10分钟且指令默认大于1小时）"""
        # 解析出30秒，但指令默认12小时，应该返回None
        text = "请在 30秒 后再试"
        result = _extract_cooldown_seconds(text, "问道")
        assert result is None
        
        # 解析出30秒，指令默认16分钟，应该正常返回
        text = "请在 30秒 后再试"
        result = _extract_cooldown_seconds(text, "闭关修炼")
        assert result == 30
    
    def test_mixed_text(self):
        """测试混合文本中提取"""
        text = "你引动了水系之力，需要打坐调息 12小时30分钟 方可再次引道"
        result = _extract_cooldown_seconds(text)
        assert result == 45000


class TestExtractCooldownWithFallback:
    """Test extract_cooldown_with_fallback function"""
    
    def test_successful_parse(self):
        """测试成功解析"""
        text = "请在 12小时 后再来"
        result = extract_cooldown_with_fallback(text, "问道")
        assert result == 43200
    
    def test_fallback_to_default(self):
        """测试回退到默认值"""
        text = "冷却中"
        result = extract_cooldown_with_fallback(text, "问道")
        # 问道默认冷却12小时
        assert result == 43200
    
    def test_fallback_unknown_command(self):
        """测试未知指令使用通用默认值"""
        text = "冷却中"
        result = extract_cooldown_with_fallback(text, "未知指令")
        # 默认30分钟
        assert result == 1800


class TestParseTimeRemaining:
    """Test parse_time_remaining function"""
    
    @pytest.mark.parametrize("text,expected", [
        ("剩余: 17分钟12秒", 1032),
        ("剩余: 3小时20分钟", 12000),
        ("剩余时间: 45秒", 45),
        ("还需 2小时", 7200),
    ])
    def test_parse_remaining_time(self, text, expected):
        """测试剩余时间解析"""
        result = parse_time_remaining(text)
        assert result == expected


class TestFormatCooldown:
    """Test format_cooldown function"""
    
    @pytest.mark.parametrize("seconds,expected", [
        (45, "45秒"),
        (200, "3分钟20秒"),
        (3600, "1小时"),
        (3661, "1小时1分钟1秒"),
        (45000, "12小时30分钟"),
        (86400, "24小时"),
        (90061, "25小时1分钟1秒"),
    ])
    def test_format_cooldown(self, seconds, expected):
        """测试冷却时间格式化"""
        result = format_cooldown(seconds)
        assert result == expected
    
    def test_format_zero(self):
        """测试格式化0秒"""
        result = format_cooldown(0)
        assert result == "0秒"


class TestEdgeCases:
    """Test edge cases"""
    
    def test_very_long_cooldown(self):
        """测试超长冷却时间"""
        text = "请在 48小时 后再来"
        result = _extract_cooldown_seconds(text)
        assert result == 172800
    
    def test_only_minutes_and_seconds(self):
        """测试只有分钟和秒"""
        text = "59分钟59秒"
        result = _extract_cooldown_seconds(text)
        assert result == 3599
    
    def test_only_hours_and_seconds(self):
        """测试只有小时和秒"""
        text = "2小时30秒"
        result = _extract_cooldown_seconds(text)
        assert result == 7230
    
    def test_multiple_time_expressions(self):
        """测试多个时间表达式（会累加所有匹配的时间）"""
        text = "请在 12小时 后再来，或者等待 24小时"
        result = _extract_cooldown_seconds(text)
        # 会累加所有时间表达式：12 + 24 = 36小时
        assert result == 129600  # 36 * 3600


class TestRealWorldExamples:
    """Test with real-world response examples"""
    
    def test_biguan_response(self):
        """测试闭关响应"""
        text = "闭关成功！你进入了深度冥想状态。需要打坐调息 16分钟 方可再次闭关。"
        result = _extract_cooldown_seconds(text, "闭关修炼")
        assert result == 960
    
    def test_yindao_response(self):
        """测试引道响应"""
        text = "你引动了水系之力！请在 12小时 后再次引道。"
        result = _extract_cooldown_seconds(text, "引道")
        assert result == 43200
    
    def test_rift_storm_response(self):
        """测试裂缝风暴响应"""
        text = "你遭遇了空间风暴，受到重创！请在 12小时30分钟 后再行探寻。"
        result = _extract_cooldown_seconds(text, "探寻裂缝")
        assert result == 45000
    
    def test_star_condensing(self):
        """测试星辰凝聚"""
        text = "1号引星盘: 天雷星 - 凝聚中 (剩余: 23小时45分钟)"
        result = parse_time_remaining(text)
        assert result == 85500
    
    def test_herb_growing(self):
        """测试药材生长"""
        text = "1号灵田: 凝血草种子 - 生长中 (剩余: 3小时20分钟)"
        result = parse_time_remaining(text)
        assert result == 12000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
