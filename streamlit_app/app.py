import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json
import time
from collections import defaultdict

# Configuration
API_BASE_URL = "https://7sevawq9u4.execute-api.ap-south-1.amazonaws.com/prod"
HEADERS = {"Content-Type": "application/json"}

# Color schemes
COLORS = {
    'severity': {'LOW': '#10B981', 'MEDIUM': '#F59E0B', 'HIGH': '#EF4444'},
    'status': {'OPEN': '#3B82F6', 'IN_PROGRESS': '#F59E0B', 'RESOLVED': '#10B981'}
}

def get_api_key() -> str:
    """Return the API key from Streamlit secrets."""
    try:
        api_key = st.secrets["API_KEY"]
    except Exception:
        api_key = ""
    return api_key

def make_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
    """Make an HTTP request to the API with improved error handling and logging."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    # Add API key if available
    api_key = get_api_key()
    if api_key:
        headers["x-api-key"] = api_key
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, params=params)
        elif method.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=headers, params=params)
        else:
            return {"error": True, "message": f"Unsupported HTTP method: {method}"}
            
        # Debug log
        st.write(f"🔧 API Request: {method} {url}")
        st.write(f"🔧 Status Code: {response.status_code}")
        
        if response.status_code >= 400:
            error_msg = f"API Error ({response.status_code}): {response.text}"
            st.error(f"❌ {error_msg}")
            return {"error": True, "message": error_msg, "status_code": response.status_code}
            
        try:
            return response.json()
        except ValueError:
            return response.text
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        st.error(f"❌ {error_msg}")
        return {"error": True, "message": error_msg}
    """Make an API request with the given method, endpoint, and data."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        **HEADERS,
        "x-api-key": get_api_key(),
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        else:
            return {"error": f"Unsupported HTTP method: {method}"}

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"Error making {method} request to {endpoint}: {str(e)}"}

def check_health() -> Dict:
    """Check the health of the API."""
    return make_request("GET", "/health")

def create_incident(title: str, description: str, severity: str, tags: List[str] = None, reported_by: str = "streamlit-app") -> Dict:
    """Create a new incident."""
    try:
        if tags is None:
            tags = []
        
        # Convert severity to lowercase to match API requirements
        severity = severity.lower()
        
        # Validate severity is one of the allowed values
        allowed_severities = ["critical", "high", "medium", "low"]
        if severity not in allowed_severities:
            return {"error": f"Invalid severity. Must be one of: {', '.join(allowed_severities)}"}
            
        # Prepare the incident data with proper types
        data = {
            "title": str(title).strip(),
            "description": str(description).strip(),
            "severity": str(severity).lower(),
            "reported_by": str(reported_by).strip(),
            "tags": [str(tag).strip() for tag in tags] if tags else []
        }
        
        # Make the API request
        response = make_request("POST", "/incidents", data=data)
        
        # Log the response for debugging
        print(f"API Response: {response}")
        
        # If there's an error in the response, return it
        if isinstance(response, dict) and "error" in response:
            return response
            
        return response
        
    except Exception as e:
        return {"error": f"Failed to create incident: {str(e)}"}

def list_incidents() -> List[Dict]:
    """List all incidents from the API."""
    try:
        st.write("🔍 Making API request to /incidents...")
        result = make_request("GET", "/incidents")
        
        if result is None:
            st.error("❌ Failed to fetch incidents: No response from API")
            return []
            
        if not isinstance(result, dict):
            st.error(f"❌ Unexpected API response format: {type(result)}")
            return []
            
        if 'items' in result and isinstance(result['items'], list):
            st.write(f"✅ Successfully fetched {len(result['items'])} incidents")
            return result['items']
        elif 'error' in result:
            st.error(f"❌ API Error: {result.get('message', 'Unknown error')}")
        else:
            st.error(f"❌ Unexpected response format: {result}")
            
    except Exception as e:
        st.error(f"❌ Error fetching incidents: {str(e)}")
        
    return []

def update_incident_status(incident_id: str, status: str) -> Dict:
    """Update the status of an incident."""
    data = {"status": status.upper()}
    return make_request("PATCH", f"/incidents/{incident_id}", data=data)

def normalize_status(status: str) -> str:
    """Normalize status values to handle different formats."""
    if not status:
        return 'UNKNOWN'
    status = str(status).strip().upper()
    # Handle different possible status formats
    if status in ['OPEN']:
        return 'OPEN'
    elif status in ['IN_PROGRESS', 'IN PROGRESS', 'INPROGRESS']:
        return 'IN_PROGRESS'
    elif status in ['RESOLVED', 'CLOSED', 'DONE']:
        return 'RESOLVED'
    return status

def create_summary_metrics(incidents: List[Dict]) -> None:
    """Create summary metrics cards with status summary."""
    if not incidents:
        st.warning("No incident data available")
        return
    
    # Normalize all status values
    for incident in incidents:
        incident['normalized_status'] = normalize_status(incident.get('status', 'UNKNOWN'))
    
    # Count statuses after normalization
    status_counts = {}
    for incident in incidents:
        status = incident['normalized_status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Display status summary
    st.write("### 📊 Status Summary")
    for status, count in sorted(status_counts.items()):
        display_name = status.replace('_', ' ').title()
        st.write(f"- {display_name}: {count} incidents")
    
    # Calculate metrics using normalized status
    total_incidents = len(incidents)
    open_incidents = len([i for i in incidents if i['normalized_status'] == 'OPEN'])
    in_progress_incidents = len([i for i in incidents if i['normalized_status'] == 'IN_PROGRESS'])
    resolved_incidents = len([i for i in incidents if i['normalized_status'] == 'RESOLVED'])
    
    # Debug: Show sample of status values
    st.write("### 🔍 Sample Status Values")
    sample = [f"{i.get('id', '?')}: {i.get('status', 'MISSING')} -> {i['normalized_status']}" 
             for i in incidents[:5]]
    st.write("\n".join(sample))
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Total Incidents
    with col1:
        st.metric("Total Incidents", total_incidents)
    
    # Open Incidents
    with col2:
        st.metric("Open", open_incidents, 
                 delta=f"{int((open_incidents/total_incidents)*100)}% of total" if total_incidents > 0 else None)
    
    # In Progress
    with col3:
        st.metric("In Progress", in_progress_incidents,
                 delta=f"{int((in_progress_incidents/total_incidents)*100)}% of total" if total_incidents > 0 else None)
    
    # Resolved
    with col4:
        st.metric("Resolved", resolved_incidents,
                 delta=f"{int((resolved_incidents/total_incidents)*100)}% of total" if total_incidents > 0 else None)

def create_severity_pie_chart(incidents: List[Dict]) -> None:
    """Create a pie chart of incident severities."""
    if not incidents:
        st.warning("No data available for severity distribution")
        return
        
    severity_counts = defaultdict(int)
    for incident in incidents:
        severity = incident.get('severity', 'UNKNOWN').upper()
        severity_counts[severity] += 1
    
    if not severity_counts:
        return
        
    df = pd.DataFrame({
        'Severity': list(severity_counts.keys()),
        'Count': list(severity_counts.values())
    })
    
    # Sort by count for consistent ordering
    df = df.sort_values('Count', ascending=False)
    
    # Create pie chart
    fig = px.pie(
        df, 
        values='Count', 
        names='Severity',
        title='Incidents by Severity',
        color='Severity',
        color_discrete_map=COLORS['severity'],
        hole=0.4
    )
    
    # Update layout for better appearance
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_status_bar_chart(incidents: List[Dict]) -> None:
    """Create a bar chart of incident statuses."""
    if not incidents:
        st.warning("No data available for status distribution")
        return
        
    status_counts = defaultdict(int)
    for incident in incidents:
        status = incident.get('status', 'UNKNOWN').upper()
        status_counts[status] += 1
    
    if not status_counts:
        return
        
    df = pd.DataFrame({
        'Status': [s.replace('_', ' ').title() for s in status_counts.keys()],
        'Count': list(status_counts.values())
    })
    
    # Create bar chart
    fig = px.bar(
        df, 
        x='Status', 
        y='Count',
        title='Incidents by Status',
        color='Status',
        color_discrete_map={
            'Open': COLORS['status']['OPEN'],
            'In Progress': COLORS['status']['IN_PROGRESS'],
            'Resolved': COLORS['status']['RESOLVED']
        }
    )
    
    # Update layout for better appearance
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Count",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_timeline_chart(incidents: List[Dict]) -> None:
    """Create a timeline of incidents."""
    if not incidents:
        st.warning("No data available for timeline")
        return
    
    # Prepare data
    timeline_data = []
    for incident in incidents:
        if 'created_at' in incident:
            try:
                created_at = datetime.fromisoformat(incident['created_at'].replace('Z', '+00:00'))
                timeline_data.append({
                    'Date': created_at.date(),
                    'Severity': incident.get('severity', 'UNKNOWN').upper(),
                    'Status': incident.get('status', 'UNKNOWN').upper(),
                    'Title': incident.get('title', 'No Title'),
                    'ID': incident.get('incident_id', 'N/A')
                })
            except (ValueError, AttributeError):
                continue
    
    if not timeline_data:
        st.warning("No valid date data available for timeline")
        return
    
    df = pd.DataFrame(timeline_data)
    
    # Group by date and severity
    df_grouped = df.groupby(['Date', 'Severity']).size().reset_index(name='Count')
    
    # Create line chart
    fig = px.line(
        df_grouped, 
        x='Date', 
        y='Count',
        color='Severity',
        title='Incidents Over Time',
        color_discrete_map=COLORS['severity'],
        markers=True
    )
    
    # Add range selector
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(step="all")
            ])
        )
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Incidents",
        legend_title="Severity",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_incident_table(incidents: List[Dict]) -> None:
    """Create an interactive data table of incidents."""
    if not incidents:
        st.info("No incidents found.")
        return
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(incidents)
    
    # Format dates
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Reorder and select columns
    columns_to_show = ['incident_id', 'title', 'severity', 'status', 'created_at']
    columns_to_show = [col for col in columns_to_show if col in df.columns]
    
    # Create status and severity badges
    def format_status(status):
        status_lower = status.lower()
        color = {
            'open': '#3B82F6',
            'in_progress': '#F59E0B',
            'resolved': '#10B981'
        }.get(status_lower, '#6B7280')
        return f'<span style="color: white; background-color: {color}; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{status.replace("_", " ").title()}</span>'
    
    def format_severity(severity):
        severity_lower = severity.lower()
        color = {
            'low': '#10B981',
            'medium': '#F59E0B',
            'high': '#EF4444'
        }.get(severity_lower, '#6B7280')
        return f'<span style="color: white; background-color: {color}; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{severity.title()}</span>'
    
    # Apply formatting
    if 'status' in df.columns:
        df['status'] = df['status'].apply(format_status)
    if 'severity' in df.columns:
        df['severity'] = df['severity'].apply(format_severity)
    
    # Display the table
    st.write(
        df[columns_to_show].to_html(escape=False, index=False), 
        unsafe_allow_html=True
    )

def show_incident_list(incidents):
    """Show the list of incidents."""
    st.subheader("All Incidents")
    
    if not incidents:
        st.info("No incidents found.")
        return
    
    # Display incidents
    create_incident_table(incidents)

def show_create_incident_form():
    """Show the form to create a new incident."""
    st.subheader("Create New Incident")
    
    with st.form("create_incident_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Title*", placeholder="Brief title of the incident")
            reported_by = st.text_input(
                "Your Name/ID*",
                placeholder="Your name or identifier",
                help="Who is reporting this incident?"
            )
        
        with col2:
            severity = st.selectbox(
                "Severity*",
                ["Critical", "High", "Medium", "Low"],
                index=1,
                help="Select the severity level of the incident"
            )
            tags = st.text_input("Tags (comma-separated)", placeholder="e.g., server,api,database")
        
        description = st.text_area(
            "Description*",
            placeholder="Detailed description of the incident...",
            height=150
        )

        submit_button = st.form_submit_button(
            "🚨 Create Incident",
            type="primary",
            use_container_width=True
        )

        if submit_button:
            if not all([title, description, reported_by]):
                missing = []
                if not title:
                    missing.append("Title")
                if not description:
                    missing.append("Description")
                if not reported_by:
                    missing.append("Your Name/ID")
                st.error(f"❌ Please fill in all required fields: {', '.join(missing)}")
            else:
                with st.spinner("Creating incident..."):
                    try:
                        # Convert tags string to list
                        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                        
                        # Call the API to create the incident
                        result = create_incident(
                            title=title,
                            description=description,
                            severity=severity.lower(),
                            tags=tag_list,
                            reported_by=reported_by.strip()
                        )
                        
                        # Handle the response
                        if isinstance(result, dict):
                            if "error" in result:
                                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                                if "message" in result:
                                    st.error(f"Details: {result['message']}")
                            else:
                                st.success("✅ Incident created successfully!")
                                st.balloons()
                                # Show the created incident details
                                st.json(result)
                                # Clear the form after a short delay
                                time.sleep(2)
                                st.session_state.page = "📋 List Incidents"
                                st.rerun()
                        else:
                            st.error("❌ Unexpected response from the server")
                            
                    except Exception as e:
                        error_msg = f"❌ Failed to create incident: {str(e)}"
                        st.error(error_msg)
                        print(f"Error: {error_msg}")
                        st.error("Please check your API connection and try again.")
                        
                        # Log the full traceback for debugging
                        import traceback
                        traceback.print_exc()

def main():
    # Initialize session state for page navigation
    if 'page' not in st.session_state:
        st.session_state.page = "📋 List Incidents"
    
    st.set_page_config(
        page_title="Incident Management",
        page_icon="🚨",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Add sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        if st.button("📋 List Incidents", use_container_width=True):
            st.session_state.page = "📋 List Incidents"
        if st.button("➕ Create Incident", use_container_width=True):
            st.session_state.page = "➕ Create Incident"

    # Custom CSS for better styling
    st.markdown("""
    <style>
        /* Set default text color to white for all elements */
        * {
            color: white !important;
        }
        
        /* Input fields */
        .stTextInput input, 
        .stTextArea textarea, 
        .stSelectbox select,
        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stNumberInput input,
        .stNumberInput label,
        .stDateInput input,
        .stDateInput label,
        .stTimeInput input,
        .stTimeInput label,
        .stMultiSelect label,
        .stRadio label,
        .stCheckbox label,
        .stSlider label,
        .stButton button,
        .stMarkdown,
        .stAlert,
        .stDataFrame,
        .stTable,
        .stProgress,
        .stSpinner,
        .stExpander,
        .stTabs {
            color: white !important;
        }
        
        /* Input field text color */
        .stTextInput input, 
        .stTextArea textarea, 
        .stSelectbox select,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input {
            color: white !important;
            background-color: #1E1E1E !important;
            border-color: #555 !important;
        }
        
        /* Placeholder text color */
        ::placeholder {
            color: #aaa !important;
            opacity: 1;
        }
        
        /* Main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            background-color: #0E1117;
        }
        
        /* Sidebar */
        .css-1d391kg {
            background-color: #0E1117;
            border-right: 1px solid #333;
        }
        
        /* Metrics */
        .stMetric {
            background-color: #1E1E1E !important;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: white !important;
        }
        
        .stMetric label {
            color: #aaa !important;
            font-size: 0.9rem;
        }
        
        .stMetric .value {
            font-size: 1.5rem;
            font-weight: 600;
            color: white !important;
    </style>
    """, unsafe_allow_html=True)
    
    # Get all incidents once
    st.write("🔍 Fetching incidents from API...")
    all_incidents = list_incidents()
    st.write(f"ℹ️ Found {len(all_incidents) if all_incidents else 0} total incidents")
    
    # Sidebar for navigation and filters
    with st.sidebar:
        st.header("🚨 Navigation")
        
        # Navigation buttons with unique keys
        if st.button("� Dashboard", use_container_width=True, key="nav_dashboard"):
            st.session_state.page = "📊 Dashboard"
            st.rerun()
            
        if st.button("�� List Incidents", use_container_width=True, key="nav_list_incidents"):
            st.session_state.page = "📋 List Incidents"
            st.rerun()
            
        if st.button("➕ Create Incident", use_container_width=True, key="nav_create_incident"):
            st.session_state.page = "➕ Create Incident"
            st.rerun()
            
        st.markdown("---")
        
        # Add filters that will be used across pages
        st.header("Filters")
        
        # Date range filter
        st.subheader("Date Range")
        today = datetime.now()
        default_start = today - timedelta(days=30)
        date_range = st.date_input(
            "Select Date Range",
            [default_start.date(), today.date()],
            format="YYYY/MM/DD"
        )
        
        # Status filter
        st.subheader("Status")
        status_options = ["All", "Open", "In Progress", "Resolved"]
        selected_status = st.multiselect(
            "Filter by Status",
            options=status_options,
            default=["All"]
        )
        
        # Severity filter
        st.subheader("Severity")
        severity_options = ["All", "High", "Medium", "Low"]
        selected_severity = st.multiselect(
            "Filter by Severity",
            options=severity_options,
            default=["All"]
        )
        
        # Add some space at the bottom
        st.markdown("---")
        if st.button("🔄 Refresh Data"):
            st.experimental_rerun()

    # Check API health
    health = check_health()
    if "error" in health:
        st.error(f"Backend health check failed: {health['error']}")
        return

    # Get incidents data and apply filters
    st.write("🔄 Applying filters to incidents...")
    incidents = all_incidents  # Use the already fetched incidents
    filtered_incidents = []
    
    if incidents:
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame(incidents)
        
        # Apply date filter
        if 'created_at' in df.columns:
            df['created_at_dt'] = pd.to_datetime(df['created_at']).dt.date
            if 'date_range' in locals() and date_range and len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df['created_at_dt'] >= start_date) & 
                       (df['created_at_dt'] <= end_date)]
        
        # Apply status filter
        if 'status' in df.columns and 'selected_status' in locals() and selected_status and "All" not in selected_status:
            status_values = [s.upper().replace(" ", "_") for s in selected_status]
            df = df[df['status'].str.upper().isin(status_values)]
        
        # Apply severity filter
        if 'severity' in df.columns and 'selected_severity' in locals() and selected_severity and "All" not in selected_severity:
            severity_values = [s.upper() for s in selected_severity]
            df = df[df['severity'].str.upper().isin(severity_values)]
        
        filtered_incidents = df.to_dict('records')
    
    # Page routing
    if st.session_state.page == "📊 Dashboard":
        st.title("Incident Dashboard")
        st.markdown("""
            <div style='
                text-align: center; 
                color:#333333; ; 
                margin: 10px 0 25px 0; 
                padding: 15px; 
                background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
                border-radius: 10px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-weight: 600;
                letter-spacing: 0.5px;
            '>
                🚨 Incident Management Dashboard
            </div>
        """, unsafe_allow_html=True)
        st.write("📊 Dashboard view active")
        st.json({"Total Incidents": len(incidents), "Filtered Incidents": len(filtered_incidents)})
        
        if not filtered_incidents:
            st.info("No incidents found matching the selected filters.")
        else:
            # Summary Metrics
            st.markdown("### 📈 Summary")
            create_summary_metrics(filtered_incidents)
            
            # Charts Row 1
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🎯 Severity Distribution")
                create_severity_pie_chart(filtered_incidents)
            
            with col2:
                st.markdown("### 📊 Status Overview")
                create_status_bar_chart(filtered_incidents)
            
            # Timeline Chart
            st.markdown("### 📅 Incidents Over Time")
            create_timeline_chart(filtered_incidents)
            
            # Recent Incidents Table
            st.markdown("### 📋 Recent Incidents")
            create_incident_table(filtered_incidents[:10])  # Show only 10 most recent
            
            if len(filtered_incidents) > 10:
                st.info(f"Showing 10 most recent of {len(filtered_incidents)} filtered incidents")
    
    elif st.session_state.page == "📋 List Incidents":
        if not filtered_incidents:
            st.info("No incidents found matching the selected filters.")
        else:
            # Display incidents table
            st.subheader("All Incidents")
            create_incident_table(filtered_incidents)
    
    elif st.session_state.page == "➕ Create Incident":
        show_create_incident_form()
    
    # Show incident count and filters for the List Incidents page
    if st.session_state.page == "📋 List Incidents":
        filter_summary = []
        if 'date_range' in locals() and len(date_range) == 2:
            filter_summary.append(f"Date: {date_range[0]} to {date_range[1]}")
            
        if 'selected_status' in locals() and selected_status and "All" not in selected_status:
            filter_summary.append(f"Status: {', '.join(selected_status)}")
            
        if 'selected_severity' in locals() and selected_severity and "All" not in selected_severity:
            filter_summary.append(f"Severity: {', '.join(selected_severity)}")
        
        # Only show filters if there are any active filters
        if filter_summary:
            st.caption(f"🔍 Filters: {', '.join(filter_summary)}")
        
        # Show incident count and incidents table
        if 'filtered_incidents' in locals():
            st.caption(f"Found {len(filtered_incidents)} incidents")
            
            if not filtered_incidents:
                st.info("No incidents match the current filters.")
            else:
                # Use the existing create_incident_table function to display incidents
                create_incident_table(filtered_incidents)

if __name__ == "__main__":
    # Initialize session state for page navigation if it doesn't exist
    if 'page' not in st.session_state:
        st.session_state.page = "� Dashboard"  # Set Dashboard as default page
    
    # Call the main function
    main()
