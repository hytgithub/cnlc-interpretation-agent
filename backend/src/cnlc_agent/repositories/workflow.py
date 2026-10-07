"""Workflow 运行、步骤、结果及报告持久化。"""

import json
from uuid import uuid4

from ..timestamps import utc_now
from ..workflow.projections import run_summary
from ..workflow.stages import summarize_stages
from .business import BusinessStore


class WorkflowStore:
    """将 Workflow、步骤、Provider 投影、结果和报告保存在原型业务 SQLite 中。"""

    def __init__(self, business_store: BusinessStore):
        self.business_store = business_store
        with business_store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL,
                    status TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_workflow_runs_owner_session
                    ON workflow_runs(owner, session);
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    run_id TEXT NOT NULL, step_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                    status TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(run_id, step_id));
                CREATE TABLE IF NOT EXISTS provider_calls (
                    provider_call_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    provider TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS result_revisions (
                    result_revision_id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL,
                    run_id TEXT NOT NULL, sequence INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_results_owner_session
                    ON result_revisions(owner, session, sequence);
                CREATE TABLE IF NOT EXISTS report_revisions (
                    report_revision_id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL,
                    run_id TEXT NOT NULL, result_revision_id TEXT, report_type TEXT NOT NULL,
                    payload TEXT NOT NULL);
            """)

    @property
    def db(self):
        """复用业务存储的连接工厂，不暴露 SQLite 给路由或 Agent。"""
        return self.business_store.connect()

    def insert_run(self, run: dict) -> None:
        """保存新运行。独立函数便于创建与后续步骤更新分开提交。"""
        with self.db as db:
            db.execute(
                "INSERT INTO workflow_runs VALUES(?,?,?,?,?)",
                (
                    run["run_id"],
                    run["owner"],
                    run["session_id"],
                    run["status"],
                    json.dumps(run, ensure_ascii=False),
                ),
            )

    def update_run(self, run: dict) -> None:
        """只更新归属一致的运行快照。"""
        with self.db as db:
            db.execute(
                "UPDATE workflow_runs SET status=?,payload=? WHERE run_id=? AND owner=? AND session=?",
                (
                    run["status"],
                    json.dumps(run, ensure_ascii=False),
                    run["run_id"],
                    run["owner"],
                    run["session_id"],
                ),
            )

    def save_step(self, run_id: str, sequence: int, step: dict) -> None:
        """保存一步的真实执行状态、工具映射和输出摘要。"""
        with self.db as db:
            db.execute(
                "INSERT INTO workflow_steps VALUES(?,?,?,?,?) ON CONFLICT(run_id,step_id) DO UPDATE SET "
                "sequence=excluded.sequence,status=excluded.status,payload=excluded.payload",
                (
                    run_id,
                    step["step_id"],
                    sequence,
                    step["status"],
                    json.dumps(step, ensure_ascii=False),
                ),
            )

    def save_provider_call(self, run_id: str, provider_call: dict) -> None:
        """保存一次 Mock Fixture 投影批次；不冒充真实 Provider 请求。"""
        with self.db as db:
            db.execute(
                "INSERT OR IGNORE INTO provider_calls VALUES(?,?,?,?,?)",
                (
                    provider_call["provider_call_id"],
                    run_id,
                    provider_call["provider"],
                    provider_call["status"],
                    json.dumps(provider_call, ensure_ascii=False),
                ),
            )

    def get_run(self, owner: str, session: str, run_id: str) -> dict | None:
        """按用户和会话读取运行，并附上顺序化步骤及 Mock 批次记录。"""
        with self.db as db:
            row = db.execute(
                "SELECT payload FROM workflow_runs WHERE run_id=? AND owner=? AND session=?",
                (run_id, owner, session),
            ).fetchone()
            if row is None:
                return None
            run = json.loads(row[0])
            steps = db.execute(
                "SELECT payload FROM workflow_steps WHERE run_id=? ORDER BY sequence",
                (run_id,),
            ).fetchall()
            providers = db.execute(
                "SELECT payload FROM provider_calls WHERE run_id=? ORDER BY rowid",
                (run_id,),
            ).fetchall()
        run["steps"] = [json.loads(item[0]) for item in steps]
        run["provider_calls"] = [json.loads(item[0]) for item in providers]
        run["stages"] = self.stage_summary(run["steps"])
        if run.get("result_revision_id"):
            run["result_revision"] = self.get_result(
                owner, session, run["result_revision_id"]
            )
        if run.get("report_revision_id"):
            run["report"] = self.get_report(owner, session, run["report_revision_id"])
        report_stage = next(
            (item for item in run["stages"] if item["stage_id"] == "REPORT"), None
        )
        if report_stage is not None:
            report_stage.update(
                status="SUCCESS" if run.get("report") else "PENDING",
                total_steps=1,
                completed_steps=1 if run.get("report") else 0,
            )
        return run

    stage_summary = staticmethod(summarize_stages)

    def list_runs(self, owner: str, session: str) -> list[dict]:
        """列出会话运行概要，完整步骤由 get_run 获取。"""
        with self.db as db:
            rows = db.execute(
                "SELECT payload FROM workflow_runs WHERE owner=? AND session=? ORDER BY rowid DESC",
                (owner, session),
            ).fetchall()
        return [self.run_summary(json.loads(row[0])) for row in rows]

    run_summary = staticmethod(run_summary)

    def save_result(self, owner: str, session: str, run_id: str, result: dict) -> dict:
        """为成功或告警终态创建新的 Mock 结果版本，不覆盖历史版本。"""
        with self.db as db:
            sequence = db.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM result_revisions WHERE owner=? AND session=?",
                (owner, session),
            ).fetchone()[0]
            payload = {
                "result_revision_id": str(uuid4()),
                "run_id": run_id,
                "sequence": sequence,
                "source": "MOCK",
                "is_mock": True,
                "created_at": utc_now(),
                **result,
            }
            db.execute(
                "INSERT INTO result_revisions VALUES(?,?,?,?,?,?)",
                (
                    payload["result_revision_id"],
                    owner,
                    session,
                    run_id,
                    sequence,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
        return payload

    def get_result(self, owner: str, session: str, result_id: str) -> dict | None:
        """按归属读取一个结果版本。"""
        with self.db as db:
            row = db.execute(
                "SELECT payload FROM result_revisions WHERE result_revision_id=? AND owner=? AND session=?",
                (result_id, owner, session),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_results(self, owner: str, session: str) -> list[dict]:
        """按版本号返回本会话的演示结果。"""
        with self.db as db:
            rows = db.execute(
                "SELECT payload FROM result_revisions WHERE owner=? AND session=? ORDER BY sequence DESC",
                (owner, session),
            ).fetchall()
        fields = (
            "result_revision_id",
            "run_id",
            "sequence",
            "well_id",
            "dataset_revision",
            "scenario_id",
            "status",
            "source",
            "is_mock",
            "created_at",
            "source_note",
        )
        return [
            {key: result[key] for key in fields if key in result}
            for result in (json.loads(row[0]) for row in rows)
        ]

    def save_report(
        self,
        owner: str,
        session: str,
        run_id: str,
        report_type: str,
        content: str,
        result_revision_id: str | None,
    ) -> dict:
        """保存绑定结果版本的 Markdown 报告。"""
        report = {
            "report_revision_id": str(uuid4()),
            "run_id": run_id,
            "result_revision_id": result_revision_id,
            "report_type": report_type,
            "content": content,
            "source": "MOCK",
            "is_mock": True,
            "created_at": utc_now(),
        }
        with self.db as db:
            db.execute(
                "INSERT INTO report_revisions VALUES(?,?,?,?,?,?,?)",
                (
                    report["report_revision_id"],
                    owner,
                    session,
                    run_id,
                    result_revision_id,
                    report_type,
                    json.dumps(report, ensure_ascii=False),
                ),
            )
        return report

    def get_report(self, owner: str, session: str, report_id: str) -> dict | None:
        """按会话归属读取报告。"""
        with self.db as db:
            row = db.execute(
                "SELECT payload FROM report_revisions WHERE report_revision_id=? AND owner=? AND session=?",
                (report_id, owner, session),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_steps(self, run_id: str) -> list[dict]:
        """按执行顺序读取已持久化的步骤快照。"""
        with self.db as db:
            rows = db.execute(
                "SELECT payload FROM workflow_steps WHERE run_id=? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
