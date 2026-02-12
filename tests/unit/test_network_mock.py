"""
utils.network_mock 單元測試
驗證 NetworkMock API 攔截與模擬回應功能。
"""

import json
import time
import urllib.request

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestMockRule:
    """MockRule dataclass"""

    @pytest.mark.unit
    def test_default_values(self):
        """預設值正確"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern="/api/test")

        assert rule.url_pattern == "/api/test"
        assert rule.method == "*"
        assert rule.status == 200
        assert rule.body is None
        assert rule.headers == {}
        assert rule.delay == 0.0
        assert rule.passthrough is False

    @pytest.mark.unit
    def test_custom_values(self):
        """自訂值正確"""
        from utils.network_mock import MockRule

        rule = MockRule(
            url_pattern="/api/users",
            method="POST",
            status=201,
            body={"id": 1},
            headers={"X-Custom": "value"},
            delay=1.5,
            passthrough=False,
        )

        assert rule.url_pattern == "/api/users"
        assert rule.method == "POST"
        assert rule.status == 201
        assert rule.body == {"id": 1}
        assert rule.headers == {"X-Custom": "value"}
        assert rule.delay == 1.5

    @pytest.mark.unit
    def test_compiled_regex(self):
        """url_pattern 被編譯為正則表達式"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern="/api/users.*")

        assert rule._compiled is not None
        assert rule._compiled.search("/api/users/123")

    @pytest.mark.unit
    def test_matches_path(self):
        """matches 正確匹配路徑"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern="/api/users")

        assert rule.matches("/api/users") is True
        assert rule.matches("/api/users/1") is True  # 部分匹配 (search)
        assert rule.matches("/api/products") is False

    @pytest.mark.unit
    def test_matches_method_wildcard(self):
        """method='*' 匹配所有 HTTP 方法"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern="/api/test", method="*")

        assert rule.matches("/api/test", "GET") is True
        assert rule.matches("/api/test", "POST") is True
        assert rule.matches("/api/test", "DELETE") is True

    @pytest.mark.unit
    def test_matches_specific_method(self):
        """指定 method 只匹配該方法"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern="/api/test", method="POST")

        assert rule.matches("/api/test", "POST") is True
        assert rule.matches("/api/test", "GET") is False

    @pytest.mark.unit
    def test_matches_method_case_insensitive(self):
        """method 比較不區分大小寫"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern="/api/test", method="POST")

        assert rule.matches("/api/test", "post") is True
        assert rule.matches("/api/test", "Post") is True

    @pytest.mark.unit
    def test_matches_regex_pattern(self):
        """支援正則表達式匹配"""
        from utils.network_mock import MockRule

        rule = MockRule(url_pattern=r"/api/users/\d+")

        assert rule.matches("/api/users/123") is True
        assert rule.matches("/api/users/abc") is False


@pytest.mark.unit
class TestNetworkMockInit:
    """NetworkMock.__init__"""

    @pytest.mark.unit
    def test_default_values(self):
        """預設值正確"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()

        assert mock._host == "0.0.0.0"
        assert mock._port == 0
        assert mock._rules == []
        assert mock._history == []
        assert mock._server is None
        assert mock._thread is None

    @pytest.mark.unit
    def test_custom_host_and_port(self):
        """自訂 host 和 port"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock(host="127.0.0.1", port=8080)

        assert mock._host == "127.0.0.1"
        assert mock._port == 8080


@pytest.mark.unit
class TestNetworkMockMock:
    """NetworkMock.mock — 新增 mock 規則"""

    @pytest.mark.unit
    def test_adds_rule(self):
        """新增一條 mock 規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/users", status=200, body={"users": []})

        assert len(mock._rules) == 1
        assert mock._rules[0].url_pattern == "/api/users"
        assert mock._rules[0].status == 200
        assert mock._rules[0].body == {"users": []}

    @pytest.mark.unit
    def test_adds_multiple_rules(self):
        """新增多條 mock 規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/users")
        mock.mock("/api/products")
        mock.mock("/api/orders")

        assert len(mock._rules) == 3

    @pytest.mark.unit
    def test_returns_self_for_chaining(self):
        """回傳自身以支援鏈式呼叫"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        result = mock.mock("/api/users")

        assert result is mock

    @pytest.mark.unit
    def test_chained_mock_calls(self):
        """鏈式呼叫新增多條規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/a").mock("/api/b").mock("/api/c")

        assert len(mock._rules) == 3

    @pytest.mark.unit
    def test_rule_with_delay(self):
        """規則包含 delay"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/slow", delay=5.0)

        assert mock._rules[0].delay == 5.0

    @pytest.mark.unit
    def test_rule_with_method(self):
        """規則包含指定 method"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/users", method="POST", status=201)

        assert mock._rules[0].method == "POST"
        assert mock._rules[0].status == 201

    @pytest.mark.unit
    def test_rule_with_custom_headers(self):
        """規則包含自訂 headers"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/test", headers={"X-Rate-Limit": "100"})

        assert mock._rules[0].headers == {"X-Rate-Limit": "100"}


@pytest.mark.unit
class TestNetworkMockMockError:
    """NetworkMock.mock_error — 模擬錯誤回應"""

    @pytest.mark.unit
    def test_adds_error_rule(self):
        """新增錯誤規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock_error("/api/login", status=500)

        assert len(mock._rules) == 1
        assert mock._rules[0].status == 500
        assert mock._rules[0].body == {"error": "模擬錯誤 500"}

    @pytest.mark.unit
    def test_default_status_500(self):
        """預設狀態碼 500"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock_error("/api/error")

        assert mock._rules[0].status == 500

    @pytest.mark.unit
    def test_custom_error_body(self):
        """自訂錯誤 body"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock_error("/api/error", body={"msg": "custom error"})

        assert mock._rules[0].body == {"msg": "custom error"}

    @pytest.mark.unit
    def test_returns_self(self):
        """回傳自身"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        result = mock.mock_error("/api/error")

        assert result is mock


@pytest.mark.unit
class TestNetworkMockMockTimeout:
    """NetworkMock.mock_timeout — 模擬逾時"""

    @pytest.mark.unit
    def test_adds_timeout_rule(self):
        """新增逾時規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock_timeout("/api/slow")

        assert len(mock._rules) == 1
        assert mock._rules[0].delay == 30.0
        assert mock._rules[0].status == 408

    @pytest.mark.unit
    def test_custom_delay(self):
        """自訂延遲時間"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock_timeout("/api/slow", delay=60.0)

        assert mock._rules[0].delay == 60.0

    @pytest.mark.unit
    def test_returns_self(self):
        """回傳自身"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        result = mock.mock_timeout("/api/slow")

        assert result is mock


@pytest.mark.unit
class TestNetworkMockMockEmpty:
    """NetworkMock.mock_empty — 模擬空資料"""

    @pytest.mark.unit
    def test_adds_empty_response_rule(self):
        """新增空回應規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock_empty("/api/data")

        assert len(mock._rules) == 1
        assert mock._rules[0].body == []
        assert mock._rules[0].status == 200

    @pytest.mark.unit
    def test_returns_self(self):
        """回傳自身"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        result = mock.mock_empty("/api/data")

        assert result is mock


@pytest.mark.unit
class TestNetworkMockClear:
    """NetworkMock.clear — 清除所有規則"""

    @pytest.mark.unit
    def test_clears_all_rules(self):
        """清除所有 mock 規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/a")
        mock.mock("/api/b")
        mock.mock("/api/c")

        assert len(mock._rules) == 3

        mock.clear()

        assert len(mock._rules) == 0

    @pytest.mark.unit
    def test_clear_empty_rules(self):
        """清除空規則列表不報錯"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.clear()

        assert len(mock._rules) == 0


@pytest.mark.unit
class TestNetworkMockRemove:
    """NetworkMock.remove — 移除特定規則"""

    @pytest.mark.unit
    def test_removes_specific_rule(self):
        """移除指定 URL 的規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/a")
        mock.mock("/api/b")
        mock.mock("/api/c")

        mock.remove("/api/b")

        assert len(mock._rules) == 2
        patterns = [r.url_pattern for r in mock._rules]
        assert "/api/b" not in patterns

    @pytest.mark.unit
    def test_remove_nonexistent_rule(self):
        """移除不存在的規則不報錯"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/a")

        mock.remove("/api/nonexistent")

        assert len(mock._rules) == 1

    @pytest.mark.unit
    def test_removes_all_matching_rules(self):
        """移除所有匹配的同 URL 規則"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock.mock("/api/a", status=200)
        mock.mock("/api/a", status=500)

        mock.remove("/api/a")

        assert len(mock._rules) == 0


@pytest.mark.unit
class TestNetworkMockAssertCalled:
    """NetworkMock.assert_called — 斷言 URL 被呼叫"""

    @pytest.mark.unit
    def test_assert_called_with_matching_history(self):
        """有匹配記錄時不拋出例外"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 1.0},
        ]

        # 不應拋出例外
        mock.assert_called("/api/users")

    @pytest.mark.unit
    def test_assert_called_without_matching_history(self):
        """無匹配記錄時拋出 AssertionError"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = []

        with pytest.raises(AssertionError, match="從未被呼叫"):
            mock.assert_called("/api/users")

    @pytest.mark.unit
    def test_assert_called_with_times(self):
        """驗證呼叫次數"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 1.0},
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 2.0},
        ]

        mock.assert_called("/api/users", times=2)

    @pytest.mark.unit
    def test_assert_called_with_wrong_times(self):
        """呼叫次數不符時拋出 AssertionError"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 1.0},
        ]

        with pytest.raises(AssertionError, match="被呼叫"):
            mock.assert_called("/api/users", times=3)

    @pytest.mark.unit
    def test_assert_called_with_method_filter(self):
        """指定 method 篩選"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 1.0},
            {"method": "POST", "path": "/api/users", "headers": {}, "body": "", "timestamp": 2.0},
        ]

        mock.assert_called("/api/users", method="POST", times=1)

    @pytest.mark.unit
    def test_assert_called_method_wildcard(self):
        """method='*' 匹配所有方法"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 1.0},
            {"method": "POST", "path": "/api/users", "headers": {}, "body": "", "timestamp": 2.0},
        ]

        mock.assert_called("/api/users", method="*", times=2)


@pytest.mark.unit
class TestNetworkMockAssertNotCalled:
    """NetworkMock.assert_not_called — 斷言 URL 未被呼叫"""

    @pytest.mark.unit
    def test_assert_not_called_with_no_history(self):
        """無記錄時不拋出例外"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = []

        mock.assert_not_called("/api/users")

    @pytest.mark.unit
    def test_assert_not_called_with_matching_history(self):
        """有匹配記錄時拋出 AssertionError"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/users", "headers": {}, "body": "", "timestamp": 1.0},
        ]

        with pytest.raises(AssertionError, match="被呼叫了"):
            mock.assert_not_called("/api/users")

    @pytest.mark.unit
    def test_assert_not_called_with_different_path(self):
        """不同路徑時不拋出例外"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        mock._history = [
            {"method": "GET", "path": "/api/products", "headers": {}, "body": "", "timestamp": 1.0},
        ]

        mock.assert_not_called("/api/users")


@pytest.mark.unit
class TestNetworkMockContextManager:
    """NetworkMock context manager"""

    @pytest.mark.unit
    def test_enter_calls_start(self):
        """__enter__ 呼叫 start()"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()

        with patch.object(mock, "start") as mock_start, \
             patch.object(mock, "stop"):
            mock_start.return_value = "http://localhost:12345"
            with mock as m:
                assert m is mock
            mock_start.assert_called_once()

    @pytest.mark.unit
    def test_exit_calls_stop(self):
        """__exit__ 呼叫 stop()"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()

        with patch.object(mock, "start") as mock_start, \
             patch.object(mock, "stop") as mock_stop:
            mock_start.return_value = "http://localhost:12345"
            with mock:
                pass
            mock_stop.assert_called_once()

    @pytest.mark.unit
    def test_context_manager_returns_self(self):
        """context manager 回傳自身"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()

        with patch.object(mock, "start") as mock_start, \
             patch.object(mock, "stop"):
            mock_start.return_value = "http://localhost:12345"
            with mock as m:
                assert isinstance(m, NetworkMock)


@pytest.mark.unit
class TestNetworkMockHistory:
    """NetworkMock.history property"""

    @pytest.mark.unit
    def test_history_returns_copy(self):
        """history 回傳副本而非原始列表"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        record = {"method": "GET", "path": "/api/test", "headers": {}, "body": "", "timestamp": 1.0}
        mock._history.append(record)

        history = mock.history
        assert len(history) == 1
        assert history is not mock._history

    @pytest.mark.unit
    def test_history_empty_initially(self):
        """初始時 history 為空"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        assert mock.history == []


@pytest.mark.unit
class TestNetworkMockUrl:
    """NetworkMock.url property"""

    @pytest.mark.unit
    def test_url_empty_when_no_server(self):
        """server 未啟動時 url 為空字串"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        assert mock.url == ""

    @pytest.mark.unit
    def test_port_zero_when_no_server(self):
        """server 未啟動時 port 為 0"""
        from utils.network_mock import NetworkMock

        mock = NetworkMock()
        assert mock.port == 0
