from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from typing import Union

REFORMULATION_PROMPT = """Generate a refined and optimized reformulation of a given question, ensuring it aligns better with the user's search intent and maximizes result relevance for RAG. The reformulated question should maintain the original meaning while improving clarity, specificity, and contextual precision.

# Important Guidelines

- **Enhanced Clarity**: Improve sentence structure and wording for better readability.
- **Intent Alignment**: Ensure the reformulated question accurately reflects the user's underlying intent.
- **Keyword Optimization**: Retain and enhance relevant keywords for improved search efficiency.
- **Context Preservation**: Maintain all necessary contextual details while removing ambiguity.
- **Concise & Precise**: Avoid unnecessary words while keeping the question well-structured.
- **Neutral Tone**: Ensure the tone remains neutral and professional.
- **Variant Suggestions**: If applicable, suggest alternative phrasings for different perspectives.
- **Avoid Unnecessary Expansions**: Do not introduce irrelevant details that alter the original intent.
- **Question Type Awareness**: Recognize if the question seeks factual, comparative, or exploratory information and optimize accordingly.
- **No Change in Core Meaning**: Ensure the fundamental intent and topic of the question remain intact.

# Steps

1. Analyze the original question to identify key intent and meaning.
2. Reformulate it with improved clarity, precision, and structure.
3. Optimize for search relevance while preserving the original inquiry’s core message.
4. Provide alternative phrasings if they offer significant improvement.
5. Ensure the final output is concise, neutral, and intent-aligned.

# Output Format
Only the pure valid json with key "reformulation" and value as the improved version of the original question.

{
  "reformulation": "<The improved version of the original question>",
}

# Notes

A poorly reformulated question may lead to irrelevant or misleading results. It is essential to preserve intent while enhancing clarity and relevance."""


def reformulate_question(question: str, api_key: str) -> str:
    openai_client = OpenAI(api_key=api_key)
    messages = [
        {
            "role": "system",
            "content": REFORMULATION_PROMPT,
        },
        {
            "role": "user",
            "content": f"Question: {question}",
        },
    ]
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, stream=False
    )
    return __get_openai_value_from(completion)


def __get_openai_value_from(
    open_ai_obj: Union[ChatCompletion, ChatCompletionChunk], raise_me: bool = True
) -> str:
    if not open_ai_obj:
        return ""
    if isinstance(open_ai_obj, ChatCompletion) or isinstance(
        open_ai_obj, ChatCompletionChunk
    ):
        if hasattr(open_ai_obj, "choices") and len(open_ai_obj.choices) > 0:
            t = open_ai_obj.choices[0]
            if isinstance(open_ai_obj, ChatCompletion):
                if hasattr(t, "message") and hasattr(t.message, "content"):
                    return t.message.content or ""
            elif isinstance(open_ai_obj, ChatCompletionChunk):
                if hasattr(t, "delta") and hasattr(t.delta, "content"):
                    return t.delta.content or ""
    else:
        raise ValueError("Unknown open_ai_obj:" + type(open_ai_obj))
    ## if we reach this point, we couldn't access the value
    if raise_me:
        raise ValueError("Couldn't access value from", open_ai_obj)
    return ""
