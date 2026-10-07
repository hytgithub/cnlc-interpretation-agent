"""会话选择、独立专业结果、耗时测试运行和工具清单持久化。"""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from ..adapters.mock.well import MockWell
from ..business.errors import BusinessError
from ..catalog import PROFESSIONAL_TOOLS
from ..business.tracing import call_trace
from ..contracts.selection import SelectionRequest
from ..timestamps import now


def _step_identifier_migration(db):
    """将历史数字步骤标识迁移为语义化标识，避免影响已有结果与参数。"""
    step_ids = tuple(dict.fromkeys(
        step for capability in PROFESSIONAL_TOOLS for step in capability.steps
    ))
    legacy_ids = {f"W{index:02d}": step for index, step in enumerate(step_ids, start=1)}

    def migrate_value(value):
        if isinstance(value, dict):
            return {
                legacy_ids.get(key, key): migrate_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [migrate_value(item) for item in value]
        if isinstance(value, str):
            for legacy_id, step_id in legacy_ids.items():
                value = value.replace(legacy_id, step_id)
        return value

    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for (table,) in tables:
        columns = {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}
        for column in ("step", "step_id"):
            if column in columns:
                for legacy_id, step_id in legacy_ids.items():
                    db.execute(
                        f'UPDATE "{table}" SET "{column}"=? WHERE "{column}"=?',
                        (step_id, legacy_id),
                    )
        if "payload" in columns:
            rows = db.execute(f'SELECT rowid, payload FROM "{table}"').fetchall()
            for rowid, payload in rows:
                try:
                    original = json.loads(payload)
                except (TypeError, json.JSONDecodeError):
                    continue
                updated = migrate_value(original)
                if updated != original:
                    db.execute(
                        f'UPDATE "{table}" SET payload=? WHERE rowid=?',
                        (json.dumps(updated, ensure_ascii=False), rowid),
                    )


class BusinessStore:
    """业务持久化。当前只支持本地单进程原型，不包含生产数据库迁移。

    selection 保存当前操作对象。tool_results 保存独立专业结果。
    runs 保存耗时测试运行。
    manifests 保存智能体实际可见的工具清单。
    owner 与 session 共同限定选择、运行和清单的读取范围。
    """

    def __init__(self, path: Path):
        # 保存数据库路径，并确保父目录存在。IF NOT EXISTS 允许复用已有数据库。
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            # selection/manifests：同一用户的同一会话只有一条当前记录。
            # runs：一次耗时调用对应一个 run_id，可以保留多次成功或失败。
            # payload 保存 JSON，方便原型迭代。生产环境的表结构需另行设计。
            db.executescript("""
                CREATE TABLE IF NOT EXISTS selection (
                    owner TEXT NOT NULL, session TEXT NOT NULL, revision INTEGER NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(owner, session));
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL,
                    status TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS manifests (
                    owner TEXT NOT NULL, session TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(owner,session));
                CREATE TABLE IF NOT EXISTS tool_results (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL,
                    payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS processing_parameters (
                    owner TEXT NOT NULL, session TEXT NOT NULL, scope TEXT NOT NULL,
                    step TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(owner, session, scope, step));
            """)
            _step_identifier_migration(db)

    def connect(self):
        """提供 with store.connect() as db 的事务使用方式。"""
        # SQLite 的 with db 正常退出时提交，异常退出时回滚，但不会关闭连接。
        # 外层 contextmanager 负责在最后关闭，避免每次查询留下连接。
        from contextlib import contextmanager

        @contextmanager
        def connection():
            # timeout=5 是等待数据库锁的最长秒数，不是工具执行超时。
            db = sqlite3.connect(self.path, timeout=5)
            try:
                with db:
                    yield db
            finally:
                db.close()

        return connection()

    def selection(self, owner, session):
        """按用户和会话读取当前选择。没有选择时返回 None。"""
        # SQL 的 ? 占位符把输入作为参数传递，不把用户标识拼接成 SQL 代码。
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM selection WHERE owner=? AND session=?",
                (owner, session),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def set_selection(self, owner, session, request: SelectionRequest, well: MockWell):
        """检查范围和旧修订号，然后原子更新当前选择。"""
        # 第 1 步：检查资料范围。非法请求不修改数据库。
        well.validate_range(
            request.well_id, request.top_depth_m, request.bottom_depth_m
        )
        with self.connect() as db:
            # 第 2 步：在读旧版本前取得写事务锁。
            # 这让“读取修订号 → 检查 → 写入”处于同一个事务中。
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT revision FROM selection WHERE owner=? AND session=?",
                (owner, session),
            ).fetchone()
            # 第 3 步：旧修订号必须与请求一致。
            # 例如页面 A/B 都读到 1，A 改成 2 后，B 再提交 1 会被拒绝。
            revision = row[0] if row else 0
            if revision != request.expected_revision:
                raise BusinessError(
                    "STALE_SELECTION", "选择修订号已过期。请读取当前选择。"
                )
            # 第 4 步：创建新选择快照。修订号递增，资料版本引用当前样本。
            payload = {
                "session_id": session,
                "well_id": well.well_id,
                "dataset_revision": well.revision,
                "revision": revision + 1,
                "top_depth_m": request.top_depth_m,
                "bottom_depth_m": request.bottom_depth_m,
                "depth_reference": "MD",
                "depth_unit": "m",
                "is_mock": True,
            }
            # 第 5 步：首次插入，已有记录则更新。事务成功后才返回新选择。
            db.execute(
                "INSERT INTO selection VALUES(?,?,?,?) ON CONFLICT(owner,session) "
                "DO UPDATE SET revision=excluded.revision,payload=excluded.payload",
                (owner, session, revision + 1, json.dumps(payload, ensure_ascii=False)),
            )
        return payload

    def require_selection(self, owner, session, expected_revision):
        """工具执行前读取选择，并拒绝缺少选择或旧修订号。"""
        # HTTP 提交时检查过一次，也必须在实际执行工具时再次检查。
        # 两个时间点之间，用户可能已经切换操作范围。
        selection = self.selection(owner, session)
        if selection is None:
            raise BusinessError("SELECTION_REQUIRED", "请先选择井和深度范围。")
        if selection["revision"] != expected_revision:
            raise BusinessError("STALE_SELECTION", "选择修订号已过期。工具未执行。")
        return selection

    def start_run(self, owner, session, tool, selection):
        """耗时工具开始前创建 RUNNING 记录，并保存当时的选择和调用关联。"""
        # run_id 是业务运行身份。它不同于原生框架的 tool_call_id/reply_id。
        # selection 存为快照。后续页面改选范围不能修改该运行的操作对象。
        payload = {
            "run_id": str(uuid4()),
            "session_id": session,
            "tool": tool,
            "selection": selection,
            "status": "RUNNING",
            "is_mock": True,
            "started_at": now(),
            "trace": dict(call_trace.get()),
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?)",
                (payload["run_id"], owner, session, "RUNNING", json.dumps(payload)),
            )
        return payload

    def finish_run(self, owner, session, payload, status, **result):
        """更新同一运行的状态，附加结果或错误，并保留原来的操作对象。"""
        # **result 接收 result=统计值、error=错误或 reason=说明等附加字段。
        # WHERE 同时检查运行、用户和会话，避免更新其他会话的记录。
        payload = {**payload, **result, "status": status, "finished_at": now()}
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status=?,payload=? WHERE id=? AND owner=? AND session=?",
                (
                    status,
                    json.dumps(payload, ensure_ascii=False),
                    payload["run_id"],
                    owner,
                    session,
                ),
            )
        return payload

    def runs(self, owner, session):
        """按创建顺序读取本会话的所有耗时运行，包含成功与失败记录。"""
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM runs WHERE owner=? AND session=? ORDER BY rowid",
                (owner, session),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_tool_result(self, owner, session, payload):
        """独立工具结果使用不可变引用，与整井流程运行及耗时测试分开保存。"""
        payload = {
            **payload, "result_id": str(uuid4()), "created_at": now(),
            "trace": dict(call_trace.get()),
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO tool_results VALUES(?,?,?,?)",
                (payload["result_id"], owner, session, json.dumps(payload, ensure_ascii=False)),
            )
        return payload

    def tool_result(self, owner, session, result_id):
        """引用解析同时检查用户和会话，不能引用其他会话的结果。"""
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM tool_results WHERE id=? AND owner=? AND session=?",
                (result_id, owner, session),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def tool_results(self, owner, session):
        """读取当前会话的不可变结果，用于计算参数修改的影响。"""
        with self.connect() as db:
            rows = db.execute('SELECT payload FROM tool_results WHERE owner=? AND session=? ORDER BY rowid', (owner, session)).fetchall()
        return [json.loads(row[0]) for row in rows]

    @staticmethod
    def _parameter_scope(context):
        return json.dumps(context, sort_keys=True, ensure_ascii=False)

    def processing_parameters(self, owner, session, context, step):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM processing_parameters WHERE owner=? AND session=? AND scope=? AND step=?',
                             (owner, session, self._parameter_scope(context), step)).fetchone()
        return json.loads(row[0]) if row else None

    def update_processing_parameters(self, owner, session, context, step, expected_revision, defaults, changes):
        """串行校验修订号，原子保存参数及变更前后值。"""
        scope = self._parameter_scope(context)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,payload FROM processing_parameters WHERE owner=? AND session=? AND scope=? AND step=?',
                             (owner, session, scope, step)).fetchone()
            revision = row[0] if row else 0
            if revision != expected_revision:
                raise BusinessError('PARAMETER_VERSION_CONFLICT', '参数版本已变化，请重新读取后修改或执行。')
            previous = json.loads(row[1])['parameters'] if row else defaults
            payload = dict(context=context, step_id=step, revision=revision + 1,
                           parameters={**previous, **changes}, previous_parameters=previous,
                           changes=changes, changed_at=now(), trace=dict(call_trace.get()))
            db.execute('INSERT INTO processing_parameters VALUES(?,?,?,?,?,?) ON CONFLICT(owner,session,scope,step) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',
                       (owner, session, scope, step, revision + 1, json.dumps(payload, ensure_ascii=False)))
        return payload

    def recover_unfinished(self):
        """服务启动时，把上次遗留的 RUNNING 记录标为 UNKNOWN。"""
        # SQLite 保留了运行记录，但 asyncio 任务不会随进程重启恢复。
        # 不能据此声称外部作业失败、成功或取消，也不能自动重试。
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,payload FROM runs WHERE status='RUNNING'"
            ).fetchall()
            for run_id, raw in rows:
                payload = {
                    **json.loads(raw),
                    "status": "UNKNOWN",
                    "finished_at": now(),
                    "reason": "服务重新启动。原型不能恢复内存中的作业，需要核实。",
                }
                db.execute(
                    "UPDATE runs SET status='UNKNOWN',payload=? WHERE id=?",
                    (json.dumps(payload, ensure_ascii=False), run_id),
                )
        return len(rows)

    def save_manifest(self, owner, session, names):
        """保存本轮实际装配的工具名称，用于验证默认工具是否已被过滤。"""
        payload = {
            "session_id": session,
            "tool_names": sorted(names),
            "assembled_at": now(),
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO manifests VALUES(?,?,?) ON CONFLICT(owner,session) "
                "DO UPDATE SET payload=excluded.payload",
                (owner, session, json.dumps(payload)),
            )

    def manifest(self, owner, session):
        """读取最近记录的工具清单。还没装配过智能体时返回 None。"""
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM manifests WHERE owner=? AND session=?",
                (owner, session),
            ).fetchone()
        return json.loads(row[0]) if row else None
