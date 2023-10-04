import logging
from time import sleep
from uuid import uuid4
from quantfreedom.enums import LeverageModeType, LongOrShortType, PositionModeType
from quantfreedom.exchanges.exchange import UNIVERSAL_TIMEFRAMES
from quantfreedom.exchanges.live_exchange import LiveExchange
from quantfreedom.exchanges.mufex_exchange.mufex import MUFEX_TIMEFRAMES, Mufex


class LiveMufex(LiveExchange, Mufex):
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        symbol: str,
        trading_in: str,
        timeframe: str,
        use_test_net: bool,
        long_or_short: LongOrShortType,
        candles_to_dl: int = None,
        keep_volume_in_candles: bool = False,
        position_mode: PositionModeType = PositionModeType.HedgeMode,
        leverage_mode: LeverageModeType = LeverageModeType.Isolated,
        category: str = "linear",
    ):
        super().__init__(
            api_key,
            secret_key,
            symbol,
            timeframe,
            trading_in,
            candles_to_dl,
            keep_volume_in_candles,
            long_or_short,
            use_test_net,
            position_mode,
            leverage_mode,
        )
        self.category = category
        self.mufex_timeframe = MUFEX_TIMEFRAMES[UNIVERSAL_TIMEFRAMES.index(timeframe)]

        if keep_volume_in_candles:
            self.volume_yes_no = -1
        else:
            self.volume_yes_no = -2

        if position_mode == PositionModeType.HedgeMode:
            self.set_position_mode_as_hedge_mode(symbol=self.symbol)
        else:
            self.set_position_mode_as_one_way_mode(symbol=self.symbol)

        if leverage_mode == LeverageModeType.Isolated:
            self.set_leverage_mode_isolated(symbol=self.symbol)
        elif leverage_mode == LeverageModeType.Cross:
            self.set_leverage_mode_cross(symbol=self.symbol)

        self.candles_to_dl_ms = self.get_candles_to_dl_in_ms(
            candles_to_dl=candles_to_dl,
            timeframe_in_ms=self.timeframe_in_ms,
            limit=200,
        )

        self.set_exchange_settings(
            symbol=symbol,
            position_mode=position_mode,
            leverage_mode=leverage_mode,
        )

    def set_init_last_fetched_time(self, **vargs):
        """
        https://www.mufex.finance/apidocs/derivatives/contract/index.html?console#t-dv_querykline
        """
        init_end = self.get_current_time_ms() - self.timeframe_in_ms
        init_start = init_end - self.timeframe_in_ms

        end_point = "/public/v1/market/kline"
        params = {
            "category": self.category,
            "symbol": self.symbol,
            "interval": self.mufex_timeframe,
            "start": init_start,
            "end": init_end,
        }
        try:
            response = self.HTTP_get_request(end_point=end_point, params=params)
            data_list = response.get("data").get("list")
            if data_list is not None and data_list:
                self.last_fetched_ms_time = int(data_list[-1][0])
            else:
                raise Exception(f"LiveMufex Class Data or List is empty {response.get('message')}")
        except Exception as e:
            raise Exception(f"LiveMufex Class Something is wrong with set_init_last_fetched_time -> {e}")

    def set_candles_df_and_np(self, **vargs):
        """
        https://www.mufex.finance/apidocs/derivatives/contract/index.html?console#t-dv_querykline
        """

        until_date_ms = self.get_current_time_ms() - self.timeframe_in_ms
        since_date_ms = until_date_ms - self.candles_to_dl_ms

        candles_list = []
        end_point = "/public/v1/market/kline"
        params = {
            "category": self.category,
            "symbol": self.symbol,
            "interval": self.mufex_timeframe,
            "start": since_date_ms,
            "end": until_date_ms,
        }
        while params["start"] + self.timeframe_in_ms < until_date_ms:
            response = self.HTTP_get_request(end_point=end_point, params=params)
            try:
                new_candles = response["data"]["list"]
                last_candle_time_ms = int(new_candles[-1][0])
                if last_candle_time_ms == params["start"]:
                    sleep(0.2)
                else:
                    candles_list.extend(new_candles)
                    # add one sec so we don't download the same candle two times
                    params["start"] = last_candle_time_ms + 1000
            except Exception as e:
                raise Exception(f"LiveMufex Class Something is wrong with get_candles_df {response.get('message')} - > {e}")
        self.candles_df = self.get_candles_list_to_pd(candles_list=candles_list, col_end=-2)
        self.candles_np = self.candles_df.iloc[:, 1:].values

    def check_long_hedge_mode_if_in_position(self, **vargs):
        if float(self.get_symbol_position_info(symbol=self.symbol)[0]["entryPrice"]) > 0:
            return True
        else:
            return False

    def create_long_hedge_mode_entry_market_order(
        self,
        asset_amount: float,
        time_in_force: str = "ImmediateOrCancel",
        **vargs,
    ):
        params = {
            "symbol": self.symbol,
            "positionIdx": 1,
            "side": "Buy",
            "orderType": "Market",
            "qty": str(asset_amount),
            "timeInForce": time_in_force,
            "orderLinkId": uuid4().hex,
        }
        return self.create_order(params=params)

    def create_long_hedge_mode_tp_limit_order(
        self,
        asset_amount: float,
        tp_price: float,
        time_in_force: str = "PostOnly",
        **vargs,
    ):
        params = {
            "symbol": self.symbol,
            "side": "Sell",
            "positionIdx": 1,
            "orderType": "Limit",
            "qty": str(asset_amount),
            "price": str(tp_price),
            "timeInForce": time_in_force,
            "reduceOnly": True,
            "orderLinkId": uuid4().hex,
        }
        return self.create_order(params=params)

    def create_long_hedge_mode_sl_order(
        self,
        asset_amount: float,
        trigger_price: float,
        time_in_force: str = "ImmediateOrCancel",
        **vargs,
    ):
        params = {
            "symbol": self.symbol,
            "side": "Sell",
            "positionIdx": 1,
            "orderType": "Market",
            "qty": str(asset_amount),
            "timeInForce": time_in_force,
            "reduceOnly": True,
            "triggerPrice": str(trigger_price),
            "triggerDirection": 2,
            "orderLinkId": uuid4().hex,
        }
        return self.create_order(params=params)

    def get_long_hedge_mode_position_info(self):
        return self.get_symbol_position_info(symbol=self.symbol)[0]
