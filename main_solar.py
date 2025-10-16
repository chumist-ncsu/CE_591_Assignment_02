import subprocess
from solve_uc_solar import solve_unit_commitment
from plot_results_solar import plot_results

# Step 1: Solve the optimization problem and store results in JSON
solve_unit_commitment(
    'unit_commitment_data_solar.dat',
    'unit_commitment_results.json',
    shift_max_percent=.2,
    shift_max_hours=2
)

# Step 2: Plot the results using the generated JSON file
plot_results('unit_commitment_results.json')

# Step 3: Visualize the network using the same JSON file

# Option 01 - Static Network
#visualize_network('unit_commitment_results.json')

# Option 02 - Dynamic Network
def run_dash_app():
    # Run the Dash app located in dashapp.py using subprocess
    subprocess.run(["python3", "dashapp.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Choose which option to execute
#option = input("Select Option (1: Static Network, 2: Dynamic Network): ")
option = "2"

if option == "1":
    print("Invalid option. Please select 2.")
    #visualize_network('unit_commitment_results.json')
elif option == "2":
    run_dash_app()
else:
    print("Invalid option. Please select 1 or 2.")



