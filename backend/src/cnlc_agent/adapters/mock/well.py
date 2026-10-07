"""样本资料读取、范围校验和有界数据查询。"""

import hashlib
import json
import math
from importlib.resources import files
from statistics import fmean

from ...business.errors import BusinessError


class MockWell:
    """只读样本资料对象。层段来自 JSON，曲线统计由本类实际计算。"""

    def __init__(self):
        # 第 1 步：从 Python 包内读取 JSON。安装后也可以定位该文件。
        raw = files("cnlc_agent").joinpath("data/WELL_MOCK_PLOT_001.json").read_bytes()
        self.data = json.loads(raw)
        # 第 2 步：用文件字节的 SHA-256 摘要生成资料标识。
        # 它用于检查选择所引用的样本是否变化，不是专业成果的版本管理。
        self.revision = "mock-" + hashlib.sha256(raw).hexdigest()[:12]
        self.well_id = self.data["well"]["well_id"]

    @property
    def depths(self):
        """取出采样深度数组。它与每条原始曲线的 values 一一对应。"""
        return self.data["raw_data"]["depths"]

    def validate_range(self, well_id, top, bottom):
        """检查井和范围。任何失败都直接拒绝，保留调用方提交的原始范围。"""
        # 第 1 步：该原型只有一口井，不能把其他井号默认替换成样本井。
        if well_id != self.well_id:
            raise BusinessError("WELL_NOT_FOUND", "样本井不存在。")
        # 第 2 步：排除 NaN/无穷值，并要求顶深小于底深。
        if not all(math.isfinite(v) for v in [top, bottom]) or top >= bottom:
            raise BusinessError(
                "INVALID_RANGE", "顶深必须小于底深。深度必须是有限数值。"
            )
        # 第 3 步：整个选择必须落在资料范围内，不能静默截断越界部分。
        if top < self.depths[0] or bottom > self.depths[-1]:
            raise BusinessError("OUT_OF_RANGE", "层段范围必须位于 2000～2120 m。")

    def summary(self):
        """返回井和资料概要。模型不需要收到全部 1201 点的曲线数组。"""
        curves = self.data["raw_data"]["curves"]
        result_curve_count = 0
        for output in self.data.get("outputs", {}).values():
            result = output.get("result") if isinstance(output, dict) else None
            curve_data = result.get("curve_data") if isinstance(result, dict) else None
            if isinstance(curve_data, dict):
                result_curve_count += len(curve_data.get("curves", {}))
        try:
            interval_count = len(self.intervals)
        except BusinessError:
            interval_count = None  # 派生层段不可用不影响原始井资料查询。
        # 范围、曲线数、层段数和空值数从样本读取或计算。
        # MD、m、0.1 m 是当前样本的约定。未来导入其他资料时需读取并检查这些元数据。
        # outputs 中只有部分结果含 curve_data.curves，缺少时按空字典处理。
        return {
            "well_id": self.well_id,
            "dataset_revision": self.revision,
            "depth_reference": "MD",
            "depth_unit": "m",
            "top_depth_m": self.depths[0],
            "bottom_depth_m": self.depths[-1],
            "sample_count": len(self.depths),
            "sample_step_m": 0.1,
            "raw_curve_names": list(curves),
            "result_curve_count": result_curve_count,
            "interval_count": interval_count,
            "null_counts": {
                k: sum(v is None for v in c["values"]) for k, c in curves.items()
            },
            "is_mock": True,
            "source": "WELL_MOCK_PLOT_001.json",
        }

    @property
    def intervals(self):
        """读取样本中预先给出的层段表，不调用专业分层算法。"""
        output = self.data.get("outputs", {}).get("intervals")
        result = output.get("result") if isinstance(output, dict) else None
        intervals = result.get("intervals") if isinstance(result, dict) else None
        if not isinstance(intervals, list):
            raise BusinessError("INTERVALS_UNAVAILABLE", "层段结果不可用。")
        return intervals

    def query_intervals(self, selection, layer_no=None):
        """查询与选择范围相交的预设层段。layer_no 可限定某个层号。"""
        # 第 1 步：可选地按层号过滤。指定层号不存在时，明确报错。
        selected = self.intervals
        if layer_no is not None:
            selected = [x for x in selected if x["layer_no"] == layer_no]
            if not selected:
                raise BusinessError("INTERVAL_NOT_FOUND", "样本层段不存在。")
        # 第 2 步：判断层段是否与选择范围有正厚度的交集。
        # 条件是“层底 > 选择顶深”且“层顶 < 选择底深”。仅边界接触不算相交。
        # 返回完整层段对象，不用用户选择范围改写专业层界或有效厚度。
        selected = [
            x
            for x in selected
            if x["bottom_depth_m"] > selection["top_depth_m"]
            and x["top_depth_m"] < selection["bottom_depth_m"]
        ]
        # 层号存在但不在选择范围内，与“层号不存在”使用不同错误码。
        if layer_no is not None and not selected:
            raise BusinessError(
                "INTERVAL_OUTSIDE_SELECTION", "层段不在当前选择范围内。"
            )
        return {
            "intervals": selected,
            "basis": "预设 Mock 层段，与选择范围相交，不裁剪专业层界。",
        }

    def statistics(self, selection, curve_name):
        """计算选定范围内一条原始曲线的点数、空值数、最值和均值。"""
        # 第 1 步：只从 raw_data.curves 取原始曲线。未找到曲线就拒绝。
        curve = self.data["raw_data"]["curves"].get(curve_name)
        if curve is None:
            raise BusinessError("CURVE_NOT_FOUND", "原始曲线不存在。")
        # 第 2 步：把深度与曲线值配对，再保留范围内的采样点。
        # strict=True 要求两个数组长度一致，避免缺失尾部样本却仍返回统计。
        # <= 表示包含顶深和底深，与上面的层段相交判断用途不同。
        samples = [
            v
            for d, v in zip(self.depths, curve["values"], strict=True)
            if selection["top_depth_m"] <= d <= selection["bottom_depth_m"]
        ]
        # 第 3 步：剔除 None 空值。0 是有效数值，不能当作空值剔除。
        values = [v for v in samples if v is not None]
        # 第 4 步：计算并返回统计值。全部为空时，最值和均值均返回 None。
        # fmean 是数值算术平均值。这一步由 Python 计算，模型不生成专业数值。
        return {
            "curve_name": curve_name,
            "unit": curve["unit"],
            "sample_count": len(samples),
            "valid_count": len(values),
            "null_count": len(samples) - len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": fmean(values) if values else None,
            "boundary_rule": "顶深和底深均包含，空值不参与统计。",
        }

    def curves(self, top, bottom, curve_name=None):
        """返回范围内原始曲线点，保留双端和空值。"""
        self.validate_range(self.well_id, top, bottom)
        all_curves = self.data["raw_data"]["curves"]
        names = [curve_name] if curve_name else list(all_curves)
        missing = [name for name in names if name not in all_curves]
        if missing:
            raise BusinessError(
                "CURVE_NOT_FOUND", "原始曲线不存在：" + ", ".join(missing)
            )
        sample_indices = [
            (index, depth)
            for (index, depth) in enumerate(self.depths)
            if top <= depth <= bottom
        ]
        return {
            "well_id": self.well_id,
            "dataset_revision": self.revision,
            "top_depth_m": top,
            "bottom_depth_m": bottom,
            "depth_reference": "MD",
            "depth_unit": "m",
            "is_mock": True,
            "curves": {
                name: {
                    "unit": all_curves[name]["unit"],
                    "points": [
                        {"depth_m": depth, "value": all_curves[name]["values"][index]}
                        for (index, depth) in sample_indices
                    ],
                }
                for name in names
            },
        }
