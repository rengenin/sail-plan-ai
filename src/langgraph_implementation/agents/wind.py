import json

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from graph.state import AgentState, show_agent_reasoning
from utils.llm import call_llm


class WindPredictions(BaseModel):
    confidence: float
    reasoning: str
    wind_strength: str
    wind_direction: str


def wind_agent(state: AgentState):
    trip_data = state["data"]
    wind_analysis = generate_wind_predictions(
        trip_data["location"], trip_data["start_date"]
    )
    wind_dict = {
        "wind_strength": wind_analysis.wind_strength,
        "wind_direction": wind_analysis.wind_direction,
        "confidence": wind_analysis.confidence,
        "reasoning": wind_analysis.reasoning,
    }
    message = HumanMessage(content=json.dumps(wind_dict), name="wind_agent")

    show_agent_reasoning(wind_dict, "Wind Agent")

    # Store signals in the overall state
    state["data"]["analyst_signals"]["wind_agent"] = wind_dict

    return {"messages": [message], "data": state["data"]}


def generate_wind_predictions(location: str, start_date: str):
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a meteorologist. Use all tools at your disposal to review forecasted wind predictions 
                for a given location and date. 
                
                Make sure to include in your reasoning response the following:
                - Wind speed
                - Wind gust speed
                - Wind compass direction
                """,
            ),
            (
                "human",
                """Aggregate wind forecast data for {location} on {start_date}

                Return the wind strength, direction and decision in the following JSON format:
                {{
                "wind_strength": "low" to "high" in knots,
                "wind_direction": "compass direction"
                "confidence": float (0-100),
                "reasoning": "string"
                }}
                """,
            ),
        ]
    )
    prompt = template.invoke({"location": location, "start_date": start_date})
    return call_llm(prompt=prompt, pydantic_model=WindPredictions)
