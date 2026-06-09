import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-for-api-tests")


@pytest.fixture(scope="module")
def app():
    from server import app, _app_state
    _app_state["memory_manager"] = MagicMock()
    _app_state["memory_manager"].get_memory_stats.return_value = {"total": 0}
    _app_state["conversation_store"] = MagicMock()
    convs = {
        "test-uuid": {
            "title": "新对话",
            "messages": [],
            "created": "01/01 00:00",
        }
    }
    _app_state["conversation_store"].load.return_value = (convs, "test-uuid")
    _app_state["conversation_store"].save.return_value = None
    _app_state["mem0_bridge"] = MagicMock()
    _app_state["mem0_bridge"].mem0_client = None
    _app_state["multimodal"] = False
    _app_state["working_memory_store"] = MagicMock()
    _app_state["working_memory_store"].format_for_prompt.return_value = ""
    return app


@pytest.fixture(scope="module")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        with patch("server._check_llm_connectivity", new_callable=AsyncMock) as mock_llm, \
             patch("server._check_mem0_connectivity", new_callable=AsyncMock) as mock_mem0:
            mock_llm.return_value = "ok"
            mock_mem0.return_value = "not_configured"
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "dependencies" in data
            assert "llm" in data["dependencies"]
            assert "mem0" in data["dependencies"]

    def test_health_v1_works(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200


class TestAPIVersioning:
    def test_v1_routes_exist(self, app):
        routes_v1 = [r.path for r in app.router.routes if hasattr(r, "path") and r.path.startswith("/api/v1/")]
        assert len(routes_v1) > 0

    def test_v1_health(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200


class TestConfigEndpoints:
    def test_get_model_config(self, client):
        response = client.get("/api/config/model")
        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert "base_url" in data

    def test_get_prompt_config(self, client):
        response = client.get("/api/config/prompt")
        assert response.status_code == 200
        data = response.json()
        assert "prompt" in data
        assert "default_prompt" in data
        assert "is_custom" in data

    def test_get_model_presets(self, client):
        response = client.get("/api/config/model-presets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_update_prompt_empty_restores_default(self, client):
        response = client.put("/api/config/prompt", json={"prompt": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["is_custom"] is False

    def test_update_prompt_custom(self, client):
        response = client.put("/api/config/prompt", json={"prompt": "你是一只小猫"})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "小猫" in data["prompt"]
        # 清理：恢复默认 prompt，避免污染实际配置
        client.put("/api/config/prompt", json={"prompt": ""})


class TestUsersEndpoint:
    def test_get_users(self, client):
        response = client.get("/api/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_user(self, client):
        response = client.post("/api/users?user_id=test_api_user")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["user_id"] == "test_api_user"


class TestConversationsEndpoint:
    def test_get_conversations(self, client):
        response = client.get("/api/conversations/test_user")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "current_id" in data
        assert isinstance(data["conversations"], list)

    def test_create_conversation(self, client):
        response = client.post("/api/conversations/test_user")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "新对话"

    def test_rename_conversation(self, client):
        create_resp = client.post("/api/conversations/test_user")
        cid = create_resp.json()["id"]
        response = client.patch(f"/api/conversations/test_user/{cid}", json={"title": "测试对话"})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["title"] == "测试对话"

    def test_delete_conversation(self, client):
        create_resp = client.post("/api/conversations/test_user")
        cid = create_resp.json()["id"]
        response = client.delete(f"/api/conversations/test_user/{cid}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "current_id" in data

    def test_get_nonexistent_conversation(self, client):
        response = client.get("/api/conversations/test_user/nonexistent-id")
        assert response.status_code == 404


class TestMemoryEndpoint:
    def test_get_memory_stats(self, client):
        response = client.get("/api/memory/test_user/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data


class TestSSEStreaming:
    def test_chat_sse_with_empty_message_returns_422(self, client):
        response = client.post(
            "/api/chat/test_user",
            json={"message": "", "conversation_history": []},
        )
        assert response.status_code == 422

    def test_chat_sse_too_long_message_returns_422(self, client):
        response = client.post(
            "/api/chat/test_user",
            json={"message": "x" * 10001, "conversation_history": []},
        )
        assert response.status_code == 422


class TestRateLimit:
    def test_chat_rate_limit_returns_429(self, client):
        with patch("server._chat_limiter.is_allowed", return_value=False):
            response = client.post(
                "/api/chat/test_user",
                json={"message": "你好", "conversation_history": []},
            )
            assert response.status_code == 429
            assert "过于频繁" in response.json()["detail"]


class TestLogsEndpoint:
    def test_get_logs(self, client):
        response = client.get("/api/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)