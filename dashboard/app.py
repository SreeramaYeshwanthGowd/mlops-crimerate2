import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

# Set the title
app.title = "Real-Time Crime Data Analytics"

# Define API endpoints
API_ENDPOINT = "http://localhost:5000/predict"

# Mock data for initial display
def generate_mock_data():
    # Generate timestamps for the last 7 days
    now = datetime.now()
    timestamps = [now - timedelta(hours=i*6) for i in range(28)]
    timestamps.reverse()
    
    # Define locations and crime types
    locations = ["London", "Birmingham", "Manchester", "Chicago", "New York", "Los Angeles"]
    crime_types = ["Theft", "Burglary", "Assault", "Robbery", "Vehicle Crime", "Drugs"]
    
    data = []
    
    for location in locations:
        for crime_type in crime_types:
            for ts in timestamps:
                # Add some randomness to the count
                count = np.random.poisson(10)
                # Occasionally add anomalies
                if np.random.random() < 0.05:
                    count = count * np.random.randint(3, 6)
                    anomaly_score = np.random.uniform(0.7, 1.0)
                    is_anomaly = True
                else:
                    anomaly_score = np.random.uniform(0, 0.3)
                    is_anomaly = False
                
                data.append({
                    "location_name": location,
                    "crime_type": crime_type,
                    "timestamp": ts,
                    "incident_count": count,
                    "anomaly_score": anomaly_score,
                    "is_anomaly": is_anomaly
                })
    
    return pd.DataFrame(data)

# Generate mock data
df = generate_mock_data()

# App layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Real-Time Crime Data Analytics and Anomaly Detection", className="display-4"),
        html.P("Interactive dashboard for monitoring crime incidents and detecting anomalies", className="lead")
    ], className="jumbotron pt-4 pb-4"),
    
    # Main content
    html.Div([
        # Filters row
        html.Div([
            html.Div([
                html.Label("Location"),
                dcc.Dropdown(
                    id="location-dropdown",
                    options=[{"label": location, "value": location} for location in df["location_name"].unique()],
                    value=df["location_name"].unique()[0],
                    clearable=False
                )
            ], className="col-md-3"),
            
            html.Div([
                html.Label("Crime Type"),
                dcc.Dropdown(
                    id="crime-type-dropdown",
                    options=[{"label": crime, "value": crime} for crime in df["crime_type"].unique()],
                    value=df["crime_type"].unique()[0],
                    clearable=False
                )
            ], className="col-md-3"),
            
            html.Div([
                html.Label("Time Range"),
                dcc.Dropdown(
                    id="time-range-dropdown",
                    options=[
                        {"label": "Last 24 Hours", "value": "24h"},
                        {"label": "Last 3 Days", "value": "3d"},
                        {"label": "Last 7 Days", "value": "7d"}
                    ],
                    value="3d",
                    clearable=False
                )
            ], className="col-md-3"),
            
            html.Div([
                html.Label("Anomaly Threshold"),
                dcc.Slider(
                    id="anomaly-threshold-slider",
                    min=0,
                    max=1,
                    step=0.05,
                    value=0.7,
                    marks={i/10: str(i/10) for i in range(0, 11, 2)}
                )
            ], className="col-md-3"),
        ], className="row mb-4"),
        
        # Charts row
        html.Div([
            # Incident count chart
            html.Div([
                html.H3("Incident Count Over Time"),
                dcc.Graph(id="incident-chart")
            ], className="col-md-8"),
            
            # Anomaly metrics
            html.Div([
                html.H3("Anomaly Metrics"),
                html.Div(id="anomaly-metrics", className="p-3 bg-light rounded"),
                html.Hr(),
                html.H4("Recent Anomalies"),
                html.Div(id="recent-anomalies", className="p-3 bg-light rounded")
            ], className="col-md-4")
        ], className="row mb-4"),
        
        # Additional charts row
        html.Div([
            # Crime type distribution
            html.Div([
                html.H3("Crime Type Distribution"),
                dcc.Graph(id="crime-distribution")
            ], className="col-md-6"),
            
            # Anomaly score distribution
            html.Div([
                html.H3("Anomaly Score Distribution"),
                dcc.Graph(id="anomaly-distribution")
            ], className="col-md-6")
        ], className="row mb-4"),
        
        # Chatbot link (optional, commented out)
        # html.Div([
        #     html.Hr(),
        #     html.Div([
        #         html.A(
        #             html.Button("Chat with Project Bot", className="btn btn-primary btn-lg"),
        #             href="http://localhost:5005",
        #             target="_blank"
        #         )
        #     ], className="text-center")
        # ], className="row mt-4 mb-4")
    ], className="container"),
    
    # Update interval
    dcc.Interval(
        id="interval-component",
        interval=30*1000,  # in milliseconds (30 seconds)
        n_intervals=0
    )
])

# Callback to update charts and metrics
@app.callback(
    [
        Output("incident-chart", "figure"),
        Output("crime-distribution", "figure"),
        Output("anomaly-distribution", "figure"),
        Output("anomaly-metrics", "children"),
        Output("recent-anomalies", "children")
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("location-dropdown", "value"),
        Input("crime-type-dropdown", "value"),
        Input("time-range-dropdown", "value"),
        Input("anomaly-threshold-slider", "value")
    ]
)
def update_charts(n_intervals, location, crime_type, time_range, anomaly_threshold):
    # Filter data based on inputs
    filtered_df = df[(df["location_name"] == location) & (df["crime_type"] == crime_type)].copy()
    
    # Apply time range filter
    now = datetime.now()
    if time_range == "24h":
        filtered_df = filtered_df[filtered_df["timestamp"] > now - timedelta(hours=24)]
    elif time_range == "3d":
        filtered_df = filtered_df[filtered_df["timestamp"] > now - timedelta(days=3)]
    else:  # 7d
        filtered_df = filtered_df[filtered_df["timestamp"] > now - timedelta(days=7)]
    
    # Apply anomaly threshold
    filtered_df["is_anomaly"] = filtered_df["anomaly_score"] > anomaly_threshold
    
    # Create incident count chart
    incident_fig = px.line(
        filtered_df, 
        x="timestamp", 
        y="incident_count",
        title=f"{crime_type} Incidents in {location}"
    )
    
    # Add anomaly points
    anomalies = filtered_df[filtered_df["is_anomaly"]]
    if not anomalies.empty:
        incident_fig.add_scatter(
            x=anomalies["timestamp"],
            y=anomalies["incident_count"],
            mode="markers",
            marker=dict(color="red", size=10),
            name="Anomalies"
        )
    
    # Create crime type distribution
    all_location_df = df[df["location_name"] == location]
    crime_counts = all_location_df.groupby("crime_type")["incident_count"].sum().reset_index()
    crime_dist_fig = px.bar(
        crime_counts,
        x="crime_type",
        y="incident_count",
        title=f"Crime Type Distribution in {location}",
        color="crime_type"
    )
    
    # Create anomaly score distribution
    anomaly_dist_fig = px.histogram(
        filtered_df,
        x="anomaly_score",
        title="Anomaly Score Distribution",
        color_discrete_sequence=["blue"]
    )
    anomaly_dist_fig.add_vline(
        x=anomaly_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text="Threshold"
    )
    
    # Create anomaly metrics
    total_incidents = filtered_df["incident_count"].sum()
    anomaly_count = filtered_df[filtered_df["is_anomaly"]]["incident_count"].sum()
    anomaly_percentage = (anomaly_count / total_incidents * 100) if total_incidents > 0 else 0
    
    metrics_html = html.Div([
        html.P(f"Total Incidents: {total_incidents}"),
        html.P(f"Anomalous Incidents: {anomaly_count}"),
        html.P(f"Anomaly Percentage: {anomaly_percentage:.2f}%"),
        html.P(f"Current Threshold: {anomaly_threshold}")
    ])
    
    # Create recent anomalies table
    recent_anomalies = anomalies.sort_values("timestamp", ascending=False).head(5)
    
    if recent_anomalies.empty:
        recent_anomalies_html = html.P("No anomalies detected with current threshold.")
    else:
        rows = []
        for _, row in recent_anomalies.iterrows():
            rows.append(html.Tr([
                html.Td(row["timestamp"].strftime("%Y-%m-%d %H:%M")),
                html.Td(f"{row['incident_count']}"),
                html.Td(f"{row['anomaly_score']:.2f}")
            ]))
        
        recent_anomalies_html = html.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Timestamp"),
                        html.Th("Count"),
                        html.Th("Anomaly Score")
                    ])
                ),
                html.Tbody(rows)
            ],
            className="table table-striped table-sm"
        )
    
    # Return updated figures and components
    return incident_fig, crime_dist_fig, anomaly_dist_fig, metrics_html, recent_anomalies_html

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
