"""使用真实 HTTP 连接验证原生 SSE 和后台卸载。"""

import json
import os
import platform
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from test_service import ALLOWED_TOOLS, bootstrap, messages, select, send


@contextmanager
def server(tmp_path):
    """启动独立服务进程，向测试提供真实 HTTP 客户端，结束后关闭进程。"""
    # 第 1 步：让系统分配一个当前可用的临时端口，随后交给测试服务使用。
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    # 第 2 步：使用临时日志和数据目录，不占用开发者的正常服务目录。
    log_path = tmp_path / "service.log"
    env = {**os.environ, "CNLC_BUS_MODE": "simulated"}
    with log_path.open("w") as log:
        # 第 3 步：使用当前虚拟环境 Python 启动服务，连接回环地址。
        process = subprocess.Popen([sys.executable, "-m", "cnlc_agent.app", "--data-dir", str(tmp_path / "data"),
                                    "--port", str(port), "--enable-test-tools"], stdout=log, stderr=log, env=env)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"X-User-ID": "prototype-owner"},
                              timeout=httpx.Timeout(20, connect=2)) as client:
                # 第 4 步：等待服务启动，最多 10 秒。失败时显示临时服务日志。
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        raise AssertionError(log_path.read_text())
                    try:
                        if client.get("/business/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert time.monotonic() < deadline, log_path.read_text()
                    time.sleep(.05)
                # 第 5 步：进入真正的测试主体，复用该 HTTP 客户端。
                yield client
        finally:
            # 第 6 步：无论断言成功或失败都关闭服务，避免测试留下后台进程。
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def next_reply(lines, previous_reply_ids=()):
    """从 SSE 逐行读取事件，直到当前一轮回复的 REPLY_END。"""
    events = []
    for line in lines:
        if not line.startswith("data: "):
            continue
        event = json.loads(line[6:])
        if event.get("reply_id") in previous_reply_ids:
            continue
        events.append(event)
        # 此函数只判断框架回复完成。业务运行可能仍处于 RUNNING。
        if event["type"] == "REPLY_END":
            assert event["finished_reason"] == "completed", event
            return events
    raise AssertionError("SSE 连接提前结束。")


def test_native_http_offload_pending_completion_reconnect_and_context_binding(tmp_path):
    """验证等待、后台完成、保留旧范围，以及重连后的独立查询。"""
    with server(tmp_path) as client:
        # 第 1 步：建立原生会话，保存全井范围，选择修订号变为 1。
        agent, session, _ = bootstrap(client)
        select(client, agent, session)
        params = {"agent_id": agent}
        stream_url = f"/sessions/{session}/stream"
        runs_url = f"/business/sessions/{session}/runs"
        with client.stream("GET", stream_url, params=params) as response:
            # 第 2 步：打开真实 SSE 连接，再提交 12 秒耗时工具。
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            lines = response.iter_lines()
            send(client, agent, session, "slow_mock_statistics", {
                "expected_selection_revision": 1, "delay_seconds": 12})
            # 第 3 步：约 10 秒时收到第一次回复，必须是 PENDING。
            # 业务查询此时为 RUNNING，且工具、回复和会话关联一致。
            pending_events = next_reply(lines)
            pending_text = "".join(x.get("delta", "") for x in pending_events if x["type"] == "TEXT_BLOCK_DELTA")
            assert json.loads(pending_text)["status"] == "PENDING"
            assert any(x["type"] == "TOOL_RESULT_END" for x in pending_events)
            run = client.get(runs_url, params=params).json()["runs"][0]
            assert run["status"] == "RUNNING"
            assert run["trace"]["tool_call_id"] == json.loads(pending_text)["tool_call_id"]
            assert run["trace"]["reply_id"] == pending_events[-1]["reply_id"]
            assert run["trace"]["session_id"] == session
            # 第 4 步：把当前范围改为修订号 2，不能改绑已提交运行。
            assert select(client, agent, session, revision=1, top=2100, bottom=2120).status_code == 200
            # 第 5 步：前台回复已结束时发出中断，检查后台运行仍在执行。
            # 本步骤不证明中断活跃回复或取消公司作业的所有行为。
            interrupted = client.post(f"/sessions/{session}/interrupt", params=params)
            assert interrupted.status_code == 202
            assert client.get(runs_url, params=params).json()["runs"][0]["status"] == "RUNNING"
            # 第 6 步：工具完成后，框架用 HINT_BLOCK 通知并自动唤醒会话。
            # 第二次回复为 SUCCEEDED，仍引用修订号 1 和原始 1201 点。
            completion_events = next_reply(lines)
            assert any(x["type"] == "HINT_BLOCK" for x in completion_events)
            final_text = "".join(x.get("delta", "") for x in completion_events if x["type"] == "TEXT_BLOCK_DELTA")
            result = json.loads(final_text)
            assert result["status"] == "SUCCEEDED"
            assert result["run_id"] == run["run_id"]
            assert result["selection"]["revision"] == 1
            assert result["result"]["sample_count"] == 1201
        # 第 7 步：框架在回复持久化后清理回放日志。重连可能看见尚未清理的
        # 旧事件，按已读 reply_id 过滤，再接收新请求；不依赖旧日志是否仍存在。
        with client.stream("GET", stream_url, params=params) as response:
            send(client, agent, session, "get_well_data")
            reconnect_events = next_reply(response.iter_lines(), {x["reply_id"] for x in pending_events + completion_events})
        prior_ids = {x["id"] for x in pending_events + completion_events}
        assert reconnect_events
        assert all(x["id"] not in prior_ids for x in reconnect_events)
        text = "".join(x.get("delta", "") for x in reconnect_events if x["type"] == "TEXT_BLOCK_DELTA")
        assert json.loads(text)["status"] == "SUCCESS"
        # 第 8 步：从业务接口核对运行数量、当前选择和实际工具清单。
        runs = client.get(runs_url, params=params).json()["runs"]
        assert len(runs) == 1 and runs[0]["status"] == "SUCCEEDED"
        selection = client.get(f"/business/sessions/{session}/selection", params=params).json()["selection"]
        assert selection["revision"] == 2
        manifest = client.get(f"/business/sessions/{session}/tools", params=params).json()["manifest"]
        assert set(manifest["tool_names"]) == ALLOWED_TOOLS
        assert messages(client, agent, session)["messages"][-1]["finished_reason"] == "completed"
        # 第 9 步：执行 README 对应的演示客户端，确认三个普通查询可用。
        demo = subprocess.run([sys.executable, "scripts/demo.py", "--url", str(client.base_url)],
                              capture_output=True, text=True, timeout=10, check=True)
        demo_outputs = [json.loads(line) for line in demo.stdout.splitlines()]
        demo_queries = [x for x in demo_outputs if "tool" in x]
        assert [x["tool"] for x in demo_queries] == ["get_well_data", "get_well_data", "query_interval_results"]
        assert all(x["result"]["status"] == "SUCCESS" for x in demo_queries)
        # 第 10 步：只有本用例上述断言全部通过后，才按需写入实际事件证据。
        # 整个测试套件是否通过，仍以 pytest 的最终结果为准。
        evidence_path = os.environ.get("CNLC_EVIDENCE_PATH")
        if evidence_path:
            path = Path(evidence_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "test": "test_native_http_offload_pending_completion_reconnect_and_context_binding",
                "python": platform.python_version(), "health": client.get("/business/health").json(),
                "agent_id": agent, "session_id": session, "native_offload_timeout_seconds": 10,
                "mock_tool_delay_seconds": 12, "pending_events": pending_events,
                "completion_events": completion_events, "reconnected_event_ids": [x["id"] for x in reconnect_events],
                "runs": runs, "current_selection": selection, "final_tool_manifest": manifest,
                "assertions": "所有测试断言通过后才写入该记录。",
            }, ensure_ascii=False, indent=2) + "\n")
