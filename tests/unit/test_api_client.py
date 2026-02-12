"""
utils.api_client 單元測試
驗證 ApiClient REST API 客戶端的初始化、Token 設定與各 HTTP 方法呼叫。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.mark.unit
class TestApiClientInit:
    """ApiClient.__init__ — 初始化"""

    @pytest.mark.unit
    def test_base_url_trailing_slash_stripped(self):
        """base_url 結尾的斜線被移除"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_requests.Session.return_value = MagicMock()
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com/")
            assert client.base_url == "https://api.example.com"

    @pytest.mark.unit
    def test_base_url_without_trailing_slash(self):
        """base_url 沒有結尾斜線時保持原樣"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_requests.Session.return_value = MagicMock()
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            assert client.base_url == "https://api.example.com"

    @pytest.mark.unit
    def test_session_headers_set(self):
        """session 的 Content-Type header 被設定"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            ApiClient("https://api.example.com")

            mock_session.headers.update.assert_called_once_with(
                {"Content-Type": "application/json"}
            )

    @pytest.mark.unit
    def test_default_timeout(self):
        """預設 timeout 為 30"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_requests.Session.return_value = MagicMock()
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            assert client.timeout == 30

    @pytest.mark.unit
    def test_custom_timeout(self):
        """可以自訂 timeout"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_requests.Session.return_value = MagicMock()
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com", timeout=60)
            assert client.timeout == 60

    @pytest.mark.unit
    def test_multiple_trailing_slashes_stripped(self):
        """多個結尾斜線只移除最後一個"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_requests.Session.return_value = MagicMock()
            from utils.api_client import ApiClient

            # rstrip("/") 會移除所有結尾斜線
            client = ApiClient("https://api.example.com///")
            assert client.base_url == "https://api.example.com"


@pytest.mark.unit
class TestSetToken:
    """ApiClient.set_token — 設定 Bearer Token"""

    @pytest.mark.unit
    def test_bearer_token_set_in_headers(self):
        """設定 Bearer token 到 session headers"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_session.headers = {}
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.set_token("my_secret_token")

            assert client.session.headers["Authorization"] == "Bearer my_secret_token"

    @pytest.mark.unit
    def test_token_can_be_updated(self):
        """token 可以被更新"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_session.headers = {}
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.set_token("token1")
            client.set_token("token2")

            assert client.session.headers["Authorization"] == "Bearer token2"


@pytest.mark.unit
class TestGet:
    """ApiClient.get — GET 請求"""

    @pytest.mark.unit
    def test_correct_url_built(self):
        """URL 正確組合"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.get.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.get("/users")

            mock_session.get.assert_called_once_with(
                "https://api.example.com/users",
                params=None,
                timeout=30,
            )

    @pytest.mark.unit
    def test_params_passed(self):
        """查詢參數正確傳遞"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.get.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            params = {"page": 1, "limit": 10}
            client.get("/users", params=params)

            mock_session.get.assert_called_once_with(
                "https://api.example.com/users",
                params=params,
                timeout=30,
            )

    @pytest.mark.unit
    def test_response_returned(self):
        """回傳 response 物件"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.get.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            result = client.get("/users")

            assert result == mock_response

    @pytest.mark.unit
    def test_path_leading_slash_handled(self):
        """path 開頭的斜線正確處理"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.get.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.get("users")

            mock_session.get.assert_called_once_with(
                "https://api.example.com/users",
                params=None,
                timeout=30,
            )


@pytest.mark.unit
class TestPost:
    """ApiClient.post — POST 請求"""

    @pytest.mark.unit
    def test_correct_url_built(self):
        """URL 正確組合"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_session.post.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.post("/users")

            mock_session.post.assert_called_once_with(
                "https://api.example.com/users",
                json=None,
                timeout=30,
            )

    @pytest.mark.unit
    def test_json_data_passed(self):
        """JSON 資料正確傳遞"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_session.post.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            data = {"name": "test_user", "email": "test@test.com"}
            client.post("/users", json_data=data)

            mock_session.post.assert_called_once_with(
                "https://api.example.com/users",
                json=data,
                timeout=30,
            )

    @pytest.mark.unit
    def test_response_returned(self):
        """回傳 response 物件"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_session.post.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            result = client.post("/users", json_data={"name": "test"})

            assert result == mock_response


@pytest.mark.unit
class TestPut:
    """ApiClient.put — PUT 請求"""

    @pytest.mark.unit
    def test_correct_url_built(self):
        """URL 正確組合"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.put.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.put("/users/1")

            mock_session.put.assert_called_once_with(
                "https://api.example.com/users/1",
                json=None,
                timeout=30,
            )

    @pytest.mark.unit
    def test_json_data_passed(self):
        """JSON 資料正確傳遞"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.put.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            data = {"name": "updated_user"}
            client.put("/users/1", json_data=data)

            mock_session.put.assert_called_once_with(
                "https://api.example.com/users/1",
                json=data,
                timeout=30,
            )

    @pytest.mark.unit
    def test_response_returned(self):
        """回傳 response 物件"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.put.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            result = client.put("/users/1", json_data={"name": "x"})

            assert result == mock_response


@pytest.mark.unit
class TestDelete:
    """ApiClient.delete — DELETE 請求"""

    @pytest.mark.unit
    def test_correct_url_built(self):
        """URL 正確組合"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_session.delete.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.delete("/users/1")

            mock_session.delete.assert_called_once_with(
                "https://api.example.com/users/1",
                timeout=30,
            )

    @pytest.mark.unit
    def test_response_returned(self):
        """回傳 response 物件"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_session.delete.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            result = client.delete("/users/1")

            assert result == mock_response

    @pytest.mark.unit
    def test_delete_with_path_no_leading_slash(self):
        """path 沒有開頭斜線時也正確組合 URL"""
        with patch("utils.api_client.requests") as mock_requests:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_session.delete.return_value = mock_response
            mock_requests.Session.return_value = mock_session
            from utils.api_client import ApiClient

            client = ApiClient("https://api.example.com")
            client.delete("users/1")

            mock_session.delete.assert_called_once_with(
                "https://api.example.com/users/1",
                timeout=30,
            )
