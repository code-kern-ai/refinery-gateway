from typing import List, Dict


def get_language_models() -> List[Dict[str, str]]:
    # CAUTION: these models must be installed in the lf-execution-environment!
    return [
        {"name": "English", "config_string": "en_core_web_sm"},
        {"name": "German", "config_string": "de_core_news_sm"},
        {"name": "Chinese", "config_string": "zh_core_web_sm"},
        {"name": "Danish", "config_string": "da_core_news_sm"},
        {"name": "Dutch", "config_string": "nl_core_news_sm"},
        {"name": "French", "config_string": "fr_core_news_sm"},
        {"name": "Greek", "config_string": "el_core_news_sm"},
        {"name": "Italian", "config_string": "it_core_news_sm"},
        {"name": "Japanese", "config_string": "ja_core_news_sm"},
        {"name": "Polish", "config_string": "pl_core_news_sm"},
        {"name": "Portuguese", "config_string": "pt_core_news_sm"},
        {"name": "Russian", "config_string": "ru_core_news_sm"},
        {"name": "Spanish", "config_string": "es_core_news_sm"},
        {"name": "Multilanguage", "config_string": "xx_ent_wiki_sm"},
    ]
