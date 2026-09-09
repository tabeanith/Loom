

# Full list
{'Power DE': 'B0IYOQ',
 'Power ES': '04STAX',
 'Power NL': 'Z8SLIK',
 'Power NO1': '1TAHM6',
 'Power NO3': 'XJRIVY',
 'Power NO4': 'T1V1QF',
 'Power NO5': 'NRO4V5',
 'Power SE1': '2S1VHH',
 'Power SE3': 'Q4LDA9',
 'Power FI': '4GXA2P',
 'Power Nordic System': 'VJPDS3',
 'Power CH': 'RJOAH1',
 'Power IT': 'SRFOY9',
 'Power DK2': '559Q64',
 'Power DK1': 'M2G4WC',
 'Power HU': '560FCT',
 'Power CZ': '6CUIIB',
 'Power FR phys': 'HV2AD1',
 'Power FR': 'TPJH2P',
 'Power FR fin': 'HVZ5K6',
 'Gas TTF': '7AYEC9',
 'Gas PL': '5XMXI6',
 'Gas SK': 'P28V1J',
 'Gas CZ': 'KBD4RK',
 'Power NO2': '8T6I87',
 'Power SE4': 'AUW3TL',
 'Power SE2': 'LE9N5N',
 'Power BE': 'F9DH5K',
 'Power AT': 'LI0UCF',
 'Coal API2 USD': '99BAP1',
 'Coal API2 EUR': 'QI5BL2',
 'Gas NCG': 'NJ5EB1',
 'Gas PSV': 'O1BV9T',
 'EUA': 'B3QFE4',
 'GO Rheinschiene':'3KXDQQ',
 'EURUSD': '9TXA8U',
 'EURGBP': 'VL16VR'}



live_curve_fuels = {
    'coal_api2_usd': '99BAP1',
    # 'power_germany': 'B0IYOQ',
    'eua': 'B3QFE4',
    #'gas_the': 'NJ5EB1',
    'fx_usd_eur': '9TXA8U'
}

market_to_eod_pfc_identifier_in_dbb = {
    'coal_api2_eur': 'G7CWO2',
    'power_germany': 'L5A2UU',
    'power_germany_last_shape': 'GWR40C',
    'power_france': 'X3EQNI',
    'eua': 'RMTKHT',
    'gas_ncg_prices_ttf_vols_hybrid': 'RGLKZG',
    'gas_ncg': 'RGLKZG',
    'euribor': 'unknown',
    'go_rheinschiene': '3KXDQQ',
    'hfo_germany': 'VXHTYP',
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
