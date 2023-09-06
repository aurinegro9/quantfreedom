import pandas as pd

from quantfreedom.poly.enums import *
from quantfreedom.poly.long_short_orders import LongOrder
from quantfreedom._typing import pdFrame
from quantfreedom.enums.enums import (
    CandleBody,
    StaticVariables,
    OrderSettingsArrays,
)
from quantfreedom.nb.helper_funcs import (
    all_os_as_1d_arrays_nb,
    check_os_1d_arrays_nb,
    create_os_cart_product_nb,
    static_var_checker_nb,
)
from quantfreedom.nb.simulate import backtest_df_only_nb


def backtest_df_only(
    entry_size_type: EntrySizeType,
    order_type: OrderType,
    sl_type: StopLossType,
    candle_body: CandleBody,
    tp_type: TakeProfitType,
    leverage_type: LeverageType,
    account_state: AccountState,
    order_settings: OrderSettings,
    backtest_settings: BacktestSettings,
    exchange_settings: ExchangeSettings,
    price_data: pdFrame,
    entries: pdFrame,
) -> tuple[pdFrame, pdFrame]:
    if order_type == OrderType.Long:
        order = LongOrder(
            sl_type=sl_type,
            candle_body=candle_body,
            tp_type=tp_type,
            entry_size_type=entry_size_type,
            leverage_type=leverage_type,
            order_settings=order_settings,
            exchange_settings=exchange_settings,
            backtest_settings=backtest_settings,
        )
        
    num_of_symbols = len(price_data.columns.levels[0])

    # Creating Settings Vars
    # total_order_settings = os_cart_arrays_tuple.sl_pct.shape[0]
    total_order_settings = 1

    total_indicator_settings = entries.shape[1]

    total_bars = entries.shape[0]

    # Printing out total numbers of things
    print(
        "Starting the backtest now ... and also here are some stats for your backtest.\n"
    )
    print(f"Total symbols: {num_of_symbols:,}")
    print(
        f"Total indicator settings per symbol: {int(total_indicator_settings / num_of_symbols):,}"
    )
    print(f"Total indicator settings to test: {total_indicator_settings:,}")
    print(f"Total order settings per symbol: {total_order_settings:,}")
    print(f"Total order settings to test: {total_order_settings * num_of_symbols:,}")
    print(f"Total candles per symbol: {total_bars:,}")
    print(
        f"Total candles to test: {total_indicator_settings * total_order_settings * total_bars:,}"
    )
    print(
        f"\nTotal combinations to test: {total_indicator_settings * total_order_settings:,}"
    )

    strat_array, settings_array = backtest_df_only_nb(
        order=order,
        entries=entries.values,
        num_of_symbols=num_of_symbols,
        os_cart_arrays_tuple=os_cart_arrays_tuple,
        price_data=price_data.values,
        static_variables_tuple=static_variables_tuple,
        total_bars=total_bars,
        total_indicator_settings=total_indicator_settings,
        total_order_settings=total_order_settings,
    )

    strat_results_df = pd.DataFrame(strat_array).sort_values(
        by=["to_the_upside", "gains_pct"], ascending=False
    )

    symbols = list(price_data.columns.levels[0])

    for i in range(len(symbols)):
        strat_results_df.replace({"symbol": {i: symbols[i]}}, inplace=True)

    symbols = list(entries.columns.levels[0])
    setting_results_df = pd.DataFrame(settings_array).dropna(axis="columns", thresh=1)

    for i in range(len(CandleBody._fields)):
        setting_results_df.replace(
            {"tsl_based_on": {i: CandleBody._fields[i]}}, inplace=True
        )
        setting_results_df.replace(
            {"sl_to_be_based_on": {i: CandleBody._fields[i]}}, inplace=True
        )
    for i in range(len(symbols)):
        setting_results_df.replace({"symbol": {i: symbols[i]}}, inplace=True)

    setting_results_df = setting_results_df.T

    return strat_results_df, setting_results_df


def sim_6(
    entries,
    price_data,
    static_variables_tuple: StaticVariables,
    broadcast_arrays: OrderSettingsArrays,
) -> tuple[pdFrame, pdFrame]:
    order_records = _sim_6(
        price_data=price_data,
        entries=entries,
        static_variables_tuple=static_variables_tuple,
        broadcast_arrays=broadcast_arrays,
    )

    return order_records
