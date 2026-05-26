import os
import sys
import logging
from gemini_live_telemetry import activate, InstrumentationConfig
from gemini_live_telemetry._dashboard import create_or_update_dashboard

logging.basicConfig(level=logging.DEBUG)

def main():
    project_id = "general-ak"
    print(f"Creating dashboard for project: {project_id}")
    try:
        config = InstrumentationConfig(project_id=project_id, dashboard_name="Gemini Live API Metrics")
        create_or_update_dashboard(config)
        print("Dashboard creation script completed.")
    except Exception as e:
        print(f"Error creating dashboard: {e}")

if __name__ == "__main__":
    main()
