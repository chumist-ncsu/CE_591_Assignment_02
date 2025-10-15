import json
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "browser"

def plot_results(json_file):
    # Load the results from the JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)

    time_steps = list(range(len(next(iter(data['buses'].values()))['demand'])))

    # Plot generator power output
    fig_power = go.Figure()
    for g, g_data in data['generators'].items():
        fig_power.add_trace(go.Scatter(
            x=time_steps, y=g_data['power_output'],
            mode='lines+markers', name=f'Generator {g}',
            hovertemplate=f"Generator {g}<br>Hour: %{{x}}<br>Power Output: %{{y:.2f}} MW"
        ))

    fig_power.update_layout(
        title="Generator Power Output Over Time",
        xaxis_title="Time (Hours)",
        yaxis_title="Power Output (MW)",
        template="plotly_white"
    )
    fig_power.show()

    # Plot generator on/off status
    fig_status = go.Figure()
    for g, g_data in data['generators'].items():
        fig_status.add_trace(go.Scatter(
            x=time_steps, y=g_data['on_off_status'],
            mode='lines+markers', name=f'Generator {g}',
            line=dict(dash='dot'),
            hovertemplate=f"Generator {g}<br>Hour: %{{x}}<br>Status: %{{y}}"
        ))

    fig_status.update_layout(
        title="Generator On/Off Status Over Time",
        xaxis_title="Time (Hours)",
        yaxis_title="On/Off Status",
        template="plotly_white"
    )
    fig_status.show()

    # Plot transmission line flows
    fig_flow = go.Figure()
    for l, l_data in data['transmission_lines'].items():
        fig_flow.add_trace(go.Scatter(
            x=time_steps, y=l_data['flow'],
            mode='lines+markers', name=f'Line {l}',
            hovertemplate=f"Line {l}<br>Hour: %{{x}}<br>Flow: %{{y:.2f}} MW"
        ))

    fig_flow.update_layout(
        title="Transmission Line Flows Over Time",
        xaxis_title="Time (Hours)",
        yaxis_title="Flow (MW)",
        template="plotly_white"
    )
    fig_flow.show()

    # Plot demand vs shifted demand
    fig_demand = go.Figure()
    for b, b_data in data['buses'].items():
        fig_demand.add_trace(go.Scatter(
            x=time_steps, y=b_data['demand'],
            mode='lines+markers', name=f'Bus {b} Demand',
            hovertemplate=f"Bus {b}<br>Hour: %{{x}}<br>Demand: %{{y:.2f}} MW"
        ))
        fig_shifted_demand = [b_data['demand'][t] + b_data['shift'][t] for t in time_steps]
        fig_demand.add_trace(go.Scatter(
            x=time_steps, y=fig_shifted_demand,
            mode='lines+markers', name=f'Bus {b} Shifted Demand',
            line=dict(dash='dot'),
            hovertemplate=f"Bus {b}<br>Hour: %{{x}}<br>Shifted Demand: %{{y:.2f}} MW"
        )) 
    fig_demand.update_layout(
        title="Bus Demand and Shifted Demand Over Time",
        xaxis_title="Time (Hours)",
        yaxis_title="Demand (MW)",
        template="plotly_white"
    )
    fig_demand.show()

    # Plot total demand vs total shifted demand
    fig_total_demand = go.Figure()
    total_demand = [0]*len(time_steps)
    total_shifted_demand = [0]*len(time_steps)
    for b, b_data in data['buses'].items():
        for t in time_steps:
            total_demand[t] += b_data['demand'][t]
            total_shifted_demand[t] += b_data['demand'][t] + b_data['shift'][t]
    fig_total_demand.add_trace(go.Scatter(
        x=time_steps, y=total_demand,
        mode='lines+markers', name='Total Demand',
        hovertemplate="Hour: %{x}<br>Total Demand: %{y:.2f} MW"
    ))
    fig_total_demand.add_trace(go.Scatter(
        x=time_steps, y=total_shifted_demand,
        mode='lines+markers', name='Total Shifted Demand',
        line=dict(dash='dot'),
        hovertemplate="Hour: %{x}<br>Total Shifted Demand: %{y:.2f} MW"
    ))  
    fig_total_demand.update_layout(
        title="Total Demand and Total Shifted Demand Over Time",
        xaxis_title="Time (Hours)",
        yaxis_title="Demand (MW)",
        template="plotly_white"
    )
    fig_total_demand.show()

    # Plot Cost with and without Demand Shifting
    

