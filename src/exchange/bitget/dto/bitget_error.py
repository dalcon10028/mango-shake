from dataclasses import dataclass
import enum

@dataclass
class BitgetError(Exception):
    def __init__(self, error_resp: dict):
        self.code = BitgetErrorCode(error_resp.get("code"))
        self.msg = error_resp.get("msg")
        self.request_time = error_resp.get("requestTime")
        self.data = error_resp.get("data")
        super().__init__(f"Bitget API Error {self.code.name}({self.code.value}): {self.msg}")


class BitgetErrorCode(enum.Enum):
    INSUFFICIENT_BALANCE = "40762" # The order amount exceeds the balance
