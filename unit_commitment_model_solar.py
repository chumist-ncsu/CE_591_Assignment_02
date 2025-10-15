from pyomo.environ import *
def define_model(shift_max_percent, shift_max_hours):
    # --- Model Definition ---
    model = AbstractModel()

    # --- Sets ---
    model.T = RangeSet(1, 24)              # Time periods (1 to 24 hours)
    model.G = Set()                        # Set of generators
    model.GS = Set()                       # Renewable Generators
    model.SD = Set()                       # Energy Storage Set
    model.B = Set()                        # Set of buses
    model.L = Set()                        # Set of transmission lines
    model.tpairs = Set(dimen=2, initialize= [(t1, t2) for t1 in model.T for t2 in model.T if 0 < abs(t1 - t2) <= shift_max_hours])

    # --- Parameters ---
    # Generator parameters
    model.Pmin = Param(model.G)            # Minimum generation limit for each generator
    model.Pmax = Param(model.G)            # Maximum generation limit for each generator
    model.Cgen = Param(model.G)            # Generation cost per MW
    model.Cstartup = Param(model.G)        # Startup cost
    model.Cshutdown = Param(model.G)       # Shutdown cost
    model.MUT = Param(model.G)             # Minimum up time
    model.MDT = Param(model.G)             # Minimum down time
    model.Rup = Param(model.G)             # Ramp up limit
    model.Rdown = Param(model.G)           # Ramp down limit
    model.y0 = Param(model.G)              # Initial on/off status
    model.GenBus = Param(model.G,within=Any)          # Bus each generator is connected to
    # model.Ccurtail = Param()        # Curtailment cost at each bus


    # Bus demand
    model.Demand = Param(model.B, model.T)  # Demand at each bus in each time period

    # Line limits (max flow)
    model.LineMax = Param(model.L)         # Maximum line capacity

    # Line incidence matrix (to describe line connections)
    model.LineFrom = Param(model.L,within=Any)        # Bus where each line originates
    model.LineTo = Param(model.L,within=Any)          # Bus where each line terminates

    #Renewable Generation Parameters
    model.Pmax_renewables = Param(model.GS)             # Max capacity of each renewable energy generator
    model.RenewablesProfile = Param(model.GS, model.T)  # Renewables generation profile (0-1) per generator per time
    model.GenBusRenewables = Param(model.GS,within=Any) # Bus each generator is connected to

    #Energy Storage Parameters
    model.Pmax_storage = Param(model.SD, within=NonNegativeReals)       # Maximum power of storage devices
    model.Storage_duration = Param(model.SD, within=NonNegativeReals)    # Duration of storage devices (hours of max discharge)
    model.Storage_efficiency = Param(model.SD, within=NonNegativeReals)  # Charging efficiency of storage devices
    model.StorageBus = Param(model.SD, within=model.B)                   # Storage units mapped to buses
    model.SOC_init = Param(model.SD, within=NonNegativeReals)            # Initial state of charge for storage

    # --- Decision Variables ---
    # Binary variables
    model.y = Var(model.G, model.T, domain=Binary)   # On/off status for each generator
    model.u = Var(model.G, model.T, domain=Binary)   # Startup decision for each generator
    model.v = Var(model.G, model.T, domain=Binary)   # Shutdown decision for each generator

    # Continuous variables
    model.P    = Var(model.G, model.T, domain=NonNegativeReals)       # Power output for each generator
    model.Flow = Var(model.L, model.T)                                # Power flow on transmission lines
    # model.Slack = Var(model.B, model.T, domain=NonNegativeReals)      # Curtail Demand
    model.P_renewables = Var(model.GS, model.T, within=NonNegativeReals)   # Renewable power output
    model.Charge = Var(model.SD, model.T, within=NonNegativeReals)    # Storage charge
    model.Discharge = Var(model.SD, model.T, within=NonNegativeReals) # Storage discharge
    model.SOC = Var(model.SD, model.T, within=NonNegativeReals)       # Storage State-of-charge
    model.shift = Var(model.B, model.tpairs, domain=NonNegativeReals)  # Demand shift at each bus in each time period

    # --- Objective Function ---
    def objective_rule(model):
        gen_cost = sum(model.Cgen[g] * model.P[g, t] for g in model.G for t in model.T)
        startup_cost = sum(model.Cstartup[g] * model.u[g, t] for g in model.G for t in model.T)
        shutdown_cost = sum(model.Cshutdown[g] * model.v[g, t] for g in model.G for t in model.T)
        # curtailment_cost = sum(model.Ccurtail * model.Slack[b, t] for b in model.B for t in model.T)
        # return gen_cost + startup_cost + shutdown_cost + curtailment_cost
        return gen_cost + startup_cost + shutdown_cost 
    model.TotalCost = Objective(rule=objective_rule, sense=minimize)

    # --- Constraints ---

    # Power balance constraints for each bus
    def relaxed_power_balance_rule(model, b, t):
        gen_renewables = sum(model.P_renewables[gs, t] for gs in model.GS if model.GenBusRenewables[gs] == b)
        gen_sum = sum(model.P[g, t] for g in model.G if model.GenBus[g] == b)
        discharge = sum(model.Discharge[i, t] for i in model.SD if model.StorageBus[i] == b)
        charge = sum(model.Charge[i, t] for i in model.SD if model.StorageBus[i] == b)
        line_flow_sum = (
            sum(model.Flow[l, t] for l in model.L if model.LineFrom[l] == b)
            - sum(model.Flow[l, t] for l in model.L if model.LineTo[l] == b)
        )

        shift_in = sum(model.shift[b, (k, t)] for k in model.T if k != t and abs(k - t) < shift_max_hours)
        shift_out = sum(model.shift[b, (t, k)] for k in model.T if k != t and abs(k - t) < shift_max_hours)
        net_shift = shift_in - shift_out
        # return gen_sum + gen_renewables + discharge - charge + line_flow_sum + model.Slack[b, t] == model.Demand[b, t]
        return gen_sum + gen_renewables + discharge - charge + line_flow_sum == model.Demand[b, t] + net_shift

    model.PowerBalance = Constraint(model.B, model.T, rule=relaxed_power_balance_rule)

    # Demand shift constraints
    def demand_shift_limit_rule(model, b, t):
        return sum(model.shift[b, (t, k)] for k in model.T if k != t and abs(k - t) < shift_max_hours) <= shift_max_percent * model.Demand[b, t]
    model.DemandShiftLimit = Constraint(model.B, model.T, rule=demand_shift_limit_rule)

    def demand_shift_hours_rule(model, b, t1, t2):
        if abs(t1 - t2) > shift_max_hours:
            return model.shift[b, (t1, t2)] == 0
        return Constraint.Skip
    model.DemandShiftHours = Constraint(model.B, model.tpairs, rule=demand_shift_hours_rule)

    # def net_shift_conservation_rule(model, b):
    #     return sum(model.shift[b, t1, t2] - model.shift[b, t2, t1] for t1 in model.T for t2 in model.T if t1 != t2) == 0
    # model.ShiftConservation = Constraint(model.B, rule=net_shift_conservation_rule)

    # Generator output limits
    # Lower bound: Generator must produce at least Pmin when it is on
    def gen_limits_min_rule(model, g, t):
        return model.P[g, t] >= model.Pmin[g] * model.y[g, t]
    model.GenLimitsMin = Constraint(model.G, model.T, rule=gen_limits_min_rule)

    # Upper bound: Generator must produce no more than Pmax when it is on
    def gen_limits_max_rule(model, g, t):
        return model.P[g, t] <= model.Pmax[g] * model.y[g, t]
    model.GenLimitsMax = Constraint(model.G, model.T, rule=gen_limits_max_rule)


    # Transmission line flow limits
    # Lower bound: Flow cannot be less than -LineMax
    def flow_limits_lower_rule(model, l, t):
        return model.Flow[l, t] >= -model.LineMax[l]
    model.FlowLimitsLower = Constraint(model.L, model.T, rule=flow_limits_lower_rule)

    # Upper bound: Flow cannot exceed LineMax
    def flow_limits_upper_rule(model, l, t):
        return model.Flow[l, t] <= model.LineMax[l]
    model.FlowLimitsUpper = Constraint(model.L, model.T, rule=flow_limits_upper_rule)


    # Startup and shutdown constraints
    def startup_shutdown_rule(model, g, t):
        if t == 1:
            return model.y[g, t] - model.y0[g] == model.u[g, t] - model.v[g, t]
        else:
            return model.y[g, t] - model.y[g, t-1] == model.u[g, t] - model.v[g, t]
    model.StartupShutdown = Constraint(model.G, model.T, rule=startup_shutdown_rule)

    # Minimum up time constraints
    def min_up_time_rule(model, g, t):
        if t < model.MUT[g]:
            return Constraint.Skip
        return sum(model.u[g, k] for k in range(t - int(model.MUT[g]) + 1, t + 1)) <= model.y[g, t]
    model.MinUpTime = Constraint(model.G, model.T, rule=min_up_time_rule)

    # Minimum down time constraints
    def min_down_time_rule(model, g, t):
        if t < model.MDT[g]:
            return Constraint.Skip
        return sum(model.v[g, k] for k in range(t - int(model.MDT[g]) + 1, t + 1)) <= 1 - model.y[g, t]
    model.MinDownTime = Constraint(model.G, model.T, rule=min_down_time_rule)

    # Ramp up limits
    def ramp_up_rule(model, g, t):
        if t == 1:
            return Constraint.Skip
        return model.P[g, t] - model.P[g, t-1] <= model.Rup[g]
    model.RampUp = Constraint(model.G, model.T, rule=ramp_up_rule)

    # Ramp down limits
    def ramp_down_rule(model, g, t):
        if t == 1:
            return Constraint.Skip
        return model.P[g, t-1] - model.P[g, t] <= model.Rdown[g]
    model.RampDown = Constraint(model.G, model.T, rule=ramp_down_rule)

    # Enforce initial conditions (optional if necessary)
    def initial_conditions_rule(model, g):
        if model.y0[g] == 1:
            return model.y[g, 1] == 1
        else:
            return model.y[g, 1] == 0
    model.InitialConditions = Constraint(model.G, rule=initial_conditions_rule)

    # Add Renewables generation constraints
    def renewables_generation_limits(model, gs, t):
        return model.P_renewables[gs, t] <= model.Pmax_renewables[gs] * model.RenewablesProfile[gs, t]/100
    model.RenewablesLimits = Constraint(model.GS, model.T, rule=renewables_generation_limits)

    # Add energy storage specific constraints

    # Constraints for storage charging, discharging, and SOC
    def soc_constraint_rule(model, s, t):
        if t == 1:
            return model.SOC[s, t] == model.SOC_init[s] + (model.Charge[s, t] * model.Storage_efficiency[s])/(model.Pmax_storage[s]*model.Storage_duration[s]) - model.Discharge[s, t]/(model.Storage_efficiency[s]*(model.Pmax_storage[s]*model.Storage_duration[s]))
        else:
            return model.SOC[s, t] == model.SOC[s, t-1] + (model.Charge[s, t] * model.Storage_efficiency[s])/(model.Pmax_storage[s]*model.Storage_duration[s]) - model.Discharge[s, t]/(model.Storage_efficiency[s]*(model.Pmax_storage[s]*model.Storage_duration[s]))
    model.SOC_constraint = Constraint(model.SD, model.T, rule=soc_constraint_rule)

    def storage_discharge_limit_rule(model, s, t):
        return model.Discharge[s, t] <= model.Pmax_storage[s]
    model.Storage_discharge_limit = Constraint(model.SD, model.T, rule=storage_discharge_limit_rule)

    def storage_charge_limit_rule(model, s, t):
        return model.Charge[s, t] <= model.Pmax_storage[s]
    model.Storage_charge_limit = Constraint(model.SD, model.T, rule=storage_charge_limit_rule)

    def soc_bounds_rule(model, s, t):
        return model.SOC[s, t] <= 1
    model.SOC_bounds = Constraint(model.SD, model.T, rule=soc_bounds_rule)


    # --- End of Model Definition ---
    return model