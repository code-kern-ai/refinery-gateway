import pandas as pd
from fast_api.types import ToolTip


def resolve_tooltip(key: str) -> ToolTip:
    df = pd.read_json("tooltip_data.json").to_dict()
    if key in df:
        tooltip = ToolTip(
            key=key,
            title=df[key]["title"],
            text=df[key]["text"],
            href=df[key]["href"],
            href_caption=df[key]["hrefCaption"],
        )
        return tooltip
    else:
        return ToolTip(
            key=key,
            title="Sorry :(",
            text="We are still working on this tooltip!",
        )
