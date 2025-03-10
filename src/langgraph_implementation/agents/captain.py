import json
from typing import Dict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal

from graph.state import AgentState
from utils.llm import call_llm


class CaptainDecision(BaseModel):
    action: Literal["go", "no-go"]
    confidence: float = Field(
        description="Confidence in the decision, between 0.0 and 100.0"
    )
    reasoning: str = Field(description="Reasoning for the decision")


def captain_agent(state: AgentState):
    trip_data = state["data"]
    analyst_signals = state["data"]["analyst_signals"]

    result = generate_sailing_decision(
        signals=analyst_signals,
        location=trip_data["location"],
        start_date=trip_data["start_date"],
    )
    result_dict = {
        "action": result.action,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }
    message = HumanMessage(content=json.dumps(result_dict), name="captain_agent")

    return {
        "messages": state["messages"] + [message],
        "data": state["data"],
    }


def generate_sailing_decision(signals: Dict, location: str, start_date: str):
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a seasoned sailor and Captain of your ship. You must decide to go on a
                trip based upon multiple inputs from your trusted crew. After condidering their inputs
                you alone can reach the final decision of "Go"/"No-Go". The safety of the crew depends 
                upon your ability to weigh the information and make an informed decision.

                Available Actions:
                - "Go": You and your crew will depart for adventures!
                - "No-Go": Stay safely ashore and wait for a better weather window.

                How to prioritize inputs:
                - Wind: Most important. If wind exceeds steady state of 25 knots always choose "No-Go". 
                However gusts upto 25 knots is acceptable.
                - Currents: Avoid choosing "Go" if it means sailing against the current and propose a new departure 
                window which will have more favorable currents.
                - Weather: The only weather to make you choose "No-Go" should be electrical storms or heavy fog.

                Inputs:
                - signals: this is a dictionary of wind, weather and current forecasts
                """,
            ),
            (
                "human",
                """Based on your crew's analysis of currents, wind and weather make the final
                "Go", "No-Go" decision.

                You are looked to depart from: {location}

                on the date: {start_date}

                Here are the collected weather information from your crew: {signals}

                Return the tide and current data in the following JSON format:
                {{
                "action": "go" or "no-go",
                "confidence": float (0-100),
                "reasoning": "string"
                }}
                """,
            ),
        ]
    )
    prompt = template.invoke(
        {"signals": json.dumps(signals), "location": location, "start_date": start_date}
    )
    return call_llm(prompt=prompt, pydantic_model=CaptainDecision)
