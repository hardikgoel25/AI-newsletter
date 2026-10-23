from groq import Groq
from openai import OpenAI
import ollama

from src.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY
)


class LLMClient:

    def __init__(
        self,
        provider="groq",
        model="llama-3.3-70b-versatile"
    ):

        self.provider = provider
        self.model = model

        if provider == "groq":
            self.client = Groq(api_key=GROQ_API_KEY)

        elif provider == "openai":
            self.client = OpenAI(api_key=OPENAI_API_KEY)

        elif provider == "ollama":
            self.client = None

        else:
            raise ValueError(
                f"Unsupported provider: {provider}"
            )

    def generate(
        self,
        prompt,
        temperature=0.3
    ):

        if self.provider == "groq":

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.choices[0].message.content

        elif self.provider == "openai":

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.choices[0].message.content

        elif self.provider == "ollama":

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response["message"]["content"]