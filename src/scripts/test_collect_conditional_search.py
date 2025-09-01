from decimal import Decimal
import pytest

# 테스트 대상 모듈
import scripts.collect_conditional_search as m


# --------- 샘플 응답 (질문에 제공한 그대로) ---------
CNSRLST_MSG = {
    'trnm': 'CNSRLST',
    'return_code': 0,
    'return_msg': '',
    'data': [
        ['0','조건1'],
        ['1','조건2'],
        ['2','조건3'],
        ['3','조건4'],
        ['4','조건5']
    ]
}

CNSRREQ_MSG = {
    'trnm': 'CNSRREQ',
    'seq': '2  ',
    'cont_yn': 'N',
    'next_key': '',
    'return_code': 0,
    'data': [
        {
            '9001': 'A005930',
            '302': '삼성전자',
            '10': '000021850',
            '25': '3',
            '11': '000000000',
            '12': '000000000',
            '13': '000000000',
            '16': '000000000',
            '17': '000000000',
            '18': '000000000'
        },
        {
            '9001': 'A005930',
            '302': '삼성전자',
            '10': '000044350',
            '25': '3',
            '11': '000000000',
            '12': '000000000',
            '13': '000000000',
            '16': '000000000',
            '17': '000000000',
            '18': '000000000'
        },
        {
            '9001': 'A005930',
            '302': '삼성전자',
            '10': '000003855',
            '25': '3',
            '11': '000000000',
            '12': '000000000',
            '13': '000000000',
            '16': '000000000',
            '17': '000000000',
            '18': '000000000'
        },
        {
            '9001': 'A005930',
            '302': '삼성전자',
            '10': '000075000',
            '25': '5',
            '11': '-00000100',
            '12': '-00000130',
            '13': '010386116',
            '16': '000075100',
            '17': '000075600',
            '18': '000074700'
        },
        {
            '9001': 'A005930',
            '302': '삼성전자',
            '10': '000002900',
            '25': '3',
            '11': '000000000',
            '12': '000000000',
            '13': '000000000',
            '16': '000000000',
            '17': '000000000',
            '18': '000000000'
        }
    ]
}


# --------- 가짜 DB/Insert/모델 구현 (monkeypatch 용) ---------
class ExcludedProxy:
    """stmt.excluded[col] 형태 접근을 받아주는 프록시 (SQLAlchemy 흉내)."""
    def __getitem__(self, key):
        return f"EXCLUDED.{key}"  # 값 자체는 안 쓰고 키만 검증에 활용

class FakeInsertStmt:
    def __init__(self, model):
        self.model = model
        self._records = None
        self.excluded = ExcludedProxy()
        self.index_elements = None
        self.set_ = None

    def values(self, records):
        self._records = records
        return self

    def on_conflict_do_update(self, *, index_elements, set_):
        self.index_elements = index_elements
        self.set_ = set_
        return self

def fake_insert(model):
    return FakeInsertStmt(model)

class FakeSession:
    def __init__(self, sink: dict):
        self.sink = sink

    async def execute(self, stmt: FakeInsertStmt):
        # 테스트에서 검증할 수 있도록 실행 정보를 모아둔다
        self.sink["executed"] = True
        self.sink["records"] = stmt._records
        self.sink["index_elements"] = stmt.index_elements
        self.sink["set_keys"] = sorted(list(stmt.set_.keys())) if stmt.set_ else []

    async def commit(self):
        self.sink["committed"] = True

class FakeGetDBCtx:
    def __init__(self, sink: dict):
        self.sink = sink
    async def __aenter__(self):
        return FakeSession(self.sink)
    async def __aexit__(self, exc_type, exc, tb):
        return False

def make_fake_get_db(sink: dict):
    def _factory():
        return FakeGetDBCtx(sink)
    return _factory




# ---------- 테스트들 ----------
@pytest.mark.asyncio
async def test_on_msg_cnsrlst_populates_conditional_searches(monkeypatch):
    # 모듈 전역 초기화
    m.conditional_searches = []

    # 실행
    await m.on_msg(CNSRLST_MSG)

    # 검증: 5개 조건식이 채워져야 함
    assert len(m.conditional_searches) == 5
    assert m.conditional_searches[0].id == '0'
    assert m.conditional_searches[0].name == '조건1'
    assert m.conditional_searches[0].stock_codes == []


@pytest.mark.asyncio
async def test_on_msg_cnsrreq_upserts_when_conditions_exist(monkeypatch):
    # 준비: 조건식이 하나라도 있어야 DB 업서트가 수행됨
    m.conditional_searches = [m.ConditionalSearch(id="0", name="조건1")]
    m.base_date = "2025-09-01"

    # DB/Insert/모델 스텁 주입
    sink = {}
    monkeypatch.setattr(m, "get_db", make_fake_get_db(sink), raising=True)
    monkeypatch.setattr(m, "insert", fake_insert, raising=True)
    monkeypatch.setattr(m, "ConditionSearchResult", _ConditionSearchResult, raising=True)

    # 실행
    await m.on_msg(CNSRREQ_MSG)

    # 검증: execute/commit 호출, 레코드 수, 업서트 키 등
    assert sink.get("executed") is True
    assert sink.get("committed") is True

    records = sink["records"]
    assert len(records) == 5  # '9001'이 모두 채워져 있으므로 5건

    # 각 record 필드 확인(샘플로 첫 건만 체크)
    r0 = records[0]
    assert r0["base_date"] == "2025-09-01"
    assert r0["symbol"] == "A005930"
    assert r0["name"] == "삼성전자"
    assert isinstance(r0["price"], Decimal)

    # 업서트 키/세트 필드 검증
    assert sink["index_elements"] == ["base_date", "symbol"]
    # id/base_date/symbol 은 set_ 대상에서 제외됨 (키/식별자라서)
    assert "id" not in sink["set_keys"]
    assert "base_date" not in sink["set_keys"]
    assert "symbol" not in sink["set_keys"]


@pytest.mark.asyncio
async def test_on_msg_cnsrreq_does_nothing_when_no_conditions(monkeypatch):
    # 준비: 조건식이 비어 있으면 DB 작업이 없어야 함
    m.conditional_searches = []
    m.base_date = "2025-09-01"

    sink = {}
    monkeypatch.setattr(m, "get_db", make_fake_get_db(sink), raising=True)
    monkeypatch.setattr(m, "insert", fake_insert, raising=True)
    # monkeypatch.setattr(m, "ConditionSearchResult", _ConditionSearchResult, raising=True)

    await m.on_msg(CNSRREQ_MSG)

    # DB 실행 흔적이 없어야 함
    assert sink.get("executed") is None
    assert sink.get("committed") is None