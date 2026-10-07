"""业务拒绝及共用错误载荷。"""


class BusinessError(Exception):
    """可预期的业务拒绝，例如过期选择、越界范围或不存在的曲线。"""

    def __init__(self, code: str, message: str):
        # code 供程序判断错误类型。message 供用户理解拒绝原因。
        super().__init__(message)
        self.code = code

    def payload(self):
        """返回共用错误对象。HTTP 接口和 AgentScope 工具分别包装它。"""
        return {
            "status": "ERROR",
            "code": self.code,
            "message": str(self),
            "is_mock": True,
        }
