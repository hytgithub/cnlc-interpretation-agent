"""环境配置、命令行参数及服务启动。"""

import argparse
import os
from pathlib import Path


def main():
    """命令行入口：解析配置，然后让 Uvicorn 运行应用。"""
    import uvicorn
    from dotenv import load_dotenv

    from .app import build_app

    # 从项目根目录读取本地配置；shell 中已设置的变量优先。
    load_dotenv(Path.cwd() / ".env", override=False)
    # 第 1 步：读取命令行参数。--data-dir 优先于环境变量的默认值。
    parser = argparse.ArgumentParser(description="启动本地 AgentScope 测井原型。")
    parser.add_argument("--data-dir", default=os.environ.get("CNLC_DATA_DIR", "var"))
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--enable-test-tools",
        action="store_true",
        default=os.getenv("CNLC_ENABLE_TEST_TOOLS", "0").lower()
        in {"1", "true", "yes"},
        help="把耗时后台通知测试工具加入 Agent 工具清单。",
    )
    args = parser.parse_args()
    # 第 2 步：构造应用。此时还没有向模型发送消息。
    app = build_app(
        args.data_dir,
        os.environ.get("CNLC_BUS_MODE", "simulated"),
        os.environ.get("CNLC_REDIS_URL"),
        args.enable_test_tools,
    )
    # 第 3 步：启动 HTTP 服务。Uvicorn 会进入上面定义的 lifespan。
    # 原型监听回环地址，供本机演示脚本和测试使用。
    uvicorn.run(app, host="127.0.0.1", port=args.port)
