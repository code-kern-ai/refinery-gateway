import time
from typing import Any, Optional, Union, List, Dict
from enum import Enum

from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
from openai import AuthenticationError
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class OpenAIClientType(Enum):
    OPEN_AI = "OPEN_AI"
    AZURE = "AZURE"


# OpenAI migration guides
# https://github.com/openai/openai-python/discussions/742
# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/migration?tabs=python-new%2Cdalle-fix

MAX_CACHED_CLIENTS = 0  # 60
CLIENT_LOOKUP = {}  # list of client -> last used tuples


# azure_endpoint = api_base (before 1.0) - basically the link to the api


def test_client_model(
    client_type: OpenAIClientType,
    model: str,
    use_async: bool,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
):
    client = __create_client(
        client_type, use_async, api_key, azure_endpoint, api_version
    )

    if __is_client_valid_ex(client) is not None:
        print(
            "Error: Invalid OpenAI client config (api_key, api_version or endpoint)",
            flush=True,
        )
        return False

    try:
        client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "A",
                }
            ],
            stream=False,
            temperature=1,
            max_tokens=1,
        )
    except Exception as e:
        print("Error: Test chat completion failed", flush=True)
        print(e, flush=True)
        return False
    return True


def get_client(
    client_type: OpenAIClientType,
    use_async: bool,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    check_valid: bool = True,
    prevent_cached_client: bool = True,
) -> Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]:
    if client_type == OpenAIClientType.AZURE and (
        azure_endpoint is None or api_version is None
    ):
        raise ValueError("azure_endpoint and api_version must be set for Azure OpenAI")

    # tuples can be used as dict keys, primitive datatype comparison works flawless, caution with objects though!
    config = (client_type.value, use_async, api_key, azure_endpoint, api_version)
    use_cache = MAX_CACHED_CLIENTS != 0 and not prevent_cached_client
    global CLIENT_LOOKUP
    if use_cache and config in CLIENT_LOOKUP:
        if check_valid:
            exception = __is_client_valid_ex(CLIENT_LOOKUP[config][0])
            if exception is not None:
                raise exception

        CLIENT_LOOKUP[config] = (CLIENT_LOOKUP[config][0], time.time())

        return CLIENT_LOOKUP[config][0]
    else:
        if use_cache and len(CLIENT_LOOKUP) >= MAX_CACHED_CLIENTS:
            # remove oldest client
            tmp = sorted(CLIENT_LOOKUP.items(), key=lambda x: x[1][1], reverse=True)
            (client, _) = tmp.pop()
            client.close()
            CLIENT_LOOKUP = dict(tmp)

        client = __create_client(
            client_type, use_async, api_key, azure_endpoint, api_version
        )

        # test client with api key
        if check_valid:
            exception = __is_client_valid_ex(client)
            if exception is not None:
                raise exception

        if use_cache:
            CLIENT_LOOKUP[config] = (client, time.time())
        return client


def __create_client(
    client_type: OpenAIClientType,
    use_async: bool,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
):
    client = None
    if client_type == OpenAIClientType.AZURE:
        if use_async:
            client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
            )
        else:
            client = AzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
            )
    else:
        if use_async:
            client = AsyncOpenAI(
                api_key=api_key,
            )
        else:
            client = OpenAI(
                api_key=api_key,
            )
    return client


def __is_client_valid_ex(
    client: Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI], tries: int = 3
) -> Union[AuthenticationError, Exception, None]:
    i = 0
    while i := i + 1:
        try:
            client.models.list()
            return None
        except AuthenticationError as e:
            if i < tries:
                time.sleep(0.05)
                continue
            # client api key not valid
            # print(traceback.format_exc()) # removed since exception is reraised and the logs would be cluttered
            return e
        except Exception as e:
            if i < tries:
                time.sleep(0.05)
                continue
            return e


def get_openai_value_from(
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


def get_openai_finish_reason_from(
    open_ai_obj: ChatCompletion, raise_me: bool = True
) -> str:
    if not open_ai_obj:
        return ""
    if isinstance(open_ai_obj, ChatCompletion) or isinstance(
        open_ai_obj, ChatCompletionChunk
    ):
        if hasattr(open_ai_obj, "choices") and len(open_ai_obj.choices) > 0:
            return open_ai_obj.choices[0].finish_reason
    else:
        raise ValueError("Unknown open_ai_obj:" + type(open_ai_obj))
    ## if we reach this point, we couldn't access the value
    if raise_me:
        raise ValueError("Couldn't access value from", open_ai_obj)
    return ""


# all work similar but use different classes etc.
# note that kwargs is just passed to the openai client so adding unknown kwargs will result in issues
# named parameter are NOT considered kwargs, only unknown parameters are kwargs
def get_chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    client_type: OpenAIClientType,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    close_after: bool = False,
    **kwargs,
) -> ChatCompletion:
    client = get_client(
        client_type=client_type,
        use_async=False,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        prevent_cached_client=close_after,
    )
    completion = client.chat.completions.create(
        model=model, messages=messages, stream=False, **kwargs
    )
    if close_after:
        client.close()

    return completion


def get_llm_response():

    api_key = "@@API_KEY@@"
    endpoint = "@@ENDPOINT@@"
    api_version = "@@API_VERSION@@"
    client_type = "@@CLIENT_TYPE@@"  # OpenAIClientType, "OPEN_AI" or "AZURE"
    model = "@@MODEL@@"

    system_prompt = "@@SYSTEM_PROMPT@@"
    user_prompt = "@@USER_PROMPT@@"

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    chat_completion = get_chat_completion(
        model, messages, client_type, api_key, endpoint, api_version, close_after=True
    )

    return get_openai_value_from(chat_completion)
