from submodules.model import enums
import pandas as pd


def infer_category(file_name: str) -> str:
    category = file_name.split("_")[-1]
    return (
        enums.RecordCategory.TEST.value
        if enums.RecordCategory.TEST.value.lower() in category.lower()
        else enums.RecordCategory.SCALE.value
    )


def infer_category_enum(df: pd.DataFrame, df_col: str) -> str:
    type_name = df[df_col].dtype.name
    if type_name == "int64":
        return enums.DataTypes.INTEGER.value
    elif type_name == "float64":
        return enums.DataTypes.FLOAT.value
    elif type_name == "bool":
        return enums.DataTypes.BOOLEAN.value
    elif type_name == "object":
        sample = df[df_col].sample(10) if len(df) > 10 else df[df_col]
        if sample.apply(lambda x: len(str(x).split()) > 4).sum() > 0:
            # if any of 10 randomly sampled texts contains more than 4 whitespaces, it is most likely text
            return enums.DataTypes.TEXT.value
        else:
            return enums.DataTypes.CATEGORY.value
    else:
        return enums.DataTypes.UNKNOWN.value


def infer_category_completeness(df: pd.DataFrame, df_col: str) -> bool:
    return df[df_col].isnull().sum() == 0
