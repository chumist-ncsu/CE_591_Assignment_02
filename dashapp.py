import json
import networkx as nx  # NetworkX for generating spring layout
from dash import dcc, html
from dash.dependencies import Input, Output
import dash
import os
import signal

# Helper function to get a color based on a value range
def get_color(value, min_val, max_val, cmap_name):
    norm_value = (value - min_val) / (max_val - min_val) if max_val != min_val else 0
    return {
        'Blues': f'rgba(0, 0, 255, {norm_value})',  # Blue scale
        'Reds': f'rgba(255, 0, 0, {norm_value})',  # Red scale
        'Greens': f'rgba(100, 255, 0, {norm_value})',  # Green scale
        'Yellows': f'rgba(255, 255, 0, {norm_value})',  # Yellow for renewables
        'Grays': f'rgba(200, 200, 200, 1)',  # Light Gray for zero values
    }[cmap_name]

# Create a fixed layout for the nodes using NetworkX spring layout
def create_fixed_positions(json_data):
    G = nx.Graph()

    # Add buses as nodes
    for bus in json_data['buses']:
        G.add_node(bus)

    # Add generators and connect them to buses
    for generator, gen_data in json_data['generators'].items():
        G.add_node(generator)
        G.add_edge(generator, gen_data['connected_bus'])

    # Add renewable generators and connect them to buses
    for renewable, ren_data in json_data['renewables_generators'].items():
        G.add_node(renewable)
        G.add_edge(renewable, ren_data['connected_bus'])

    # Add storage and connect them to buses
    if 'storage' in json_data:
        for storage, storage_data in json_data['storage'].items():
            G.add_node(storage)
            G.add_edge(storage, storage_data['connected_bus'])

    # Add transmission lines between buses
    for line_data in json_data['transmission_lines'].values():
        G.add_edge(line_data['from_bus'], line_data['to_bus'])

    # Use NetworkX spring layout to generate positions
    pos = nx.spring_layout(G, seed=42)  # Fixed seed for consistent layout

    fixed_positions = {}
    for node, (x, y) in pos.items():
        fixed_positions[node] = {'x': x * 1000, 'y': y * 1000}  # Scaling for better visualization

    return fixed_positions

# Function to process the JSON data and return nodes and edges
def process_network_data(json_data, selected_hour, fixed_positions, selected_buses=None):
    nodes = []
    edges = []

    is_average = selected_hour == 'average'

    # If no buses are selected, show the full network
    if not selected_buses:
        selected_buses = list(json_data['buses'].keys())  # Default to all buses

    # Compute the max values for scaling the color intensity
    max_demand = max(
        max(sum(bus['demand']) / len(bus['demand']) for bus in json_data['buses'].values()) if is_average
        else max(bus['demand'][int(selected_hour)] for bus in json_data['buses'].values()), 1
    )
    max_generation = max(
        max(sum(gen['power_output']) / len(gen['power_output']) for gen in json_data['generators'].values()) if is_average
        else max(gen['power_output'][int(selected_hour)] for gen in json_data['generators'].values()), 1
    )
    max_renewable = max(
        max(sum(ren['power_output']) / len(ren['power_output']) for ren in json_data['renewables_generators'].values()) if is_average
        else max(ren['power_output'][int(selected_hour)] for ren in json_data['renewables_generators'].values()), 1
    )
    max_soc = max(
        max(sum(storage['SoC']) / len(storage['SoC']) for storage in json_data['storage'].values()) if is_average
        else max(storage['SoC'][int(selected_hour)] for storage in json_data['storage'].values()), 1
    )

    # Filter and add buses as nodes
    for bus, bus_data in json_data['buses'].items():
        if bus in selected_buses:
            demand = (
                sum(bus_data['demand']) / len(bus_data['demand'])
                if is_average
                else bus_data['demand'][int(selected_hour)]
            )
            curtailment = (
                sum(bus_data['curtailment']) / len(bus_data['curtailment'])
                if is_average
                else bus_data['curtailment'][int(selected_hour)]
            )

            hover_text = (
                f"Bus {bus}<br>Demand: {demand:.2f} MW<br>"
                f"Curtailment: {curtailment:.2f} MW"
            )

            nodes.append({
                "id": bus,
                "label": f"{bus}",
                "color": get_color(demand, 0, max_demand, 'Reds' if demand > 0 else 'Grays'),
                "borderWidth": 3,
                "borderColor": "red",
                "title": hover_text,
                "x": fixed_positions[bus]['x'],
                "y": fixed_positions[bus]['y'],
            })

    # Filter and add generators as nodes
    for generator, gen_data in json_data['generators'].items():
        if gen_data['connected_bus'] in selected_buses:
            power_output = (
                sum(gen_data['power_output']) / len(gen_data['power_output'])
                if is_average
                else gen_data['power_output'][int(selected_hour)]
            )
            hover_text = f"Generator {generator}<br>Power Output: {power_output:.2f} MW"

            nodes.append({
                "id": generator,
                "label": f"{generator}",
                "color": get_color(power_output, 0, max_generation, 'Blues' if power_output > 0 else 'Grays'),
                "borderWidth": 3,
                "borderColor": "blue",
                "title": hover_text,
                "x": fixed_positions[generator]['x'],
                "y": fixed_positions[generator]['y'],
            })

            edges.append({
                "from": generator,
                "to": gen_data['connected_bus'],
                "arrows": {"to": True},
                "color": {"color": "gray"}
            })

    # Filter and add renewable generators as nodes
    for renewable, ren_data in json_data['renewables_generators'].items():
        if ren_data['connected_bus'] in selected_buses:
            power_output = (
                sum(ren_data['power_output']) / len(ren_data['power_output'])
                if is_average
                else ren_data['power_output'][int(selected_hour)]
            )
            hover_text = f"Renewable {renewable}<br>Power Output: {power_output:.2f} MW"

            nodes.append({
                "id": renewable,
                "label": f"{renewable}",
                "color": get_color(power_output, 0, max_renewable, 'Yellows' if power_output > 0 else 'Grays'),
                "borderWidth": 3,
                "borderColor": "yellow",
                "title": hover_text,
                "x": fixed_positions[renewable]['x'],
                "y": fixed_positions[renewable]['y'],
            })

            edges.append({
                "from": renewable,
                "to": ren_data['connected_bus'],
                "arrows": {"to": True},
                "color": {"color": "gray"}
            })

    # Filter and add storage nodes
    if 'storage' in json_data:
        for storage, storage_data in json_data['storage'].items():
            if storage_data['connected_bus'] in selected_buses:
                soc = (
                    sum(storage_data['SoC']) / len(storage_data['SoC'])
                    if is_average
                    else storage_data['SoC'][int(selected_hour)]
                )
                charge_discharge = (
                    sum(storage_data['charge_discharge']) / len(storage_data['charge_discharge'])
                    if is_average
                    else storage_data['charge_discharge'][int(selected_hour)]
                )
                hover_text = f"Storage {storage}<br>State of Charge: {soc:.2f}%<br>Charge/Discharge: {charge_discharge:.2f} MW"

                nodes.append({
                    "id": storage,
                    "label": f"{storage}",
                    "color": get_color(soc, 0, max_soc, 'Greens' if soc > 0 else 'Grays'),
                    "borderWidth": 3,
                    "borderColor": "green",
                    "shape": "square",
                    "title": hover_text,
                    "x": fixed_positions[storage]['x'],
                    "y": fixed_positions[storage]['y'],
                })
                edges.append({
                    "from": storage if charge_discharge > 0 else storage_data['connected_bus'],
                    "to": storage_data['connected_bus'] if charge_discharge > 0 else storage,
                    "arrows": {"to": True},
                    "color": {"color": "gray"}
                })

    # Filter and add transmission lines as edges between selected buses
    for line, line_data in json_data['transmission_lines'].items():
        if line_data['from_bus'] in selected_buses or line_data['to_bus'] in selected_buses:
            flow = (
                sum(line_data['flow']) / len(line_data['flow'])
                if is_average
                else line_data['flow'][int(selected_hour)]
            )
            bus_from = line_data['from_bus']
            bus_to = line_data['to_bus']

            if flow > 0:
                edges.append({
                    "from": bus_from,
                    "to": bus_to,
                    "arrows": {"to": True},
                    "color": {"color": "gray"},
                    "title": f"Flow: {flow:.2f} MW from {bus_from} to {bus_to}"
                })
            else:
                edges.append({
                    "from": bus_to,
                    "to": bus_from,
                    "arrows": {"to": True},
                    "color": {"color": "gray"},
                    "title": f"Flow: {abs(flow):.2f} MW from {bus_to} to {bus_from}"
                })

    return nodes, edges

# Create the Dash app
app = dash.Dash(__name__)

# Load the JSON data
with open('unit_commitment_results.json', 'r') as f:
    network_data = json.load(f)

# Generate fixed positions for the network nodes using NetworkX spring layout
fixed_positions = create_fixed_positions(network_data)

# Dynamically get the number of hours from the JSON file (based on the flow or demand)
num_hours = len(next(iter(network_data['transmission_lines'].values()))['flow'])

# Layout of the Dash app
app.layout = html.Div([
    html.H1('Interactive Power Network'),
    dcc.Dropdown(
        id='bus-dropdown',
        options=[{'label': f'Bus {bus}', 'value': bus} for bus in network_data['buses'].keys()],
        multi=True,
        placeholder="Select buses to filter",
    ),
    dcc.Dropdown(
        id='hour-dropdown',
        options=[{'label': f'Hour {i}', 'value': i} for i in range(num_hours)] + [{'label': 'Average', 'value': 'average'}],
        value='average',
        clearable=False
    ),
    html.Iframe(id='vis-network', width='100%', height='800', srcDoc=''),  # Empty srcDoc for now
    dcc.Store(id='network-data'),  # Store network data here
    #html.Button('Exit', id='exit-button')  # Add Exit button
    html.Button('Exit', id='exit-button', style={
    'position': 'fixed',
    'bottom': '45px',
    'right': '120px',
    'padding': '10px 20px',
    'background-color': '#f44336',  # Red background for emphasis
    'color': 'white',
    'border': 'none',
    'border-radius': '5px',
    'cursor': 'pointer',
    'font-size': '16px'
})
])

# Callback to process the network data and store it
@app.callback(
    Output('network-data', 'data'),
    [Input('hour-dropdown', 'value'),
     Input('bus-dropdown', 'value')]
)
def update_network_data(selected_hour, selected_buses):
    nodes, edges = process_network_data(network_data, selected_hour, fixed_positions, selected_buses)
    return {'nodes': nodes, 'edges': edges}

# Callback to update the iframe's content with JavaScript and the network data
@app.callback(
    Output('vis-network', 'srcDoc'),
    Input('network-data', 'data')
)
def update_iframe(network_data):
    # Generate the HTML content that will be injected into the iframe
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
      <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css">
      <style type="text/css">
        #mynetwork {{
          width: 100%;
          height: 800px;
          border: 1px solid lightgray;
        }}
      </style>
    </head>
    <body>
    <div id="mynetwork"></div>
    <script type="text/javascript">
      var nodes = new vis.DataSet({json.dumps(network_data['nodes'])});
      var edges = new vis.DataSet({json.dumps(network_data['edges'])});

      var container = document.getElementById('mynetwork');
      var data = {{
        nodes: nodes,
        edges: edges
      }};
      var options = {{
        nodes: {{
          borderWidth: 2,
          borderWidthSelected: 2,
          borderColor: 'black',
          shape: 'dot',
          font: {{ color: '#000', size: 14 }},
          scaling: {{
            label: true
          }},
          size: 15
        }},
        edges: {{
          arrows: {{
            to: {{enabled: true, scaleFactor: 1}}
          }},
          color: {{
            color: 'gray'
          }},
          smooth: {{
            enabled: true
          }}
        }},
        interaction: {{
          dragNodes: true,
          hover: true,
          zoomView: true,
          dragView: true
        }},
        physics: {{
          enabled: false  // Disable physics for fixed positions
        }}
      }};
      var network = new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    return html_content

# Callback to handle the exit button
@app.callback(
    Output('exit-button', 'n_clicks'),
    Input('exit-button', 'n_clicks')
)
def exit_app(n_clicks):
    if n_clicks is not None:
        os.kill(os.getpid(), signal.SIGTERM)  # Terminate the process

if __name__ == '__main__':
    app.run_server(debug=True)
