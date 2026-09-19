import os
from typing import Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

load_dotenv()


class Memories(BaseModel):
    memories: list[str]

parser = PydanticOutputParser(pydantic_object=Memories)

def llm_call(summary:Optional[str] = None , top_k_messages:Optional[list[str]] = None , user_message:str = None):
    llm = ChatGroq(
        api_key = os.getenv("GROQ_API_KEY"),
        model = os.getenv("GROQ_MODEL"),
    )

    
    prompt = PromptTemplate(
        template = """
        You extract durable user memories from a conversation.
        Return only facts that are useful for future conversations, such as
        preferences, personal details, goals, projects, or important events.
        Do not extract greetings, questions without answers, or temporary details.

        Summary:
        {summary}

        Recent conversation:
        {top_k_messages}

        Current conversation:
        User: {user_message}

        {format_instructions}
        Return the candidate memories as a list of concise facts.
        """,
        input_variables = ["user_message" , "summary" , "top_k_messages"],
        partial_variables = {"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser

    return chain.invoke({"user_message": user_message , "summary": summary , "top_k_messages": top_k_messages})
