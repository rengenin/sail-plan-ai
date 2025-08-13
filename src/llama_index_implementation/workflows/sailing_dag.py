from langgraph import LangGraph
from langgraph.tasks import Task
from agents.noaa_agent import get_noaa_data
from agents.weather_agent import get_weather_data
from agents.captain_agent import make_decision

def build_sailing_dag():
    """Create a DAG with tasks for NOAA, weather, and captain decisions."""
    graph = LangGraph()

    # Define each task as an agent
    noaa_task = Task(get_noaa_data, station_id="9445958")  # Example station ID
    weather_task = Task(get_weather_data, lat=47.5404, lon=-122.6361)
    decision_task = Task(make_decision)

    # Define task dependencies (order of execution)
    graph.add_edge(noaa_task, weather_task)  # NOAA data is required before weather
    graph.add_edge(weather_task, decision_task)  # Weather data is required for decision

    # Execute the graph
    graph.execute()

    # Return the decision
    decision_result = decision_task.result
    print(f"Sailing Decision: {decision_result['decision']} ({decision_result['reason']})")
    return decision_result