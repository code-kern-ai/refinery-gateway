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
        if df[df_col].apply(lambda x: x > 2_147_483_647).sum() > 0:
            # doesn't fit in database INTEGER type
            # check all values instead of sample since it a simple integer column
            return enums.DataTypes.TEXT.value
        return enums.DataTypes.INTEGER.value
    elif type_name == "float64":
        return enums.DataTypes.FLOAT.value
    elif type_name == "bool":
        return enums.DataTypes.BOOLEAN.value
    elif type_name == "object":
        if (
            df[df_col].nunique() <= df[df_col].count() * 0.2
            and df[df_col].str.len().max() < 50
        ):
            return enums.DataTypes.CATEGORY.value
        return enums.DataTypes.TEXT.value
    else:
        return enums.DataTypes.UNKNOWN.value


def infer_category_completeness(df: pd.DataFrame, df_col: str) -> bool:
    return df[df_col].isnull().sum() == 0
