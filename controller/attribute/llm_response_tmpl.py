import time
from typing import Optional, Union, List, Dict
from enum import Enum

from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
from openai import AuthenticationError
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class OpenAIClientType_A2VYBG(Enum):
    OPEN_AI = "OPEN_AI"
    AZURE = "AZURE"


# OpenAI migration guides
# https://github.com/openai/openai-python/discussions/742
# https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/migration?tabs=python-new%2Cdalle-fix

MAX_CACHED_CLIENTS_A2VYBG = 0  # 60
CLIENT_LOOKUP_A2VYBG = {}  # list of client -> last used tuples

API_KEY_A2VYBG = "@@API_KEY@@"
ENDPOINT_A2VYBG = "@@ENDPOINT@@"
API_VERSION_A2VYBG = "@@API_VERSION@@"
CLIENT_TYPE_A2VYBG = "@@CLIENT_TYPE@@"  # OpenAIClientType, "OPEN_AI" or "AZURE"
MODEL_A2VYBG = "@@MODEL@@"

SYSTEM_PROMPT_A2VYBG = "@@SYSTEM_PROMPT@@"
# SYSTEM_PROMPT_A2VYBG = (
#     "You are a news critic identifying clickbaits."
#     "The input is a news article title. Determine if the input is clickbait or not."
#     "Make your answer a single word, e.g. 'yes' or 'no'."
# )
USER_PROMPT_A2VYBG = (
    "@@USER_PROMPT@@"  # is updated in runtime by refinery-ac-exec-env/run_ac.py
)

# azure_endpoint = api_base (before 1.0) - basically the link to the api


def test_client_model_2c6ecfb1_9bce_4e89_80c8_cbc4e3fca9e5(
    model: str,
    use_async: bool,
    api_key: str,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
):
    client = __create_client_bf47529a_75f7_498b_a091_4e7d52d35b6b(
        use_async, api_key, azure_endpoint, api_version
    )

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
    global CLIENT_TYPE_A2VYBG

    if CLIENT_TYPE_A2VYBG == OpenAIClientType_A2VYBG.AZURE.value and (
        azure_endpoint is None or api_version is None
    ):
        raise ValueError("azure_endpoint and api_version must be set for Azure OpenAI")

    # tuples can be used as dict keys, primitive datatype comparison works flawless, caution with objects though!
    config = (CLIENT_TYPE_A2VYBG, use_async, api_key, azure_endpoint, api_version)
    use_cache = MAX_CACHED_CLIENTS_A2VYBG != 0 and not prevent_cached_client
    global CLIENT_LOOKUP_A2VYBG
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
    global CLIENT_TYPE_A2VYBG

    client = None
    if CLIENT_TYPE_A2VYBG == OpenAIClientType_A2VYBG.AZURE.value:
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
        model=model, messages=messages, stream=False, **kwargs
    )
    if close_after:
        client.close()

    return completion


def get_llm_response():
    global SYSTEM_PROMPT_A2VYBG, USER_PROMPT_A2VYBG, MODEL_A2VYBG, API_KEY_A2VYBG, ENDPOINT_A2VYBG, API_VERSION_A2VYBG

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

    chat_completion = get_chat_completion_4a90ecec_fc72_45af_ba0d_ae9a2dc4674c(
        MODEL_A2VYBG,
        messages,
        API_KEY_A2VYBG,
        ENDPOINT_A2VYBG,
        API_VERSION_A2VYBG,
        close_after=True,
    )

    return get_openai_value_from_336aa73b_a8a0_4148_8c6e_445c29a9e377(chat_completion)
