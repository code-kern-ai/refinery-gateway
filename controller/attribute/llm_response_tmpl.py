import json
import time
from typing import Any, Optional, Union, List, Dict
from enum import Enum
import asyncio

from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
from openai import (
    AuthenticationError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    UnprocessableEntityError,
    BadRequestError,
)
from openai.types.chat import ChatCompletion


class LLMProvider_A2VYBG(Enum):
    OPEN_AI = "Open AI"
    OPEN_SOURCE = "Open-Source"
    AZURE = "Azure"


# OpenAI migration guides
# https://github.com/openai/openai-python/discussions/742
# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/migration?tabs=python-new%2Cdalle-fix

MAX_CACHED_CLIENTS_A2VYBG = 0  # 60
CLIENT_LOOKUP_A2VYBG = {}  # list of client -> last used tuples
NUM_WORKERS_A2VYBG = "@@NUM_WORKERS@@"  # number of concurrent API calls for LLM
MAX_RETRIES_A2VYBG = "@@MAX_RETRIES_A2VYBG@@"  # number of retries for LLM API calls
RETRY_SLEEP_SEC_A2VYBG = (
    "@@RETRY_SLEEP_SEC_A2VYBG@@"  # seconds to sleep between retries
)

API_KEY_A2VYBG = "@@API_KEY@@"
API_BASE_A2VYBG = "@@API_BASE@@"
API_VERSION_A2VYBG = "@@API_VERSION@@"
CLIENT_TYPE_A2VYBG = "@@CLIENT_TYPE@@"  # OpenAIClientType, "OPEN_AI" or "AZURE"
MODEL_A2VYBG = "@@MODEL@@"
CACHE_ACCESS_LINK_A2VYBG = "@@CACHE_ACCESS_LINK@@"
CACHE_FILE_UPLOAD_LINK_A2VYBG = "@@CACHE_FILE_UPLOAD_LINK@@"
LLM_KWARGS_A2VYBG = {
    "response_format": {"type": "json_object"},
    "stream": False,
    # fmt:off
    "stop": json.loads('@@STOP_SEQUENCE@@'),
    # fmt:on
    "temperature": float("@@TEMPERATURE@@"),
    "max_tokens": int("@@MAX_TOKENS@@"),
    "top_p": float("@@TOP_P@@"),
    "frequency_penalty": float("@@FREQUENCY_PENALTY@@"),
    "presence_penalty": float("@@PRESENCE_PENALTY@@"),
}

SYSTEM_PROMPT_A2VYBG = (
    """@@SYSTEM_PROMPT@@ You must only output valid JSON. """
    "If there is not yet a schema defined for the JSON output, "
    "please put everything into a single value under the key 'result' "
    "- otherwise stick to the schema that has been provided already."
)
USER_PROMPT_A2VYBG = (
    """@@USER_PROMPT@@"""  # is updated in runtime by refinery-ac-exec-env/run_ac.py
)

# azure_endpoint = api_base (before 1.0) - basically the link to the api


def test_client_model_2c6ecfb1_9bce_4e89_80c8_cbc4e3fca9e5(
    client: Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI], model: str
):
    if __is_client_valid_ex_8840b3a8_92d2_4526_b054_3b83c5cccb5c(client) is not None:
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


def get_client_8e8a360e_3f7f_4cf9_ba80_8cb239e897d2(
    use_async: bool,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    check_valid: bool = True,
    prevent_cached_client: bool = True,
) -> Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]:
    global CLIENT_LOOKUP_A2VYBG

    if CLIENT_TYPE_A2VYBG == LLMProvider_A2VYBG.AZURE.value and (
        azure_endpoint is None or api_version is None
    ):
        raise ValueError("azure_endpoint and api_version must be set for Azure OpenAI")

    # tuples can be used as dict keys, primitive datatype comparison works flawless, caution with objects though!
    config = (CLIENT_TYPE_A2VYBG, use_async, api_key, azure_endpoint, api_version)
    use_cache = MAX_CACHED_CLIENTS_A2VYBG != 0 and not prevent_cached_client
    if use_cache and config in CLIENT_LOOKUP_A2VYBG:
        if check_valid:
            exception = __is_client_valid_ex_8840b3a8_92d2_4526_b054_3b83c5cccb5c(
                CLIENT_LOOKUP_A2VYBG[config][0]
            )
            if exception is not None:
                raise exception

        CLIENT_LOOKUP_A2VYBG[config] = (CLIENT_LOOKUP_A2VYBG[config][0], time.time())

        return CLIENT_LOOKUP_A2VYBG[config][0]
    else:
        if use_cache and len(CLIENT_LOOKUP_A2VYBG) >= MAX_CACHED_CLIENTS_A2VYBG:
            # remove oldest client
            tmp = sorted(
                CLIENT_LOOKUP_A2VYBG.items(), key=lambda x: x[1][1], reverse=True
            )
            (client, _) = tmp.pop()
            client.close()
            CLIENT_LOOKUP_A2VYBG = dict(tmp)

        client = __create_client_bf47529a_75f7_498b_a091_4e7d52d35b6b(
            use_async, api_key, azure_endpoint, api_version
        )

        # test client with api key
        if check_valid:
            exception = __is_client_valid_ex_8840b3a8_92d2_4526_b054_3b83c5cccb5c(
                client
            )
            if exception is not None:
                raise exception

        if use_cache:
            CLIENT_LOOKUP_A2VYBG[config] = (client, time.time())
        return client


def __create_client_bf47529a_75f7_498b_a091_4e7d52d35b6b(
    use_async: bool,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
):
    client = None
    if CLIENT_TYPE_A2VYBG == LLMProvider_A2VYBG.AZURE.value:
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


def __is_client_valid_ex_8840b3a8_92d2_4526_b054_3b83c5cccb5c(
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


def get_openai_value_from_336aa73b_a8a0_4148_8c6e_445c29a9e377(
    open_ai_obj: ChatCompletion, raise_me: bool = True
) -> Dict[str, Any]:
    if not open_ai_obj:
        return ""
    if hasattr(open_ai_obj, "choices") and len(open_ai_obj.choices) > 0:
        t = open_ai_obj.choices[0]
        if hasattr(t, "message") and hasattr(t.message, "content"):
            # fmt:off
            content = t.message.content or '{\"result\": \"Error: N/A\"}'
            # fmt:on
            try:
                content = json.loads(content)
            except Exception:
                content = {
                    "result": "Error: Could not parse LLM response into valid JSON: "
                    + content
                }
                print(
                    'Error: Could not parse LLM response into valid JSON -> check databrowser for "Error: "',
                    flush=True,
                )
            if isinstance(content, dict):
                content = convert_to_string(content)
            return content
    else:
        raise ValueError("Unknown open_ai_obj:" + type(open_ai_obj))
    ## if we reach this point, we couldn't access the value
    if raise_me:
        raise ValueError("Couldn't access value from", open_ai_obj)
    return ""


def convert_to_string(data):
    if isinstance(data, dict):
        return {key: convert_to_string(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_to_string(item) for item in data]
    else:
        if isinstance(data, str):
            return data
        return str(data)


# all work similar but use different classes etc.
# note that kwargs is just passed to the openai client so adding unknown kwargs will result in issues
# named parameter are NOT considered kwargs, only unknown parameters are kwargs
def get_chat_completion_4a90ecec_fc72_45af_ba0d_ae9a2dc4674c(
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    close_after: bool = False,
    **kwargs,
) -> ChatCompletion:
    client = get_client_8e8a360e_3f7f_4cf9_ba80_8cb239e897d2(
        use_async=False,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        prevent_cached_client=close_after,
    )
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )
    if close_after:
        client.close()

    return completion


async def get_chat_completion_async_4a90ecec_fc72_45af_ba0d_ae9a2dc4674c(
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    close_after: bool = False,
    **kwargs,
) -> ChatCompletion:
    client = get_client_8e8a360e_3f7f_4cf9_ba80_8cb239e897d2(
        use_async=True,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        prevent_cached_client=close_after,
    )
    completion = await client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )
    if close_after:
        await client.close()

    return completion


def get_llm_config_a2vybg():
    return {
        "client_type": CLIENT_TYPE_A2VYBG,
        "api_key": API_KEY_A2VYBG,
        "api_base": API_BASE_A2VYBG,
        "api_version": API_VERSION_A2VYBG,
        "model": MODEL_A2VYBG,
        "system_prompt": SYSTEM_PROMPT_A2VYBG,
        "user_prompt": USER_PROMPT_A2VYBG,
        "llm_kwargs": LLM_KWARGS_A2VYBG,
    }


async def get_llm_response(record: dict, cached_records: dict):
    curr_running_id = str(record["running_id"])

    if curr_running_id in cached_records:
        return cached_records[curr_running_id]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_A2VYBG,
        },
        {
            "role": "user",
            "content": USER_PROMPT_A2VYBG,
        },
    ]
    exception = None
    for _ in range(int(MAX_RETRIES_A2VYBG)):
        try:
            chat_completion = (
                await get_chat_completion_async_4a90ecec_fc72_45af_ba0d_ae9a2dc4674c(
                    MODEL_A2VYBG,
                    messages,
                    API_KEY_A2VYBG,
                    API_BASE_A2VYBG,
                    API_VERSION_A2VYBG,
                    close_after=True,
                    **LLM_KWARGS_A2VYBG,
                )
            )
            value = get_openai_value_from_336aa73b_a8a0_4148_8c6e_445c29a9e377(
                chat_completion
            )
            cached_records[curr_running_id] = value
            return value
        except (
            APITimeoutError,
            RateLimitError,
            InternalServerError,
            UnprocessableEntityError,
        ) as e:
            exception = e
            await asyncio.sleep(int(RETRY_SLEEP_SEC_A2VYBG))
            continue
        except BadRequestError as e:
            exception = e
            break
    m = f"Error: Failed to get LLM response ({str(exception)})"
    print(m, flush=True)
    cached_records[curr_running_id] = {"result": m}
    return {"result": m}
