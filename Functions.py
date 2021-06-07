def compressor(h2_in, max_flow, max_power_consumption):
    """ Calculates the power consumption of a compressor for a 15 minutes interval, according to its rated maximum
    mass flow in [kg/day] and maximum power consumption in [W/kg]. The result will be a power consumption in
    Watts [Wh/kg].

    h2_in = [kg/15']
    max_flow = [kg/day]
    max_power_consumption = [Wh/kg]

    result = [Wh]

    """

    if h2_in > 0:
        compressor_on = True
        h2_day = h2_in * 4 * 24  # From kg/15' to kg/day
        utilization = h2_day / max_flow
        compressor_power = (utilization * max_power_consumption/4) * h2_in  # the /4 is for Wh in 15'
        return compressor_power
    else:
        compressor_power = 0
        return compressor_power


def electrolyzer (P_in, EL_consumption, b):
    # I won't do the calculation of PV-load, as this will be a system configuration
    """
    This function calculates the amount of hydrogen produced both in kg and in Nm3.
    It has an option to return the output pressure as well.

    PS.: for now I don't know how to make it output different stuff.

    """

    H2_change = P_in / EL_consumption * 0.08988