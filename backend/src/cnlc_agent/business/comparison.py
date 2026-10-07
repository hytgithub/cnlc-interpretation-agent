"""比较结果内容并排除运行及时间元数据。"""


def compare_results(left, right):
    changes = []

    def walk(a, b, path="$"):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                if key in {"created_at", "result_revision_id", "run_id"}:
                    continue
                if key not in a or key not in b:
                    changes.append(
                        {
                            "path": f"{path}.{key}",
                            "left": a.get(key),
                            "right": b.get(key),
                        }
                    )
                else:
                    walk(a[key], b[key], f"{path}.{key}")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                changes.append(
                    {"path": f"{path}.length", "left": len(a), "right": len(b)}
                )
            for index, (item_a, item_b) in enumerate(zip(a, b)):
                walk(item_a, item_b, f"{path}[{index}]")
        elif a != b:
            changes.append({"path": path, "left": a, "right": b})

    walk(left, right)
    return {
        "left_result_revision_id": left["result_revision_id"],
        "right_result_revision_id": right["result_revision_id"],
        "change_count": len(changes),
        "changes": changes,
        "source": "MOCK",
        "is_mock": True,
    }
