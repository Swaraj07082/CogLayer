import os
from typing import Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

load_dotenv()


class Response(BaseModel):
    response: str

parser = PydanticOutputParser(pydantic_object=Response)

def llm_call(memories:Optional[list[str]] = None , conversations:Optional[list[str]] = None , user_message:str = None):
    llm = ChatGroq(
        api_key = os.getenv("GROQ_API_KEY"),
        model = os.getenv("GROQ_MODEL"),
    )

    
    prompt = PromptTemplate(
        template = """
        These are previous memories of the user:
        {memories}

        These are previous conversations of the user:
        {conversations}

        This is the user's current message:
        {user_message}

        give an appropriate response to the user's message based on the previous memories and conversations and your own knowledge.

        {format_instructions}.
        """,
        input_variables = ["user_message" , "memories" , "conversations"],
        partial_variables = {"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser

    return chain.invoke({"user_message": user_message , "memories": memories , "conversations": conversations})
