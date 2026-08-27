import pandas as pd
import pulp

from aleph.power_backtesting.data.simulated import generate_germany_solar_profile


class Battery:

    def __init__(self,
                  max_produce_mw: int,
                  max_storage_mwh: int,
                  efficiency: float,
        ):
        self.name = "battery"
        self.max_produce_mw  = max_produce_mw  # Max Power (MW)
        self.max_storage_mwh  = max_storage_mwh  # Reservoir Capacity (MWh equivalent)
        self.efficiency  = efficiency  # Round-trip efficiency (applied to both ways as sqrt or simplify)
        self.v_initial_mwh = self.max_storage_mwh / 2.  # Starting energy in reservoir


    def set_start_value_mwh(self, start_value: float):
        self.v_initial_mwh = start_value


    def valuate(self, prices, opt_schedule):
        return prices * opt_schedule


    def optimize(self, ts_start_optimization, prices: pd.Series):
        _prices = prices[prices.index >= ts_start_optimization]
        _index = _prices.index

        _prices = _prices.values
        n_hours = len(_prices)

        # 2. Define the Problem
        prob = pulp.LpProblem("Pump_Storage_Optimization", pulp.LpMaximize)

        # 3. Decision Variables
        gen = [pulp.LpVariable(f"gen_{t}", 0, self.max_produce_mw) for t in range(n_hours)]
        pump = [pulp.LpVariable(f"pump_{t}", 0, self.max_produce_mw) for t in range(n_hours)]
        vol = [pulp.LpVariable(f"vol_{t}", 0, self.max_storage_mwh) for t in range(n_hours)]

        # 4. Objective Function: Maximize Revenue
        prob += pulp.lpSum([gen[t] * _prices[t] - pump[t] * _prices[t] for t in range(n_hours)])

        # 5. Constraints
        for t in range(n_hours):
            # Energy Balance Constraint
            if t == 0:
                prob += vol[t] == self.v_initial_mwh + (pump[t] * self.efficiency) - (gen[t] / self.efficiency)
            else:
                prob += vol[t] == vol[t - 1] + (pump[t] * self.efficiency) - (gen[t] / self.efficiency)

            # Optional: Prevent simultaneous pumping and generating
            # (Though the optimizer naturally avoids this if prices > 0 and self.efficiency < 1)

        # 6. Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=0))

        # 7. Output Results
        if False:
            print(f"Status: {pulp.LpStatus[prob.status]}")
            print(f"Total Profit: ${pulp.value(prob.objective):.2f}")
            print("\nHour | Price | Action | Power (MW) | Reservoir (MWh)")
            print("-" * 50)
            for t in range(n_hours):
                g_val = gen[t].varValue
                p_val = pump[t].varValue
                action = "GEN" if g_val > 0 else "PUMP" if p_val > 0 else "IDLE"
                power = g_val if g_val > 0 else p_val
                print(f"{t:02d}   | {_prices[t]:<5} | {action:<5} | {power:<10.1f} | {vol[t].varValue:.1f}")

        opt_produce = pd.Series(index=_index, data=[x.varValue for x in gen])
        opt_charge = pd.Series(index=_index, data=[x.varValue for x in pump])
        opt_storage = pd.Series(index=_index, data=[x.varValue for x in vol])
        opt_schedule = opt_produce - opt_charge

        return opt_schedule, opt_storage


class Battery_Colocated:

    def __init__(self,
                  max_produce_mw: int,
                  max_storage_mwh: int,
                  efficiency: float,
        ):
        self.name = "battery_colocated"
        self.max_produce_mw  = max_produce_mw  # Max Power (MW)
        self.max_storage_mwh  = max_storage_mwh  # Reservoir Capacity (MWh equivalent)
        self.efficiency  = efficiency  # Round-trip efficiency (applied to both ways as sqrt or simplify)
        self.v_initial_mwh = self.max_storage_mwh / 2.  # Starting energy in reservoir


    def set_start_value_mwh(self, start_value: float):
        self.v_initial_mwh = start_value


    def valuate(self, prices, opt_schedule):
        return prices * opt_schedule


    def optimize(self, ts_start_optimization, prices: pd.Series):
        _prices = prices[prices.index >= ts_start_optimization]
        _index = _prices.index

        n_hours = _prices.shape[0]
        _solar_generation = generate_germany_solar_profile(_index)

        # Lets assume solar_generation is normalized at 1MW
        _solar_generation = _solar_generation * self.max_produce_mw * 1.5
        _solar_generation = _solar_generation.clip(upper=self.max_produce_mw)

        # 3. Define Problem
        prob = pulp.LpProblem("Battery_Optimization", pulp.LpMaximize)

        # 4. Decision Variables
        # charge/discharge are flow rates; soc is State of Charge
       # charge = [pulp.LpVariable(f"pump_{t}", 0, self.max_produce_mw) for t in range(n_hours)]
        discharge = [pulp.LpVariable(f"gen_{t}", 0, self.max_produce_mw) for t in range(n_hours)]
        vol = [pulp.LpVariable(f"vol_{t}", 0, self.max_storage_mwh) for t in range(n_hours)]

        # 5. Objective Function: Maximize (Sales - Purchases)
        # We assume "net" energy: (Solar + Discharge - Charge) * Price
        prob += pulp.lpSum([discharge[t] * _prices.values[t] for t in range(n_hours)])

        # 6. Constraints
        for t in range(n_hours):
            # Energy Balance (SoC transition)
            if t == 0:
                prob += vol[t] == self.v_initial_mwh - (discharge[t] / self.efficiency) + (_solar_generation[t] * self.efficiency)
            else:
                prob += vol[t] == vol[t - 1] - (discharge[t] / self.efficiency) + (_solar_generation[t] * self.efficiency)

            # Optional: Ensure battery doesn't discharge more than what's available in SoC
           # prob += discharge[t] <= (vol[t - 1] if t > 0 else self.v_initial_mwh)


        # 7. Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=0))

        opt_produce = pd.Series(index=_index, data=[x.varValue for x in discharge])
       # opt_charge = pd.Series(index=_index, data=[x.varValue for x in charge])
        opt_storage = pd.Series(index=_index, data=[x.varValue for x in vol])
        opt_schedule = opt_produce # - opt_charge

        valuation = prices * opt_schedule

        return opt_schedule, opt_storage, valuation


class Turbine:

    def __init__(self,
                  max_produce_mw: int,
                  strike: float,
        ):
        self.name = "turbine"
        self.max_produce_mw  = max_produce_mw  # Max Power (MW)
        self.strike  = strike  # Reservoir Capacity (MWh equivalent)


    def set_start_value_mwh(self, start_value: float):
        pass


    def valuate(self, prices, opt_schedule):
        _prices = prices.reindex(opt_schedule.index)
        valuation = (_prices - self.strike).clip(lower=0.) * opt_schedule
        return valuation


    def optimize(self, ts_start_optimization, prices: pd.Series):
        _prices = prices[prices.index >= ts_start_optimization]
        _index = _prices.index

        _prices = _prices.values
        n_hours = len(_prices)

        opt_schedule = pd.Series(index=_index, data=0)
        opt_storage = pd.Series(index=_index, data=0)
        opt_schedule += (_prices > self.strike).astype(int) * self.max_produce_mw

        valuation = (_prices - self.strike).clip(lower=0.) * opt_schedule

        return opt_schedule, opt_storage, valuation


class MarketSynthTurbine:

    def __init__(self,
                  max_produce_mw: int,
                  quantile: float,

        ):
        self.name = "turbine"
        self.max_produce_mw  = max_produce_mw  # Max Power (MW)
        self.quantile = 0.75


    def set_start_value_mwh(self, start_value: float):
        pass


    def valuate(self, prices, opt_schedule):
        return None


    def optimize(self, ts_start_optimization, prices: pd.Series):
        _prices = prices[prices.index >= ts_start_optimization]
        _index = _prices.index

        # TODO: How to exactly determine the strike? This would be a forward looing strike calculation (_prices are the forward curve)
        strike = _prices.rolling(24*30).quantile(self.quantile).bfill()  # TODO: Maybe take CSS into consideration?

        _prices = _prices.values
        n_hours = len(_prices)

        opt_schedule = pd.Series(index=_index, data=0)
        opt_storage = pd.Series(index=_index, data=0)
        opt_schedule += (_prices > strike).astype(int) * self.max_produce_mw

        valuation = (_prices - strike).clip(lower=0.) * opt_schedule

        return opt_schedule, opt_storage, valuation


