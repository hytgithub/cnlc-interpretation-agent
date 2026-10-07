"""原生服务集成测试：通过 HTTP 接口触发真实 AgentScope 执行循环。

TestClient 在当前测试进程内运行服务和生命周期。
它仍执行原生路由、会话存储、工具与中间件，不直接代替 Agent 调用业务函数。
真实网络连接与 SSE 的测试见 test_http_sse.py。
"""

import json
import time

import pytest
from agentscope.message import UserMsg
from fastapi.testclient import TestClient

from cnlc_agent.app import build_app
from cnlc_agent.framework import ALLOWED_TOOLS, TEST_TOOLS, ScriptedModel


def bootstrap(client):
    """依次创建脚本模型凭据、智能体定义和绑定该模型的会话。"""
    response = client.post("/credential/", json={"data": {"type": "scripted_mock"}})
    assert response.status_code == 201, response.text
    credential = response.json()["credential_id"]
    response = client.post("/agent/", json={"name": "测井助手", "system_prompt": "依据实际工具结果回答。"})
    assert response.status_code == 201, response.text
    agent = response.json()["agent_id"]
    body = {"agent_id": agent, "name": "框架验证", "chat_model_config": {
        "type": "scripted_mock", "credential_id": credential, "model": "scripted", "parameters": {}}}
    response = client.post("/sessions/", json=body)
    assert response.status_code == 201, response.text
    return agent, response.json()["session_id"], body


def select(client, agent, session, revision=0, top=2000, bottom=2120):
    """通过业务接口设置选择，用于检查与聊天工具共用的业务约束。"""
    return client.put(f"/business/sessions/{session}/selection", params={"agent_id": agent},
                      json={"expected_revision": revision, "top_depth_m": top, "bottom_depth_m": bottom})


def send(client, agent, session, tool, arguments=None):
    """把明确 JSON 指令放入原生 UserMsg，并提交到 /chat。"""
    content = json.dumps({"tool": tool, "arguments": arguments or {}})
    msg = UserMsg(name="prototype-tester", content=content).model_dump(mode="json")
    response = client.post("/chat/", json={"agent_id": agent, "session_id": session, "input": msg})
    assert response.status_code == 200, response.text
    # started 只表示请求被框架接收，结果需要另行等待。
    assert response.json()["status"] == "started"


def messages(client, agent, session):
    """读取原生持久化会话历史，不直接读取模型内部上下文。"""
    return client.get(f"/sessions/{session}/messages", params={"agent_id": agent}).json()


def wait_reply(client, agent, session, previous=0):
    """普通测试等待新回复落盘，最多 5 秒，不适用于 12 秒耗时用例。"""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        data = messages(client, agent, session)
        replies = [x for x in data["messages"] if x["role"] == "assistant" and x.get("finished_at")]
        # previous 用于排除旧回复。is_running=False 表示前台回复结束。
        # 即使前台回复结束，后台业务运行仍需通过业务接口单独检查。
        if len(replies) > previous and not data["is_running"]:
            reply = replies[-1]
            assert reply["finished_reason"] == "completed", reply
            return reply
        time.sleep(.025)
    raise AssertionError("原生智能体未在 5 秒内结束。")


def final_json(reply):
    """提取最后一个最终文字块。脚本模型把它约定为可检查的 JSON。"""
    return json.loads([x["text"] for x in reply["content"] if x["type"] == "text"][-1])


@pytest.mark.parametrize("tool", ["get_well_data", "identify_lithology", "merge_intervals"])
def test_native_service_calls_business_tools_and_filters_toolkit(tmp_path, tool):
    """无需预先设置选择，原生 Agent 可以直接调用专业工具。"""
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        well = client.get("/business/well").json()
        arguments = {} if tool == "get_well_data" else {
            "well_id": well["well_id"], "dataset_revision": well["dataset_revision"],
            "top_depth_m": 2000, "bottom_depth_m": 2001,
        }
        send(client, agent, session, tool, arguments)
        reply = wait_reply(client, agent, session)
        result = final_json(reply)
        assert result["status"] == "SUCCESS"
        assert result["is_mock"] is True
        assert any(x["type"] == "tool_call" and x["name"] == tool for x in reply["content"])
        manifest = client.get(f"/business/sessions/{session}/tools", params={"agent_id": agent}).json()["manifest"]
        # AgentScope Skills are registered as skills, not FunctionTools,
        # so the runtime manifest lists only callable tools.
        assert set(manifest["tool_names"]) == ALLOWED_TOOLS - TEST_TOOLS
        assert "start_mock_interpretation" not in manifest["tool_names"]
        assert client.get(f"/business/sessions/{session}/selection", params={"agent_id": agent}).json()["selection"] is None
        assert client.get(f"/business/sessions/{session}/interpretation-runs", params={"agent_id": agent}).json()["runs"] == []
        if tool == "get_well_data":
            assert result["output"]["null_counts"]["GR"] == 4
        if tool == "merge_intervals":
            assert result["output"]["result"]["intervals"][0]["layer_no"] == 1


def test_agent_can_use_explicit_scope_without_mutating_selection(tmp_path):
    """专业工具直接接收范围，模型不需要选择设置入口。"""
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        well = client.get("/business/well").json()
        send(client, agent, session, "get_well_data", {
            "well_id": well["well_id"], "top_depth_m": 2000, "bottom_depth_m": 2001,
            "curve_names": ["GR"],
        })
        result = final_json(wait_reply(client, agent, session))
        assert result["status"] == "SUCCESS"
        assert len(result["output"]["curve_data"]["curves"]["GR"]["points"]) == 11
        assert client.get(f"/business/sessions/{session}/selection", params={"agent_id": agent}).json()["selection"] is None


def test_native_middleware_receives_context_and_stale_dataset_is_rejected(tmp_path, monkeypatch):
    """捕获模型输入；专业工具仍校验显式资料版本。"""
    captured = []
    original = ScriptedModel._call_api

    async def capture(self, *args, **kwargs):
        # 只观察输入，仍调用原始测试模型，不替换其响应和工具执行。
        inputs = args[1] if len(args) > 1 else kwargs["messages"]
        captured.extend(x.model_dump(mode="json") for x in inputs if x.role == "system")
        return await original(self, *args, **kwargs)

    # monkeypatch 在本测试结束后自动恢复，其他测试不受影响。
    monkeypatch.setattr(ScriptedModel, "_call_api", capture)
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        select(client, agent, session)
        select(client, agent, session, revision=1, top=2010, bottom=2020)
        well = client.get("/business/well").json()
        send(client, agent, session, "identify_lithology", {
            "well_id": well["well_id"], "dataset_revision": "stale",
            "top_depth_m": 2010, "bottom_depth_m": 2020,
        })
        result = final_json(wait_reply(client, agent, session))
        assert result["code"] == "DATASET_VERSION_CONFLICT"
        prompts = [b["text"] for x in captured for b in x["content"] if b["type"] == "text"]
        assert any('"revision": 2' in text for text in prompts)
        assert any('"top_depth_m": 2010.0' in text for text in prompts)


def test_http_session_isolation_and_ownership(tmp_path):
    """同一用户的两个会话各有独立范围，其他用户不能读写该会话选择。"""
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, first, body = bootstrap(client)
        second = client.post("/sessions/", json=body).json()["session_id"]
        assert second != first
        select(client, agent, first, top=2000, bottom=2010)
        select(client, agent, second, top=2100, bottom=2120)
        first_url = f"/business/sessions/{first}/selection"
        params = {"agent_id": agent}
        assert client.get(first_url, params=params).json()["selection"]["top_depth_m"] == 2000
        assert client.get(f"/business/sessions/{second}/selection", params=params).json()["selection"]["top_depth_m"] == 2100
        assert client.get(first_url, params=params, headers={"X-User-ID": "other"}).status_code == 404
        assert client.put(first_url, params=params, headers={"X-User-ID": "other"}, json={
            "expected_revision": 1, "top_depth_m": 2000, "bottom_depth_m": 2120}).status_code == 404


def test_native_sessions_and_business_results_survive_restart(tmp_path):
    """结束第一个服务生命周期，再用相同目录启动第二个服务对象。"""
    app = build_app(tmp_path, include_test_tools=True)
    with TestClient(app, headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        select(client, agent, session)
        send(client, agent, session, "slow_mock_statistics", {"expected_selection_revision": 1, "delay_seconds": 0})
        success = final_json(wait_reply(client, agent, session))
        assert success["status"] == "SUCCEEDED"
        # 预置一个遗留 RUNNING 记录，模拟进程结束后不能恢复的内存作业。
        # 这不是完整的进程崩溃或外部作业恢复测试。
        app.state.business_store.start_run("owner", session, "slow_mock_statistics", app.state.business_store.selection("owner", session))
    with TestClient(build_app(tmp_path, include_test_tools=True), headers={"X-User-ID": "owner"}) as client:
        params = {"agent_id": agent}
        assert client.get(f"/business/sessions/{session}/selection", params=params).json()["selection"]["revision"] == 1
        runs = client.get(f"/business/sessions/{session}/runs", params=params).json()["runs"]
        assert runs[0]["run_id"] == success["run_id"] and runs[0]["status"] == "SUCCEEDED"
        assert runs[1]["status"] == "UNKNOWN"
        assert final_json(messages(client, agent, session)["messages"][-1])["run_id"] == success["run_id"]


def test_script_model_marks_natural_language_unassessed(tmp_path):
    """输入中文自然语言，确认脚本模型不把格式解析宣称为理解能力。"""
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        msg = UserMsg(name="tester", content="请读取当前井").model_dump(mode="json")
        client.post("/chat/", json={"agent_id": agent, "session_id": session, "input": msg})
        reply = wait_reply(client, agent, session)
        assert final_json(reply)["status"] == "UNASSESSED"
        assert not any(x["type"] == "tool_call" for x in reply["content"])


def test_native_tool_failure_keeps_success_queryable(tmp_path):
    """通过原生工具执行失败分支，检查错误状态和旧成功结果保留。"""
    with TestClient(build_app(tmp_path, include_test_tools=True), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        select(client, agent, session)
        arguments = {"expected_selection_revision": 1, "delay_seconds": 0}
        send(client, agent, session, "slow_mock_statistics", arguments)
        success = final_json(wait_reply(client, agent, session))
        send(client, agent, session, "slow_mock_statistics", {**arguments, "fail": True})
        reply = wait_reply(client, agent, session, previous=1)
        assert final_json(reply)["status"] == "FAILED"
        assert any(x["type"] == "tool_result" and x["state"] == "error" for x in reply["content"])
        runs = client.get(f"/business/sessions/{session}/runs", params={"agent_id": agent}).json()["runs"]
        assert runs[0]["run_id"] == success["run_id"] and runs[0]["status"] == "SUCCEEDED"
        assert runs[1]["status"] == "FAILED"


@pytest.mark.parametrize("tool", [
    "read_mock_well", "set_mock_selection", "query_mock_intervals",
    "calculate_mock_statistics", "start_mock_interpretation", "get_mock_interpretation_run",
])
def test_old_prototype_entries_cannot_be_called_by_model(tmp_path, tool):
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        send(client, agent, session, tool)
        reply = wait_reply(client, agent, session)
        assert final_json(reply)["code"] == "TOOL_NOT_ALLOWED"
        assert not any(item["type"] == "tool_call" for item in reply["content"])


def test_agent_can_read_bundled_interpretation_skill(tmp_path):
    """通过原生 Skill 工具读取已注册的流程，而非只把文件放在包里。"""
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        send(client, agent, session, "Skill", {"skill": "conventional-log-interpretation"})
        reply = wait_reply(client, agent, session)
        assert final_json(reply)["status"] == "SUCCESS"
        output = next(item for item in reply["content"] if item["type"] == "tool_result")
        assert output["state"] == "success"


def test_native_service_queries_updates_and_reruns_only_requested_step(tmp_path):
    """交互工具经实际 AgentScope 装配可调用，修改与执行使用同一修订。"""
    with TestClient(build_app(tmp_path), headers={'X-User-ID': 'owner'}) as client:
        agent, session, _ = bootstrap(client)
        well = client.get('/business/well').json()
        scope = dict(well_id=well['well_id'], dataset_revision=well['dataset_revision'],
                     top_depth_m=2000, bottom_depth_m=2001)
        send(client, agent, session, 'query_interval_results', {**scope, 'layer_no': 1})
        query = final_json(wait_reply(client, agent, session))
        assert query['output']['intervals'][0]['layer_no'] == 1
        send(client, agent, session, 'get_processing_parameters', {**scope, 'step_id': 'curve_quality'})
        settings = final_json(wait_reply(client, agent, session, previous=1))
        send(client, agent, session, 'update_processing_parameters', {
            **scope, 'step_id': 'curve_quality', 'expected_revision': settings['revision'],
            'changes': {'sampling_interval_m': 0.2},
        })
        updated = final_json(wait_reply(client, agent, session, previous=2))
        send(client, agent, session, 'rerun_step', {
            **scope, 'step_id': 'curve_quality', 'expected_parameter_revision': updated['revision'],
        })
        rerun = final_json(wait_reply(client, agent, session, previous=3))
        assert rerun['executed_tools'] == ['check_curve_quality']
        assert rerun['results'][0]['parameter_snapshot']['parameters']['sampling_interval_m'] == 0.2
        assert client.get(f'/business/sessions/{session}/selection', params={'agent_id': agent}).json()['selection'] is None
        assert client.get(f'/business/sessions/{session}/interpretation-runs', params={'agent_id': agent}).json()['runs'] == []


def test_native_curve_plot_metadata_and_owned_artifact_route(tmp_path):
    """绘图经真实工具循环返回可用图表，读取拒绝其他用户和会话。"""
    with TestClient(build_app(tmp_path), headers={'X-User-ID': 'owner'}) as client:
        agent, session, body = bootstrap(client)
        well = client.get('/business/well').json()
        scope = dict(well_id=well['well_id'], dataset_revision=well['dataset_revision'],
                     top_depth_m=2000, bottom_depth_m=2010)
        send(client, agent, session, 'plot_curves', {**scope, 'curve_names': ['GR', 'RT'], 'log_curve_names': ['RT']})
        reply = wait_reply(client, agent, session)
        payload = final_json(reply)
        assert payload['status'] == 'SUCCESS'
        output = next(block for block in reply['content'] if block['type'] == 'tool_result')
        chart = output['metadata']['curve_plot']
        assert chart['plot_id'] == payload['plot_id']
        assert payload['chart']['url'] == chart['url']
        assert payload['chart']['format'] == 'svg'
        assert payload['chart']['display'] == 'inline'
        assert payload['chart']['track_count'] == 2
        assert payload['chart']['overlays'] == []
        assert 'artifact_id' not in payload
        url = chart['url']
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/svg+xml')
        assert response.headers['cache-control'] == 'private, no-store'
        assert '<svg' in response.text and 'GR' in response.text and 'RT' in response.text
        assert client.get(url, headers={'X-User-ID': 'other'}).status_code == 404
        second = client.post('/sessions/', json=body).json()['session_id']
        other_url = url.replace(f'/sessions/{session}/', f'/sessions/{second}/')
        assert client.get(other_url).status_code >= 400
        assert client.get(f'/business/sessions/{session}/selection', params={'agent_id': agent}).json()['selection'] is None
