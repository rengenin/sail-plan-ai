import json
from typing import Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from graph.state import AgentState, show_agent_reasoning
from utils.api import get_tidal_data
from utils.llm import call_llm


class WaterCurrent(BaseModel):
    confidence: float
    reasoning: str
    current_speed: str
    current_direction: str


class NOAAStations(BaseModel):
    station_ids: List[int]
    station_names: List[str]
    station_distances: List[float]


def current_agent(state: AgentState):
    trip_data = state["data"]
    tides_data = {}
    for station_id in trip_data["analyst_signals"]["noaa_agent"]["noaa_station_ids"]:
        print(f"trying NOAA station: {station_id}")
        http_code, tides_data = get_tidal_data(
            noaa_id=station_id, start_date=trip_data["start_date"]
        )
        if http_code == 200:
            break
        else:
            pass

    print("Pulled some NOAA data...")
    print(tides_data)
    current_analysis = generate_current_predictions(
        location=trip_data["location"],
        tides_data=tides_data,
        start_date=trip_data["start_date"],
    )
    current_analysis_dict = {
        "confidence": current_analysis.confidence,
        "reasoning": current_analysis.reasoning,
        "current_speed": current_analysis.current_speed,
        "currend_direction": current_analysis.current_direction,
    }
    message = HumanMessage(
        content=json.dumps(current_analysis_dict), name="current_agent"
    )

    show_agent_reasoning(current_analysis_dict, "Current Agent")

    # Store signals in the overall state
    state["data"]["analyst_signals"]["current_agent"] = current_analysis_dict

    return {"messages": [message], "data": state["data"]}


def noaa_agent(state: AgentState):
    trip_data = state["data"]
    noaa_station = closest_noaa_stations(trip_data["location"])
    station_dict = {
        "noaa_station_ids": noaa_station.station_ids,
        "noaa_station_names": noaa_station.station_names,
        "noaa_station_distances": noaa_station.station_distances,
    }
    message = HumanMessage(content=json.dumps(station_dict), name="noaa_agent")
    show_agent_reasoning(station_dict, "NOAA Agent")

    state["data"]["analyst_signals"]["noaa_agent"] = station_dict

    return {"messages": [message], "data": state["data"]}


def closest_noaa_stations(location: str):
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Provide a list of the NOAA water levels stations closest to {location}. 
                Order response by distance from clostest for furthest. 
                """,
            ),
            (
                "human",
                """What are the closest 8 NOAA station to {location}?

                Return JSON exactly in this format:
                {{
                "station_ids": List[int],
                "station_names": List[str],
                "station_distances": List[float]
                }}
                """,
            ),
        ]
    )
    prompt = template.invoke({"location": location})
    return call_llm(prompt=prompt, pydantic_model=NOAAStations)


def generate_current_predictions(
    location: str, tides_data: Dict, start_date: str, end_date: str = None
):

    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a seasoned sailor analyzing local NOAA tides and current data for {location}.
                trying to understand how your planned trip for {start_date} will be effected.

                Analyze tides and current data {tides_data} for {location} on {start_date}.
                
                Make sure to include in your reasoning response the following:
                - Max current speed
                - Compass direction of current
                - Time of Ebb and Flow
                """,
            ),
            (
                "human",
                """Aggregate {tides_data} for {location} on {start_date}

                Return JSON exactly in this format:
                {{
                "current_speed": "low" to "high" in knots,
                "current_direction": "compass direction and "ebb or flow"
                "confidence": float (0-100),
                "reasoning": "string"
                }}
                """,
            ),
        ]
    )
    prompt = template.invoke(
        {"location": location, "tides_data": tides_data, "start_date": start_date}
    )
    return call_llm(prompt=prompt, pydantic_model=WaterCurrent)
