"""原型客户端：模拟未来工作台如何通过 HTTP 使用智能体服务。

先启动 cnlc-prototype，再运行本脚本。
默认演示井概要、原始曲线和层段三个独立查询，--slow 增加一个 12 秒测试工具。
本脚本只提交请求和读取事件，不直接访问样本 JSON 或业务数据库。
"""

import argparse
import json

import httpx
from agentscope.message import UserMsg


def main():
    # 第 1 步：取得服务地址，以及是否演示后台工具的开关。
    parser = argparse.ArgumentParser(description="调用本地测井框架验证原型。")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--slow", action="store_true", help="增加 12 秒耗时工具，观察两次回复。")
    args = parser.parse_args()
    # 创建一个可复用的 HTTP 客户端。
    # X-User-ID 是本地测试身份。timeout=20 允许等待 12 秒工具的下一条事件。
    with httpx.Client(base_url=args.url, headers={"X-User-ID": "prototype-user"}, timeout=20) as client:
        def post(path, body):
            # 统一处理 POST：发送 JSON，拒绝失败响应，再解析响应对象。
            response = client.post(path, json=body)
            response.raise_for_status()
            return response.json()

        # 第 2 步：通过三个原生接口建立运行配置。
        # credential_id：模型配置记录。此处是无需密钥的脚本模型类型。
        # agent_id：智能体定义，包含名称和系统提示。
        # session_id：本次演示的会话，包含模型选择和独立聊天历史。
        # 每次运行脚本都新建演示记录，便于隔离不同演示。
        credential = post("/credential/", {"data": {"type": "scripted_mock"}})["credential_id"]
        agent = post("/agent/", {"name": "测井助手", "system_prompt": "依据实际工具结果回答。"})["agent_id"]
        session = post("/sessions/", {"agent_id": agent, "name": "框架验证演示", "chat_model_config": {
            "type": "scripted_mock", "credential_id": credential, "model": "scripted", "parameters": {}}})["session_id"]
        # 后续会话查询需要 agent_id，以便服务检查完整会话归属。
        params = {"agent_id": agent}
        # 第 3 步：取得实际井与资料版本。专业工具直接接收范围参数。
        response = client.get("/business/well")
        response.raise_for_status()
        well = response.json()
        scope = {"well_id": well["well_id"], "dataset_revision": well["dataset_revision"],
                 "top_depth_m": 2000, "bottom_depth_m": 2001}
        print(json.dumps({"agent_id": agent, "session_id": session, "context": scope}, ensure_ascii=False))

        # 第 4 步：准备明确的 JSON 测试指令。
        # 井概要无需范围参数；数据与层段查询使用显式井段。
        commands = [("get_well_data", {}), ("get_well_data", {**scope, "curve_names": ["GR"]}),
                    ("query_interval_results", scope)]
        if args.slow:
            # 测试工具保留原来的选择快照机制，仅 --slow 使用该测试路径。
            response = client.put(f"/business/sessions/{session}/selection", params=params,
                                  json={"top_depth_m": 2000, "bottom_depth_m": 2120, "expected_revision": 0})
            response.raise_for_status()
            # 原生后台卸载阈值为 10 秒。12 秒延迟可以观察等待和完成两次回复。
            commands.append(("slow_mock_statistics", {"expected_selection_revision": 1, "delay_seconds": 12}))
        for tool, arguments in commands:
            # 第 5 步：开始每个请求前，先记录已有回复 ID。
            # 原生 SSE 重连会重放旧事件，因此需要排除已存在的回复。
            history = client.get(f"/sessions/{session}/messages", params=params)
            history.raise_for_status()
            previous_replies = {x["id"] for x in history.json()["messages"] if x["role"] == "assistant"}
            # 第 6 步：先订阅 SSE，再提交聊天，避免错过新请求的即时事件。
            # SSE 是持续的 HTTP 事件流，服务可在同一连接上发送多次回复。
            with client.stream("GET", f"/sessions/{session}/stream", params=params) as stream:
                stream.raise_for_status()
                # UserMsg 是原生用户消息。model_dump 将其转换成 HTTP 可传输的字典。
                msg = UserMsg(name="prototype-user", content=json.dumps({"tool": tool, "arguments": arguments})).model_dump(mode="json")
                # 第 7 步：POST /chat 仅启动执行，返回 started。
                # 真正的调用、等待和完成信息从上面建立的 SSE 连接返回。
                post("/chat/", {"agent_id": agent, "session_id": session, "input": msg})
                reply_text = ""
                # 第 8 步：按回复 ID 筛选新回复，拼接原生文本增量。
                # reply_text 只拼接最终回复文字，不拼接工具输出事件。
                active_reply = None
                current = False
                for line in stream.iter_lines():
                    # SSE 的 data: 行承载 JSON 事件。空行和心跳行直接跳过。
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event["type"] == "REPLY_START":
                        # 新一轮回复开始，清空文本。旧回复重放则 current=False。
                        active_reply = event["reply_id"]
                        current = active_reply not in previous_replies
                        reply_text = ""
                    elif event["type"] == "TEXT_BLOCK_DELTA" and current:
                        # delta 是当前这一小段文本，需要拼接成完整 JSON 回复。
                        reply_text += event["delta"]
                    elif event["type"] == "REPLY_END" and current:
                        # 框架一轮回复结束，不一定代表后台业务运行已结束。
                        if event["finished_reason"] != "completed":
                            raise RuntimeError(event)
                        result = json.loads(reply_text) if reply_text else {}
                        print(json.dumps({"tool": tool, "reply_id": active_reply, "result": result}, ensure_ascii=False))
                        # 第 9 步：普通查询得到结果即可结束本次读取。
                        # PENDING 表示工具仍在后台，继续读取后续自动唤醒的回复。
                        if result.get("status") != "PENDING":
                            break
        # 第 10 步：单独查询持久化运行记录。
        # 独立专业工具保存结果引用，不创建整井流程或耗时测试运行。
        response = client.get(f"/business/sessions/{session}/runs", params=params)
        response.raise_for_status()
        print(json.dumps(response.json(), ensure_ascii=False))


if __name__ == "__main__":
    main()
