import json

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from graph.state import AgentState, show_agent_reasoning
from utils.llm import call_llm


class WeatherPrediction(BaseModel):
    confidence: float
    reasoning: str
    temperature: str
    rain_forecast: str


def weather_agent(state: AgentState):
    trip_data = state["data"]
    weather_analysis = generate_weather_predictions(
        trip_data["location"], trip_data["start_date"]
    )
    analysis_dict = {
        "confidence": weather_analysis.confidence,
        "reasoning": weather_analysis.reasoning,
        "temperature": weather_analysis.temperature,
        "rain_forecast": weather_analysis.rain_forecast,
    }
    message = HumanMessage(content=json.dumps(analysis_dict), name="weather_agent")
    show_agent_reasoning(analysis_dict, "Weather Agent")

    # Store signals in the overall state
    state["data"]["analyst_signals"]["weather_agent"] = analysis_dict

    return {"messages": [message], "data": state["data"]}


def generate_weather_predictions(location: str, start_date: str):
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a meteorologist. Provide the weather forecast for a given date and location.

                Include the following:
                - Temperature forecast low and high
                - Rain forecast
                - Confidence in prediction
                """,
            ),
            (
                "human",
                """Aggregate weather data for {location} on {start_date}

                Temperature and rain predictions the following JSON format:
                {{
                "temperature": "low" to "high" in Fahrenheit,
                "rain_forecast": "string"
                "confidence": float (0-100),
                "reasoning": "string"
                }}
                """,
            ),
        ]
    )
    prompt = template.invoke({"location": location, "start_date": start_date})
    return call_llm(prompt=prompt, pydantic_model=WeatherPrediction)
