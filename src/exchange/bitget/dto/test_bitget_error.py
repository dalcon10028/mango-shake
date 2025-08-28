import pytest

from exchange.bitget.dto.bitget_error import BitgetErrorCode, BitgetError


@pytest.mark.parametrize(
    "error_resp, expected_code, expected_msg, expected_request_time, expected_data",
    [
        (
            {"code":"40762","msg":"The order amount exceeds the balance","requestTime":1756346471768,"data":None},
            BitgetErrorCode.INSUFFICIENT_BALANCE,
            "The order amount exceeds the balance",
            1756346471768,
            None,
        ),
    ]
)
def test_bitget_error_parsing(error_resp, expected_code, expected_msg, expected_request_time, expected_data):
    error = BitgetError(error_resp)
    assert error.code == expected_code
    assert error.msg == expected_msg
    assert error.request_time == expected_request_time
    assert error.data == expected_data
    assert str(error).find(str(expected_code.value)) != -1
    assert str(error).find(expected_msg) != -1