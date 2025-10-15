import json
from pyomo.environ import *
from pyomo.opt import SolverFactory
from unit_commitment_model_solar import define_model

def solve_unit_commitment(data_file, 
                          output_json="unit_commitment_results.json", 
                          shift_max_percent=0.2,    
                          shift_max_hours=4):
    
    print("Solving Unit Commitment Problem with Solar and Storage...")
    # Load the model and data
    instance = define_model(shift_max_percent, shift_max_hours).create_instance(data_file)

    # Solve the optimization problem
    solver = SolverFactory('glpk')
    results = solver.solve(instance, tee=True)

    # Prepare results to be stored in a JSON format
    results_data = {
        "total_cost": value(instance.TotalCost),
        "generators": {},
        "buses": {},
        "transmission_lines": {},
        "renewables_generators": {},
        "storage": {}
    }

    # Store generator results
    for g in instance.G:
        results_data["generators"][str(g)] = {
            "power_output": [value(instance.P[g, t]) for t in instance.T],
            "on_off_status": [value(instance.y[g, t]) for t in instance.T],
            "startup": [value(instance.u[g, t]) for t in instance.T],
            "shutdown": [value(instance.v[g, t]) for t in instance.T],
            "max_capacity": value(instance.Pmax[g]),
            "connected_bus": str(instance.GenBus[g])
        }

    # Store bus results (demand, curtailment)
    for b in instance.B:
        results_data["buses"][str(b)] = {
            "demand": [value(instance.Demand[b, t]) for t in instance.T],
            # "curtailment": [value(instance.Slack[b, t]) for t in instance.T]
            "shift" : [sum(value(instance.shift[b, k, t]) for k in instance.T if k != t and abs(k - t) < shift_max_hours) - \
                       sum(value(instance.shift[b, t, k]) for k in instance.T if k != t and abs(k - t) < shift_max_hours)
                       for t in instance.T]
        }

    # Store transmission line flow results
    for l in instance.L:
        results_data["transmission_lines"][str(l)] = {
            "flow": [value(instance.Flow[l, t]) for t in instance.T],
            "from_bus": str(instance.LineFrom[l]),
            "to_bus": str(instance.LineTo[l])
        }

    for g in instance.GS:
        results_data["renewables_generators"][str(g)] = {
            "power_output": [value(instance.P_renewables[g, t]) for t in instance.T],
            "max_capacity": value(instance.Pmax_renewables[g]),
            "connected_bus": str(instance.GenBusRenewables[g])
        }

    for g in instance.SD:
        results_data["storage"][str(g)] = {
            "charge_discharge": [value(instance.Charge[g, t]) - value(instance.Discharge[g, t]) for t in instance.T],
            "charge": [value(instance.Charge[g, t]) for t in instance.T],
            "discharge": [value(instance.Discharge[g, t]) for t in instance.T],
            "SoC": [value(instance.SOC[g, t]) for t in instance.T],
            "connected_bus": str(instance.StorageBus[g])
        }

    # Save the results to a JSON file
    with open(output_json, "w") as f:
        json.dump(results_data, f, indent=4)

    print(f"Optimization results saved to {output_json}")

