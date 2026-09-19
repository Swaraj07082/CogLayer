# import json
# import os
# from pathlib import Path
# from typing import Literal, Optional

# from dotenv import load_dotenv
# from langchain_groq import ChatGroq
# from langchain_core.output_parsers import PydanticOutputParser
# from langchain_core.prompts import PromptTemplate
# from pydantic import BaseModel

# load_dotenv()


# class MemoryAction(BaseModel):
#     action: Literal["ADD", "UPDATE", "DELETE", "NOOP"]
#     memory: str
#     old_memory: Optional[str] = None


# class MemoryActions(BaseModel):
#     actions: list[MemoryAction]


# parser = PydanticOutputParser(pydantic_object=MemoryActions)


