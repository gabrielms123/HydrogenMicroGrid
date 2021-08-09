import math


# TODO 3. Make a forecast column: It will sum the next 672 rows (7 days * 24 hours * 4 quarter of hour) of solar
#  irradiation. Once it's reaching the end, make it use the data from January ("next year")
# TODO 5. Calculate the amount of hydrogen that will be produced in the next 30 days.
# TODO 6. Compressor consumption for hydrogen from the grid
# TODO 7. Electrolyzers can be turned off only 5 times a day


def call_electrolyzer(installed_capacity, electrical_consumption=4800, PE_efficiency=0.98, unit_capacity=2_400,
                      number_electrolyzer=20, temp_out=50, p_out=50, water_consumption=0.4):
    electrolyzer_kwargs = {
        'electrical_consumption': electrical_consumption,  # Wh/Nm3
        'PE_efficiency': PE_efficiency,  # %
        'installed_capacity': installed_capacity,
        'unit_capacity': unit_capacity,  # W
        'temp_out': temp_out,  # ºC
        'p_out': p_out,  # bar
        'number_electrolyzer': number_electrolyzer,
        'water_consumption': water_consumption  # L/h
    }
    electrolyzer = Electrolyzer(**electrolyzer_kwargs)
    return electrolyzer


def electrolyzer_switch(electrolyzer_on, electrolyzer_critical, grid_price, H2_storage, hydrogen_tank):
    if grid_price < 0.2:  # If in cheap hours
        if not electrolyzer_on and H2_storage <= hydrogen_tank.storage_lower_limit:
            electrolyzer_on = True
        elif electrolyzer_on and H2_storage <= hydrogen_tank.storage_higher_limit:  # Keep running
            electrolyzer_on = True
        else:  # turn off
            electrolyzer_on = False
        # to a certain percentage
    else:
        if H2_storage < hydrogen_tank.storage_critical_limit and not electrolyzer_on:  # This is the critical level
            electrolyzer_on = True
            electrolyzer_critical = True
        elif electrolyzer_critical and H2_storage > 2 * hydrogen_tank.storage_lower_limit:
            electrolyzer_critical = False
            electrolyzer_on = False
        else:
            electrolyzer_on = False
    return electrolyzer_on, electrolyzer_critical


class PvArray(object):
    """
    PS: Power electronics and tilt efficiency are independent of the model and are defined within the class.

    Question: is the installed capacity the expected output at 1000W/m2, after accounting for all the efficiencies?
    Or before efficiencies?

    """

    def __init__(self, pv_capacity: int, unit_nominal_power: int, panel_unit_area: float, panel_efficiency: float):
        tilt_efficiency = 0.71
        pe_efficiency = 0.95
        self.pv_capacity = pv_capacity
        self.unit_nominal_power = unit_nominal_power
        self.panel_unit_area = panel_unit_area
        self.panel_efficiency = panel_efficiency
        self.total_efficiency = tilt_efficiency * panel_efficiency * pe_efficiency
        self.area_covered = pv_capacity / unit_nominal_power * panel_unit_area

    def power_production(self, irradiation):
        output_power = irradiation * self.total_efficiency * self.area_covered
        return output_power


class Compressor(object):

    def __init__(self, max_flow: float, max_power_consumption: float, avg_consumption: float, ip_efficiency: float,
                 m_efficiency: float, e_efficiency: float):
        super().__init__()
        self.max_flow = max_flow
        self.max_power_consumption = max_power_consumption
        self.avg_consumption = avg_consumption
        self.ip_efficiency = ip_efficiency
        self.m_efficiency = m_efficiency
        self.e_efficiency = e_efficiency

    def compressor_energy(self, p_in, p_out, temp_in, m_h2):
        """This equation is for the ideal condition where
        k (1.4) is the ratio of the specific heats (cp and cv),
        RH2 is the hydrogen gas constant (4.12 kJ/kg K),
        Tin (K) is the hydrogen inlet temperature (25 ?C)
        p_in and p_out are the inlet (10 bar) and outlet (400 bar) pressures, respectively
        ip_efficiency is the isentropic efficiency
        m_efficiency is the mechanical efficiency
        e_efficiency is the electrical efficiency
        P_compressor is the electrical power required by the compressor
         """
        k = 1.4
        R_h2 = 4.12  # kJ/kg/kgK
        k_ratio = (k / (k - 1))
        total_efficiency = self.ip_efficiency * self.m_efficiency * self.e_efficiency
        L_isc = k_ratio * R_h2 * temp_in * (((p_out / p_in) ** k_ratio) - 1) / 1000  # kJ/g to kJ/kg
        E_compressor = m_h2 * L_isc / total_efficiency * 1000 / (15 * 60)  # kJ to Wh
        return E_compressor

    def power_consumption(self, h2_in: float) -> float:
        """ Calculates the power consumption of a compressor for a 15 minutes interval, according to its rated maximum
        mass flow in [kg/day] and maximum power consumption in [W/kg]. The result will be a power consumption in
        Watts [Wh/kg].

        h2_in = [kg/15']
        max_flow = [kg/day]
        max_power_consumption = [Wh/kg]

        result = [Wh]
        """
        compressor_power = 0
        if h2_in > 0:
            h2_day = h2_in * 4 * 24  # From kg/15' to kg/day
            utilization = h2_day / self.max_flow
            #    compressor_power = (utilization * self.max_power_consumption / 4) * h2_in  # the /4 is for Wh in 15'
            compressor_power = h2_in * self.avg_consumption

        return compressor_power


class HydrogenStorage(object):
    def __init__(self, p_min, p_max, m_max):
        super(HydrogenStorage, self).__init__()
        self.p_min = p_min
        self.p_max = p_max
        self.m_max = m_max
        self.storage_lower_limit = 0.3 * m_max
        self.storage_critical_limit = 0.1 * m_max
        self.storage_higher_limit = 0.95 * m_max

    def tank_pressure(self, current_storage: float) -> float:
        pressure = self.p_min + (current_storage / self.m_max) * (self.p_max - self.p_min)
        if pressure > self.p_max:
            pressure = self.p_max
        return pressure


class Electrolyzer(object):
    """
    The electrolyzer equipment will calculate how much hydrogen is produced with a certain amount of power.

    Future developments:
    > Water consumption
    > Pressure variation
    > % Utilization
    > Number of modules active, and stand-by consumption
    > Degradation
    """

    def __init__(self, electrical_consumption: float, PE_efficiency: float, installed_capacity: int, unit_capacity: int,
                 number_electrolyzer: int, temp_out: int, p_out: int, water_consumption: float):
        super().__init__()
        self.electrical_consumption = electrical_consumption
        self.PE_efficiency = PE_efficiency
        self.installed_capacity = installed_capacity
        self.unit_capacity = unit_capacity
        self.number_electrolyzer = installed_capacity / unit_capacity
        self.temp_out = temp_out
        self.p_out = p_out
        self.water_consumption = water_consumption

    def power_consumption(self, P_in: float) -> float:
        # Probably this is not doing anything for now. I will calculate this efficiency in the other methods as well.
        # This one would only return the useful power that will generate hydrogen.
        # High case P for power, low case for pressure.
        if P_in > 0:
            P_in = P_in * self.PE_efficiency
            return P_in

    def h2_production_kg(self, P_in: float):
        if P_in > 0:
            h2_out_kg = P_in / (self.electrical_consumption / 0.08988)  # Wh / ((Wh/Nm3)/(kg/Nm3))
        return h2_out_kg

    def h2_production_Nm3(self, P_in: float):
        if P_in > 0:
            h2_out_Nm3 = P_in / self.electrical_consumption
        return h2_out_Nm3

    def grid_hydrogen(self, H2_needed: float, power_already_in_use):
        """
        H2 Needed entry should be in kg
        For now there is no start-up time. Hydrogen is magically produced whenever needed. :)
        """
        H2_needed = H2_needed / 0.08988  # kg / (kg/Nm3)
        grid_consumption = H2_needed * self.electrical_consumption  # Nm3 * Wh/Nm3
        available_power = self.installed_capacity / 4  - power_already_in_use # Max Wh it can produce in 15'

        if grid_consumption > available_power:
            return available_power
        else:
            return grid_consumption

    def water_consumed(self, h2_produced: float):
        """ This method calculates the amount of water in Liters that is used to produce a certain amount of hydrogen.
         Enter h2_produced in kg.
         """
        proportional_consumption = self.water_consumption * self.electrical_consumption / self.unit_capacity
        # (L/h) * (Wh/Nm3) / (W) = L of water per Nm3 of hydrogen
        h2o_m3 = h2_produced / 0.0898
        h2o_liters = proportional_consumption * h2o_m3
        return h2o_liters

    def h2_critical(self, H2_storage, critical_level, solar_energy):
        if H2_storage < critical_level:
            free_capacity = self.installed_capacity/4 - solar_energy
            h2_critical = Electrolyzer.grid_hydrogen(self, free_capacity)
            return h2_critical
        else:
            return 0

    def max_capacity_h2(self, PV_net, P_critical, ):
        """This method makes the EL work at maximum capacity. It discounts the PV and critical level power consumptions
        from the max capacity, and activates the ELs."""


'''    def switch(self, electrolyzer_on, hour, H2_storage, storage_lower_limit, storage_higher_limit):
        """
        This method will return if the electrolyzer should stay on, or be turned off.
        It takes into consideration the previous status, the hour of day, and the level of hydrogen storage.
        """
        if hour <= 6 or hour >= 20:  # If in cheap hours
            if not electrolyzer_on and H2_storage <= storage_lower_limit:
                electrolyzer_on = True
            elif electrolyzer_on and H2_storage <= storage_higher_limit:  # Keep running
                electrolyzer_on = True
            else:  # turn off
                electrolyzer_on = False
            # to a certain percentage
        else:
            if H2_storage < storage_critical_limit and not electrolyzer_on:  # This would be the critical level
                electrolyzer_on = True
            else:
                electrolyzer_on = False
        
        return electrolyzer_on
'''


class FuelCell(object):
    """
    The fuel cell will calculate how much hydrogen is consumed to fulfill a certain power.

    Future developments:
    > H2O output
    > Degradation
    > Voltage and Current
    > Temperature profile
    > Available Fuel Cell energy back to the grid (Create a column just to know how much I'd have available)

    """

    def __init__(self, fuel_consumption: float, FC_efficiency: float):
        super().__init__()
        self.fuel_consumption = fuel_consumption  # g/Wh
        self.FC_efficiency = FC_efficiency

    def h2_consumption(self, P_needed: float) -> float:
        """ This method will define how much hydrogen is consumed by the fuel cell in kg.
            P_needed has to be entered in Wh.
            Check if the parameter defined for Fuel Consumption is at g/Wh
        """
        h2_cons = P_needed * self.fuel_consumption / 1000
        return h2_cons

    def electricity_generation(self, hydrogen_available: float) -> float:
        e_gen = hydrogen_available * 1000 / self.fuel_consumption
        return e_gen
