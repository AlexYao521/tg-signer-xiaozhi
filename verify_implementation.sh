#!/bin/bash
# 实现验证脚本
# Verification script for channel automation bot implementation

echo "===================================================="
echo "频道自动化机器人实现验证"
echo "Channel Automation Bot Implementation Verification"
echo "===================================================="
echo ""

PASSED=0
FAILED=0

# Function to run test
run_test() {
    local name="$1"
    local cmd="$2"
    
    echo -n "Testing: $name ... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✓ PASS"
        ((PASSED++))
    else
        echo "✗ FAIL"
        ((FAILED++))
    fi
}

# 1. Check file existence
echo "1. Checking files..."
run_test "bot_config.py exists" "test -f tg_signer/bot_config.py"
run_test "bot_worker.py exists" "test -f tg_signer/bot_worker.py"
run_test "xiaozhi_client.py exists" "test -f tg_signer/xiaozhi_client.py"
run_test "cli/bot.py exists" "test -f tg_signer/cli/bot.py"
run_test "test_bot_config.py exists" "test -f tests/test_bot_config.py"
run_test "test_xiaozhi_client.py exists" "test -f tests/test_xiaozhi_client.py"
run_test "test_integration.py exists" "test -f tests/test_integration.py"
run_test "example_bot_config.json exists" "test -f example_bot_config.json"
run_test "BOT_TESTING_GUIDE.md exists" "test -f BOT_TESTING_GUIDE.md"
run_test "IMPLEMENTATION_SUMMARY.md exists" "test -f IMPLEMENTATION_SUMMARY.md"

echo ""
echo "2. Testing imports..."
run_test "bot_config import" "python3 -c 'from tg_signer.bot_config import BotConfig'"
run_test "xiaozhi_client import" "python3 -c 'from tg_signer.xiaozhi_client import XiaozhiClient'"
run_test "bot_worker import" "python3 -c 'from tg_signer.bot_worker import ChannelBot'"
run_test "cli.bot import" "python3 -c 'from tg_signer.cli.bot import bot_cli'"

echo ""
echo "3. Testing configuration..."
run_test "Create default config" "python3 -c 'from tg_signer.bot_config import create_default_bot_config; create_default_bot_config(-1001234567890)'"
run_test "Config serialization" "python3 -c 'from tg_signer.bot_config import BotConfig; c=BotConfig(chat_id=-1001234567890); c.model_dump()'"
run_test "Example config valid" "python3 -c 'import json; from tg_signer.bot_config import BotConfig; BotConfig(**json.load(open(\"example_bot_config.json\")))'"

echo ""
echo "4. Testing CLI commands..."
run_test "bot --help" "python3 -m tg_signer bot --help"
run_test "bot list" "python3 -m tg_signer bot list"
run_test "bot doctor" "python3 -m tg_signer bot doctor"

echo ""
echo "5. Running integration tests..."

# Run integration tests
python3 << 'EOF' > /tmp/test_output.txt 2>&1
import sys
sys.path.insert(0, '.')

from tests.test_integration import (
    test_state_store_operations,
    test_command_queue_basic,
    test_command_queue_deduplication,
    test_bot_config_full_workflow,
    test_xiaozhi_client_creation_with_config,
    test_xiaozhi_client_disabled,
    test_bot_config_validation,
    test_example_bot_config_valid
)

tests = [
    ("State store operations", test_state_store_operations),
    ("Command queue basic", test_command_queue_basic),
    ("Command queue deduplication", test_command_queue_deduplication),
    ("Bot config full workflow", test_bot_config_full_workflow),
    ("Xiaozhi client creation", test_xiaozhi_client_creation_with_config),
    ("Xiaozhi client disabled", test_xiaozhi_client_disabled),
    ("Bot config validation", test_bot_config_validation),
    ("Example bot config valid", test_example_bot_config_valid),
]

passed = 0
failed = 0
for name, test_func in tests:
    try:
        test_func()
        print(f"✓ {name}")
        passed += 1
    except Exception as e:
        print(f"✗ {name}: {e}")
        failed += 1

print(f"\nIntegration tests: {passed}/{len(tests)} passed")
sys.exit(0 if failed == 0 else 1)
EOF

if [ $? -eq 0 ]; then
    cat /tmp/test_output.txt | grep "^✓" | while read line; do
        echo -n "Testing: "
        echo "$line" | sed 's/✓ //' | sed 's/ ... / ... /'
        echo "  ✓ PASS"
        ((PASSED++))
    done
    INTEGRATION_PASSED=$(cat /tmp/test_output.txt | grep "^✓" | wc -l)
    PASSED=$((PASSED + INTEGRATION_PASSED))
else
    echo "  ✗ Integration tests FAILED"
    cat /tmp/test_output.txt
    FAILED=$((FAILED + 8))
fi

echo ""
echo "===================================================="
echo "Verification Results"
echo "===================================================="
echo "Total tests: $((PASSED + FAILED))"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All checks passed! Implementation is complete."
    echo ""
    echo "Quick start:"
    echo "  1. tg-signer bot config my_bot"
    echo "  2. tg-signer bot doctor my_bot"
    echo "  3. tg-signer bot run my_bot"
    exit 0
else
    echo "⚠️  Some checks failed. Please review the errors above."
    exit 1
fi
