import asyncio
import json
import logging

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from dependency_injector.wiring import inject, Provide
from sqlalchemy.dialects.postgresql import insert
from exchange.kiwoom.rest_client import KiwoomRestClient
from exchange.kiwoom.ws_client import KiwoomWS
from model.condition_search_meta import ConditionSearchMeta
from model.condition_search_result import ConditionSearchResult
from shared.containers import Container
from shared.db import get_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def to_decimal(v: Optional[str]) -> Decimal:
    """Convert Kiwoom zero-padded numeric strings (or None/"") safely to Decimal."""
    if v is None or v == "":
        return Decimal(0)
    try:
        return Decimal(v)
    except (InvalidOperation, TypeError):
        return Decimal(0)


results = []

class ConditionSearchCollector:
    """Handle HTS 조건검색 WebSocket messages and persist results."""

    def __init__(self, ws: KiwoomWS, base_date: date):
        self.ws = ws
        self.base_date = base_date

    async def on_msg(self, msg: Dict[str, Any]) -> None:
        logger.info(f"Received message: {msg}")
        match msg:
            case {"trnm": "CNSRLST", "return_code": 0, "data": data}:
                await self._handle_cnsrlst(data)
            case {"trnm": "CNSRREQ", "return_code": 0, "data": data, "seq": condition_id}:
                await self._handle_cnsrreq(condition_id, data)
            case _:
                logger.debug("Unhandled message or non-success return_code")

    async def _handle_cnsrlst(self, data: List[List[str]]) -> None:
        """조건식 목록 수신 → 내부 상태 저장 + 각 조건식에 대한 검색 요청 발송"""
        meta_records = [{"condition_id": item[0], "name": item[1]} for item in data]

        if meta_records:
            async with get_db() as session:
                stmt = insert(ConditionSearchMeta).values(meta_records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["condition_id"],
                    set_={
                        "name": stmt.excluded.name,
                        "updated_at": "CURRENT_TIMESTAMP",
                    },
                )
                await session.execute(stmt)
                await session.commit()
            logger.info(f"Upserted {len(meta_records)} condition search meta items.")

        for item in data:  # 데모용으로 상위 5개 조건식만 처리
            seq, name = item[0], item[1]
            await self.ws.send(
                {
                    "trnm": "CNSRREQ",
                    "seq": seq,
                    "search_type": "0",
                    "stex_tp": "K",
                    "cont_yn": "N",
                    "next_key": "",
                }
            )
            # sleep
            await asyncio.sleep(0.3)
        logger.info(f"Requested condition search for {len(data)} items")

    async def _handle_cnsrreq(self, condition_id: str, data=None) -> None:
        if data is None:
            data = list()

        for item in data:
            symbol = item.get("9001")
            if not symbol:
                continue
            results.append(
                ConditionSearchResult(
                    base_date=self.base_date,
                    condition_id=condition_id,
                    symbol=symbol,
                    name=item.get("302"),
                    price=to_decimal(item.get("10")),
                    change_sign=item.get("25"),
                    change_price=to_decimal(item.get("11")),
                    change_rate=to_decimal(item.get("12")),
                    volume_acc=to_decimal(item.get("13")),
                    open=to_decimal(item.get("16")),
                    high=to_decimal(item.get("17")),
                    low=to_decimal(item.get("18")),
                    response=item,
                )
            )

        if not results:
            logger.info("No valid results to upsert (no symbol present)")
            return

        logger.info(f"Condition Search Results: {results}")


@inject
async def main(
    kiwoom_rest_client: KiwoomRestClient = Provide[Container.kiwoom_rest_client],
):
    # 1) REST 토큰 발급
    async with kiwoom_rest_client as client:
        token = await client.get_access_token()

    # 2) WS 클라이언트 구성 + 콜백 바인딩
    ws_client = KiwoomWS(
        "wss://api.kiwoom.com:10000/api/dostk/websocket",
        access_token=token,
        on_message=None,  # 콜렉터 바인딩 후 설정
    )
    collector = ConditionSearchCollector(ws=ws_client, base_date=date.today())
    ws_client.on_message = collector.on_msg

    # 3) 수신 루프 시작
    ws_task = asyncio.create_task(ws_client.run())

    # 4) 로그인 이후 약간 대기한 뒤 조건식 목록 요청 (CNSRLST)
    await asyncio.sleep(1)
    await ws_client.send({"trnm": "CNSRLST"})

    # 5) 데모: 5초간 실행 후 종료 (필요 시 취향껏 변경)
    await asyncio.sleep(60)

    # Build clean dicts explicitly to avoid ORM internals in __dict__
    records = []
    for r in results:
        records.append(
            {
                "base_date": r.base_date,
                "condition_id": r.condition_id.strip(),
                "symbol": r.symbol.strip(),
                "name": r.name.strip(),
                "price": r.price,
                "change_sign": r.change_sign,
                "change_price": r.change_price,
                "change_rate": r.change_rate,
                "volume_acc": r.volume_acc,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "response": r.response,
            }
        )

    await ws_client.disconnect()
    await ws_task

    if not records:
        logger.info("No records to upsert. Exiting.")
        return

    async with get_db() as session:
        stmt = insert(ConditionSearchResult).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["condition_id", "base_date", "symbol"],
            set_={
                col: stmt.excluded[col]
                for col in records[0].keys()
                if col not in ("condition_id", "base_date", "symbol")
            },
        )
        await session.execute(stmt)
        await session.commit()
    logger.info(f"Upserted {len(records)} condition search results into database.")


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())