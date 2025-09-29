from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional


from exchange.bitget.client.signature_client import SignatureClient


class BitgetFutureTradeClient(SignatureClient):

    def __init__(
        self,
        base_url: str,
        access_key: str,
        secret_key: str,
        passphrase: str,
    ):
        super().__init__(base_url, access_key, secret_key, passphrase)

    async def __aenter__(self) -> "BitgetFutureTradeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.close()

    async def get_history_orders(
        self,
        product_type: str,
        order_id: str = None,
        client_oid: str = None,
        symbol: str = None,
        id_less_than: str = None,
        order_source: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ):
        """
        Fetch historical orders (up to 90 days) from Bitget.
        """
        path = "/api/v2/mix/order/orders-history"
        # assemble query params
        params = {"productType": product_type}
        for key, value in [
            ("orderId", order_id),
            ("clientOid", client_oid),
            ("symbol", symbol),
            ("idLessThan", id_less_than),
            ("orderSource", order_source),
            (
                "startTime",
                str(int(start_time.timestamp() * 1000)) if start_time else None,
            ),
            ("endTime", str(int(end_time.timestamp() * 1000)) if end_time else None),
            ("limit", limit),
        ]:
            if value is not None:
                params[key] = value

        return await self.get(path, params=params)

    async def place_order(
        self,
        *,
        symbol: str,
        product_type: str,
        size: Decimal,
        side: str,
        order_type: str = "limit",
        price: Optional[Decimal] = None,
        preset_tp_price: Optional[Decimal] = None,
        preset_sl_price: Optional[Decimal] = None,
        trade_side: Optional[str] = None,   # hedge-mode: "open" | "close"
        hold_side: Optional[str] = None,    # hedge-mode: "long" | "short"
        margin_mode: Optional[str] = "crossed",
        margin_coin: Optional[str] = "USDT",
        force: Optional[str] = None,        # limit 주문일 때 gtc/ioc/fok/post_only
        client_oid: Optional[str] = None,   # 주문 식별용
    ):
        """
        Place a new order on Bitget.
        trade_side: "open" 신규 / "close" 청산
        side: buy/sell (포지션 방향 반대 청산 시 사용)
        """
        path = "/api/v2/mix/order/place-order"
        if order_type == "limit" and price is None:
            raise ValueError("limit 주문에는 price가 필요합니다")

        # limit 주문이면 force를 gtc로 설정
        if order_type == "limit" and force is None:
            force = "gtc"

        body = {
            "symbol": symbol, "productType": product_type,
            **({"marginMode": margin_mode} if margin_mode else {}),
            **({"marginCoin": margin_coin} if margin_coin else {}),
            "size": str(size), "side": side, "orderType": order_type,
            **({"price": str(price)} if (order_type=="limit" and price is not None) else {}),
            **({"tradeSide": trade_side} if trade_side else {}),
            **({"holdSide": hold_side} if hold_side else {}),
            **({"force": force} if (order_type=="limit" and force) else {}),
            **({"clientOid": client_oid} if client_oid else {}),
            **({"presetStopSurplusPrice": str(preset_tp_price)} if preset_tp_price is not None else {}),
            **({"presetStopLossPrice": str(preset_sl_price)} if preset_sl_price is not None else {}),
        }
        return await self.post(path, json_body=body)

    async def cancel_all_orders(
        self,
        product_type: str = "USDT-FUTURES",
    ):
        """
        Cancel all orders for a given product type and symbol.
        """
        path = "/api/v2/mix/order/cancel-all-orders"
        body = {"productType": product_type}
        return await self.post(path, json_body=body)

    async def flash_close_position(
        self,
        symbol: str,
        product_type: str = "USDT-FUTURES",
        hold_side: str = "long",
    ):
        """
        Close all positions for a given symbol and hold side.
        """
        path = "/api/v2/mix/order/close-positions"
        body = {
            "symbol": symbol,
            "productType": product_type,
            "holdSide": hold_side,
        }
        return await self.post(path, json_body=body)

    # --- New helper for partial close ---
    async def partial_close_position(
        self,
        symbol: str,
        product_type: str = "USDT-FUTURES",
        hold_side: str = "long",  # 청산하려는 보유 포지션 방향
        fraction: float = 0.5,
        order_type: str = "market",
        price: Optional[Decimal] = None,  # limit 주문 시 필수
        size_step: Optional[Decimal] = None,  # 규격 없으면 그대로 사용
        min_size: Optional[Decimal] = None,  # 최소 주문수량 체크용
        force: Optional[str] = None,  # limit 주문 시 gtc/ioc/fok/post_only
        client_oid: Optional[str] = None,  # 주문 식별용
    ):
        """
        현재 포지션의 fraction(예: 0.5) 만큼 부분 청산.
        1) 단일 심볼 포지션 조회
        2) hold_side 일치 포지션 찾기
        3) size * fraction 계산 후 step / min 반올림
        4) 반대 side (long->sell, short->buy) 로 tradeSide='close' 주문
        """
        import logging
        logger = logging.getLogger("bitget.partial_close_position")

        if not (0 < fraction <= 1):
            raise ValueError("fraction 은 0 ~ 1 사이 여야 합니다")

        # 포지션 조회 (position client 기능 경량 복제)
        path = "/api/v2/mix/position/single-position"
        params = {"symbol": symbol, "productType": product_type, "marginCoin": "USDT"}
        res = await self.get(path, params=params)
        logger.info(f"[포지션조회] symbol={symbol}, res={res}")
        data = res.get("data")
        if not data:
            logger.warning(f"[부분청산] 포지션 없음: symbol={symbol}, hold_side={hold_side}")
            return {"status": "no_position"}

        positions_raw = data if isinstance(data, list) else [data]
        positions = [p for p in positions_raw if isinstance(p, dict)]
        if not positions:
            logger.warning(f"[부분청산] 포지션 데이터 형식 오류: {data}")
            return {"status": "invalid_position_format"}

        target = None
        for p in positions:
            try:
                if p.get("holdSide") == hold_side and Decimal(p.get("total", "0")) > 0:
                    target = p
                    break
            except Exception:
                continue
        if target is None:
            logger.warning(f"[부분청산] 해당 hold_side 포지션 없음: {hold_side}")
            return {"status": "no_target_side"}

        total_str = target.get("total", "0") if isinstance(target, dict) else "0"
        try:
            total = Decimal(total_str)
        except Exception:
            logger.warning(f"[부분청산] total 파싱 오류: {total_str}")
            return {"status": "invalid_total"}
        if total <= 0:
            logger.warning(f"[부분청산] 포지션 수량 0: {total}")
            return {"status": "empty"}

        close_size = total * Decimal(str(fraction))

        # step 적용
        if size_step:
            if size_step <= 0:
                raise ValueError("size_step 은 양수여야 합니다")
            quant_factor = (close_size / size_step).to_integral_value(
                rounding=ROUND_DOWN
            )
            close_size = quant_factor * size_step
        if min_size and close_size < min_size:
            logger.warning(f"[부분청산] 최소 주문수량 미만: {close_size} < {min_size}")
            return {"status": "below_min_size"}
        if close_size <= 0:
            logger.warning(f"[부분청산] 계산된 청산수량 0")
            return {"status": "computed_zero"}

        # limit 주문이면 price 필수
        if order_type == "limit" and price is None:
            raise ValueError("limit 주문에는 price가 필요합니다")

        side = "sell" if hold_side == "long" else "buy"
        logger.info(f"[부분청산] 주문 파라미터: symbol={symbol}, size={close_size}, side={side}, order_type={order_type}, price={price}, tradeSide=close, holdSide={hold_side}, force={force}")

        return await self.place_order(
            symbol=symbol,
            product_type=product_type,
            size=close_size,
            side=side,
            order_type=order_type,
            price=price,
            trade_side="close",                # hedge-mode close
            hold_side=hold_side,               # specify long/short explicitly
            margin_mode=(
                target.get("marginMode", "crossed")
                if isinstance(target, dict)
                else "crossed"
            ),
            margin_coin=(
                target.get("marginCoin", "USDT") if isinstance(target, dict) else "USDT"
            ),
            force=force,
            client_oid=client_oid,
        )
