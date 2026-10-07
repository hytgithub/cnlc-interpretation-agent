"""绑定用户与会话的业务查询和耗时测试操作。"""

import asyncio
import math

from ..adapters.mock.well import MockWell
from ..repositories.business import BusinessStore
from .errors import BusinessError


class BusinessService:
    """业务操作入口，绑定当前用户和会话。

    MockWell 读取资料并计算统计值。BusinessStore 保存状态。
    本类把两者串联起来。调用方无需知道数据库或 JSON 的内部结构。
    """

    def __init__(self, store: BusinessStore, well: MockWell, owner: str, session: str):
        # 这些对象由服务端工厂传入，模型工具参数只包含曲线、层号和修订号。
        self.store, self.well, self.owner, self.session = store, well, owner, session

    def read_well(self):
        """读取井概要。此操作不依赖范围选择，也不创建运行记录。"""
        return {"status": "SUCCESS", "session_id": self.session, **self.well.summary()}

    def selection(self, revision):
        """所有范围工具共用的检查：选择修订号、资料版本和实际范围。"""
        selection = self.store.require_selection(self.owner, self.session, revision)
        # 选择没变化，也可能在重启后引用了旧资料，因此还要检查资料版本。
        if selection["dataset_revision"] != self.well.revision:
            raise BusinessError(
                "DATASET_VERSION_CONFLICT", "样本资料版本已变化。请重新选择资料。"
            )
        self.well.validate_range(
            selection["well_id"], selection["top_depth_m"], selection["bottom_depth_m"]
        )
        return selection

    def query(self, revision, layer_no=None):
        """先检查操作对象，再读取相交层段，最后附上来源与选择快照。"""
        selection = self.selection(revision)
        return {
            "status": "SUCCESS",
            "selection": selection,
            "is_mock": True,
            **self.well.query_intervals(selection, layer_no),
        }

    def statistics(self, revision, curve_name="GR"):
        """先检查操作对象，再计算统计值。普通统计直接返回，不创建耗时运行。"""
        selection = self.selection(revision)
        return {
            "status": "SUCCESS",
            "selection": selection,
            "is_mock": True,
            **self.well.statistics(selection, curve_name),
        }

    async def slow_statistics(
        self, revision, curve_name="GR", delay_seconds=10.5, fail=False
    ):
        """模拟耗时调用，验证框架后台通知和业务状态保存。

        delay_seconds 控制测试等待时间。fail 控制预设失败分支。
        这里没有调用公司服务，也没有执行新的专业解释算法。
        """
        # 第 1 步：限制测试延迟，避免误输入导致长时间等待。
        if not math.isfinite(delay_seconds) or not 0 <= delay_seconds <= 15:
            raise BusinessError("INVALID_DELAY", "测试延迟必须位于 0～15 秒。")
        selection = self.selection(revision)
        # 第 2 步：验证选择和曲线，并先算出统计值。
        # 本工具延迟的是已计算结果的返回，用于模拟耗时，不模拟算法耗时。
        result = self.well.statistics(selection, curve_name)
        # 第 3 步：等待前保存 RUNNING。客户端此时可以查询到真实业务状态。
        run = self.store.start_run(
            self.owner, self.session, "slow_mock_statistics", selection
        )
        try:
            # 第 4 步：异步等待。await 把执行权交回事件循环，服务仍可处理其他请求。
            # 等待超过原生 10 秒阈值时，AgentScope 会将调用转入后台。
            await asyncio.sleep(delay_seconds)
            if fail:
                # 第 5a 步：预设失败写入当前运行，保留其他运行的已有成功结果。
                return self.store.finish_run(
                    self.owner,
                    self.session,
                    run,
                    "FAILED",
                    error={"code": "MOCK_FAILURE", "message": "预设测试失败。"},
                )
            # 第 5b 步：成功后持久化结果，再返回给框架，由框架负责通知会话。
            return self.store.finish_run(
                self.owner, self.session, run, "SUCCEEDED", result=result
            )
        except asyncio.CancelledError:
            # 第 5c 步：本地协程被取消时记录 UNKNOWN，并继续抛出取消信号。
            # 本地取消不证明外部作业取消，因此没有使用“公司作业已取消”状态。
            self.store.finish_run(
                self.owner,
                self.session,
                run,
                "UNKNOWN",
                reason="本地测试协程已中断。该状态不证明外部公司作业已取消。",
            )
            raise
