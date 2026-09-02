import numpy as np
import pandas as pd
import numba as nb
from numba import njit, int32, float32, int64, prange, boolean


@njit
def numba_rolling_quantile_q_value(data, rolling_window):
    """

    """
    length = data.shape[0]
    result = np.copy(data)
    result[:] = np.nan

    for i in nb.prange(length):
        if i < rolling_window: continue
        _i_start = max([0, i-rolling_window])
        _data = data[_i_start:i+1]

        _latest = _data[-1]
        if np.isnan(_latest): continue

        _data_nonnan = _data[~np.isnan(_data)]
        result[i] = np.mean(_data_nonnan < _latest)

    return result
