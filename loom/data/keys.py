import dataclasses


@dataclasses.dataclass
class Keys:

    power_germany: str = "power_germany"
    gas: str = "gas"
    carbon: str = "carbon"
    coal: str = "coal"

    cds: str = "cds"
    css: str = "css"
    gen_coal: str = "gen_coal"
    gen_gas: str = "gen_gas"
    contra_fuels: str = "contra_fuels"

    asset_n_storage_base_mw: str = "asset_n_storage_base_mw"
    asset_n_storage_value_eur: str = "asset_n_storage_value_eur"

    residual_load_ec00ops: str = "residual_load_ec00ops"
    residual_load_ec00ens: str = "residual_load_ec00ens"
    residual_load_ec06ops: str = "residual_load_ec06ops"
    residual_load_ec06ens: str = "residual_load_ec06ens"
    rdl_ec00: str = "rdl_ec00"
    rdl_ec06: str = "rdl_ec06"
    residual_load_ec46: str = "residual_load_ec46"

    signal_delivered: str = "signal_delivered"
    signal_stop: str = "signal_stop"

    spot_power_germany: str = "spot_power_germany"
    spot_gas_the: str = "spot_gas_the"
    spot_carbon_eua: str = "spot_carbon_eua"
    spot_coal_api2: str = "spot_coal_api2"

    price_implied: str = "price_implied"
    price_market: str = "price_market"
    implied_vs_market: str = "implied_vs_market"

    pricing_regime: str = "pricing_regime"
    pricing_regime_str: str = "pricing_regime_str"
    mtm_model: str = "mtm_model_EUR"

    specs: str = "specs"
    summary_mtms_in_eur: str = "summary_mtms_in_eur"
    summary_positions_in_mw: str = "summary_positions_in_mw"
    summary_positions_in_mwh: str = "summary_positions_in_mwh"



    # For calibration
    name: str = "name"
    contracts: str = "contracts"
    use_n_front_contracts_to_trade: str = "use_n_front_contracts_to_trade"
    use_n_front_contracts_to_regim: str = "use_n_front_contracts_to_regim"
    daily_clip_size: str = "daily_clip_size"  # MW executed per day
    spread_pct: str = "spread_pct"
    implied_price_lookback: str = "implied_price_lookback"  # days
    regime_check_lookback: str = "regime_check_lookback"  # days
    regime_check_pnltresh: str = "regime_check_pnltresh"  # EUR/MWh
    treshold_to_select_implied_prices: str = "treshold_to_select_implied_prices"  # EUR/MWh
    treshold_to_generate_signal: str = "treshold_to_generate_signal"  # EUR/MWh






    # EXPERIMENTAL
    residual_load_backcast: str = "residual_load_backcast"

    cross_border_exchange_ec00ops: str = "cross_border_exchange_ec00ops"
    cross_border_exchange_ec00ens: str = "cross_border_exchange_ec00ens"
    cross_border_exchange_ec46: str = "cross_border_exchange_ec46"

    rdl_ec00_chg_factor: str = "rdl_ec00_chg_factor"
    rdl_ec00_chg_on_prices: str = "rdl_ec00_chg_on_prices"

    cross_border_exchange_backcast: str = "cross_border_exchange_backcast"
    temperature_backcast: str = "temperature_backcast"
    hydro_pump_actual: str = "hydro_pump_actual"
    hydro_turb_actual: str = "hydro_turb_actual"

    gas_backwardation: str = "gas_backwardation"

    CONTRACT_WEEKS: str = "KW"
    CONTRACT_MONTHS: str = "M"
    CONTRACT_QUARTERS: str = "Q"



