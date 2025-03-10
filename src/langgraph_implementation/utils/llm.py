import os
from typing import Optional

from langchain_openai import ChatOpenAI


def get_model() -> Optional[ChatOpenAI | None]:
    # Get and validate API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Print error to console
        print(
            f"API Key Error: Please make sure OPENAI_API_KEY is set in your .env file."
        )
        raise ValueError(
            "OpenAI API key not found.  Please make sure OPENAI_API_KEY is set in your .env file."
        )
    return ChatOpenAI(model="gpt-4o-mini", api_key=api_key)


def call_llm(prompt, pydantic_model):
    llm = get_model()

    llm = llm.with_structured_output(
        pydantic_model,
        method="json_mode",
    )
    print("Invoking OpenAI")
    result = llm.invoke(prompt)
    return result
