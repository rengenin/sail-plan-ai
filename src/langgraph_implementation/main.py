from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from agents.captain import captain_agent
from agents.currents import current_agent, noaa_agent
from agents.weather import weather_agent
from agents.wind import wind_agent
from graph.state import AgentState, show_agent_reasoning

# Load environment variables from .env file
load_dotenv()


def parse_final_response(response):
    import json

    try:
        return json.loads(response)
    except:
        print(f"Error parsing response: {response}")
        return None


def run_sail_planner(
    start_date: str,
    # start_location: str = "Port Orchard Marina, Sinclair Inlet, Port Orchard Washington",
    start_location: str = "Port Orchard Marina, Port Orchard, Washington",
    end_location: str = "Port Orchard Marina, Sinclair Inlet, Port Orchard Washington",
    model_name: str = "gpt-4o-mini",
):
    # noaa_data = noaa_agent({"data": {"location": start_location}})
    # print(noaa_data)
    workflow = create_workflow()
    # # print(workflow)
    agent = workflow.compile()

    final_state = agent.invoke(
        {
            "messages": [HumanMessage(content="Make plans for a sailing adventure.")],
            "data": {
                "location": start_location,
                "start_date": start_date,
                "analyst_signals": {},
            },
            "metadata": {
                "show_reasoning": True,
            },
        },
    )

    return {
        "decisions": parse_final_response(final_state["messages"][-1].content),
        "analyst_signals": final_state["data"]["analyst_signals"],
    }


def start(state: AgentState):
    """Initialize the workflow with the input message."""
    return state


def create_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    ## NOAA Agent->Current->Captain
    workflow.add_node("noaa_agent", noaa_agent)
    workflow.add_edge("start_node", "noaa_agent")

    workflow.add_node("current_agent", current_agent)
    workflow.add_edge("noaa_agent", "current_agent")

    workflow.add_node("captain_agent", captain_agent)
    workflow.add_edge("current_agent", "captain_agent")

    # Wind->Captain
    workflow.add_node("wind_agent", wind_agent)
    workflow.add_edge("start_node", "wind_agent")
    workflow.add_edge("wind_agent", "captain_agent")

    # Weather->Captain
    workflow.add_node("weather_agent", weather_agent)
    workflow.add_edge("start_node", "weather_agent")
    workflow.add_edge("weather_agent", "captain_agent")

    workflow.add_edge("captain_agent", END)

    workflow.set_entry_point("start_node")
    return workflow


if __name__ == "__main__":
    result = run_sail_planner(start_date="03/16/2025")
    show_agent_reasoning(result, "The Captain's Decision")
