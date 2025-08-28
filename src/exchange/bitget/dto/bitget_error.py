from dataclasses import dataclass
import logging
import enum

logger = logging.getLogger(__name__)

@dataclass
class BitgetError(Exception):
    def __init__(self, error_resp: dict):
        code = error_resp.get("code", "00000")
        try:
            self.code = BitgetErrorCode(code)
        except ValueError:
            # 알 수 없는 코드는 UNKNOWN_ERROR로 매핑
            self.code = BitgetErrorCode.UNKNOWN_ERROR
            logging.warning(f"Unknown error code {code}, response: {error_resp}")
        self.original_code = code  # 원래 응답 코드 저장
        self.msg = error_resp.get("msg")
        self.request_time = error_resp.get("requestTime")
        self.data = error_resp.get("data")
        super().__init__(f"Bitget API Error {self.code.name}({self.code.value}): {self.msg}")

class BitgetErrorCode(enum.Enum):
    INSUFFICIENT_BALANCE = "40762" # The order amount exceeds the balance
    UNKNOWN_ERROR = "00000" # Unknown error
    NO_ORDER_TO_CANCEL = "22001"

    @classmethod
    def _missing_(cls, value):
        # enum에 정의되지 않은 코드 값이 들어오면 UNKNOWN_ERROR로 fallback
        return cls.UNKNOWN_ERROR

    def ignorable(self) -> bool:
        # 무시해도 되는 에러인지 여부 반환
        return self in {
            BitgetErrorCode.NO_ORDER_TO_CANCEL,
        }

# ValueError("'22001' is not a valid BitgetErrorCode")