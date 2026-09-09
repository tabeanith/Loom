

live_curve_fuels = {
    'coal_api2_usd': 'TZ8KM',
    'coal_api2_eur': '8ZRVV',
    # 'power_germany': 'XII0N',
    'eua': 'JO59V',
    #'gas_the': 'M4E1P',
    'fx_usd_eur': 'WKWYP'
}

market_to_eod_pfc_identifier_in_dbb = {
    'coal_api2_usd': 'TLU1L',
    'coal_api2_eur': 'JFKXZ',
    'power_germany': 'E63YU',
    'power_france': 'B0IJA',
    'eua': '1LAWS',
    'gas_ncg_prices_ttf_vols_hybrid': 'PQ9X6',
    'gas_ncg': 'PQ9X6',
    'euribor': 'unknown',
    'go_rheinschiene': 'QKB6S',
    'hfo_germany': '212IL',
}

market_to_live_pfc_identifier_in_dbb = {
    'coal_api2_eur': 'QI5BL2',
    'power_germany': 'B0IYOQ',
    'power_france': market_to_eod_pfc_identifier_in_dbb['power_france'],  # No live curve
    'eua': 'B3QFE4',
    'gas_ncg_prices_ttf_vols_hybrid': 'NJ5EB1',
    'gas_ncg': 'NJ5EB1',
    'euribor': market_to_eod_pfc_identifier_in_dbb['euribor'],  # No live curve
    'go_rheinschiene': market_to_eod_pfc_identifier_in_dbb['go_rheinschiene'],  # No live curve
    'hfo_germany': market_to_eod_pfc_identifier_in_dbb['hfo_germany'],  # No live curve
    'fx_usd_eur': '9TXA8U'
}
