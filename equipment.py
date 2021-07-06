import math
# TODO 3. Make a forecast column: It will sum the next 672 rows (7 days * 24 hours * 4 quarter of hour) of solar
#  irradiation. Once it's reaching the end, make it use the data from January ("next year")
# TODO 5. Calculate the amount of hydrogen that will be produced in the next 30 days.
# TODO 6. Compressor consumption for hydrogen from the grid
# TODO 7. Electrolyzers can be turned off only 5 times a day


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

    def __init__(self, max_flow: float, max_power_consumption: float, avg_consumption: float):
        super().__init__()
        self.max_flow = max_flow
        self.max_power_consumption = max_power_consumption
        self.avg_consumption = avg_consumption

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
                 number_electrolyzer: int):
        super().__init__()
        self.electrical_consumption = electrical_consumption
        self.PE_efficiency = PE_efficiency
        self.installed_capacity = installed_capacity
        self.unit_capacity = unit_capacity
        self.number_electrolyzer = installed_capacity / unit_capacity

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

    def h2_pressure_out(self):
        pass
        # Dunno how to do this yet.

    def grid_hydrogen(self, H2_needed: float):
        """
        H2 Needed entry should be in kg
        For now there is no start-up time. Hydrogen is magically produced whenever needed. :)
        """
        H2_needed = H2_needed / 0.08988  # kg / (kg/Nm3)
        grid_consumption = H2_needed * self.electrical_consumption  # Nm3 * Wh/Nm3
        max_production = self.installed_capacity / 4  # Max Wh it can produce in 15'

        if grid_consumption > max_production:
            return max_production
        else:
            return grid_consumption

    def water_consumption (self, P_in: float):
        # It's saying this is static. Is it? Why? How?
        h2_mol = Electrolyzer.h2_production_kg(P_in)/2  # H2 in kmol
        h2o_mol = h2_mol
        h2o_wt = h2o_mol * 18  # in kg
        return h2o_wt


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
        self.fuel_consumption = fuel_consumption
        self.FC_efficiency = FC_efficiency

    def h2_consumption(self, P_needed: float) -> float:
        """ This method will define how much hydrogen is consumed by the fuel cell in kg.
            P_needed has to be entered in Wh.
            Check if the parameter defined for Fuel Consumption is at g/Wh
        """
        h2_cons = P_needed * self.fuel_consumption/1000
        return h2_cons
