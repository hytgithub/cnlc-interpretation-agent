"""服务共享资源的创建与依赖装配。"""

from dataclasses import dataclass
from pathlib import Path

from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import AsyncSQLAlchemyStorage
from redis.asyncio import ConnectionPool

from .adapters.mock.well import MockWell
from .repositories.business import BusinessStore
from .repositories.workflow import WorkflowStore
from .workflow.engine import MockWorkflow


@dataclass
class Runtime:
    root: Path
    well: MockWell
    business_store: BusinessStore
    workflow_store: WorkflowStore
    workflow: MockWorkflow
    storage: AsyncSQLAlchemyStorage
    pool: ConnectionPool
    bus: RedisMessageBus
    bus_mode: str
    include_test_tools: bool


def build_runtime(
    data_dir: Path | str, bus_mode: str, redis_url: str | None, include_test_tools: bool
) -> Runtime:
    root = Path(data_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    well = MockWell()
    business_store = BusinessStore(root / "business.sqlite3")
    workflow_store = WorkflowStore(business_store)
    workflow = MockWorkflow(workflow_store, well)
    storage = AsyncSQLAlchemyStorage(
        f"sqlite+aiosqlite:///{root / 'agentscope.sqlite3'}"
    )
    if bus_mode == "simulated":
        import fakeredis
        from fakeredis import FakeAsyncRedisConnection

        pool = ConnectionPool(
            connection_class=FakeAsyncRedisConnection,
            server=fakeredis.FakeServer(),
            decode_responses=True,
        )
    elif bus_mode == "redis":
        if not redis_url:
            raise ValueError("redis 模式需要 CNLC_REDIS_URL。")
        pool = ConnectionPool.from_url(redis_url, decode_responses=True)
    else:
        raise ValueError("CNLC_BUS_MODE 只支持 simulated 或 redis。")
    bus = RedisMessageBus(connection_pool=pool)
    return Runtime(
        root,
        well,
        business_store,
        workflow_store,
        workflow,
        storage,
        pool,
        bus,
        bus_mode,
        include_test_tools,
    )
