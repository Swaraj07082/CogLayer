from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

def generate_summary(conversation_messages : list[dict]) -> str:
    summary = ""

    llm = ChatGroq(
        api_key = os.getenv("GROQ_API_KEY"),
        model = os.getenv("GROQ_MODEL"),
    )

    class Summary(BaseModel):
        summary : str

    parser = PydanticOutputParser(pydantic_object=Summary)

    prompt = PromptTemplate(
        template = """
        You are a helpful assistant that summarizes a conversation.
        The conversation is a list of messages between a user and an assistant.
        {format_instructions}
        {conversation_messages}
        Return the summary of the conversation.
        """,
        input_variables = ["conversation_messages"],
        partial_variables = {"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser
    result = chain.invoke({"conversation_messages": conversation_messages})
    return result.summary

    