import logging
from typing import Sequence, TypeVar

from langchain.chat_models.base import BaseChatModel
from langchain.output_parsers import RetryWithErrorOutputParser
from langchain.schema import BaseOutputParser, HumanMessage
from langchain.schema.language_model import BaseLanguageModel
from langchain.schema.prompt import PromptValue
from pydantic import BaseModel

T = TypeVar("T")


def parse_and_attempt_repair_for_output(
    output: str,
    parser: BaseOutputParser[T],
    formatted_prompt: PromptValue,
    repair_llm: BaseLanguageModel,
    do_not_repair: bool = False,
) -> T:
    try:
        return parser.parse(output)
    except Exception:
        logging.exception("Parse failed. Doing retry")
        if do_not_repair:
            raise
        retry_parser = RetryWithErrorOutputParser.from_llm(parser=parser, llm=repair_llm)
        return retry_parser.parse_with_prompt(completion=output, prompt_value=formatted_prompt)


def convert_list_of_pydantic_objects_for_json(
    pydantic_objects: Sequence[BaseModel],
) -> list[dict]:
    return [obj.model_dump() for obj in pydantic_objects]


def get_response(llm: BaseLanguageModel | BaseChatModel, message: str) -> str:
    # I really despise the interface inconsistencies with LangChain
    if isinstance(llm, BaseLanguageModel):
        return llm.predict(message)
    return llm([HumanMessage(content=message)]).content


async def get_response_async(llm: BaseLanguageModel | BaseChatModel, message: str) -> str:
    # I really despise the interface inconsistencies with LangChain
    if isinstance(llm, BaseLanguageModel):
        return await llm.apredict(message)
    return await llm.agenerate([HumanMessage(content=message)]).content
