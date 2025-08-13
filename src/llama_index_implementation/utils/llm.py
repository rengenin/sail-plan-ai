import os
from typing import Optional
from llama_index.llms.openai import OpenAI


def get_model() -> Optional[OpenAI]:
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
    return OpenAI(model="gpt-4o-mini", api_key=api_key)


def call_llm(prompt, llm, output_data_cls):
    try:
        resp = llm.as_structured_llm(output_cls=output_data_cls).chat(prompt)
        print(resp)
    except Exception as e:
        print(f"Error in LLM response: {e}")