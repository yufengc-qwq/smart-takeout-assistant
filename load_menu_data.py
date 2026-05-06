import pandas as pd
import json
import re

def load_restaurant_data(file_path: str, file_type: str = "csv") -> pd.DataFrame:
    """
    读取餐厅/菜品表格数据
    :param file_path: 文件路径
    :param file_type: "csv" 或 "excel"
    :return: DataFrame
    """
    if file_type == "csv":
        df = pd.read_csv(file_path, encoding="utf-8")
    elif file_type == "excel":
        df = pd.read_excel(file_path, engine="openpyxl")
    else:
        raise ValueError("file_type 只支持 'csv' 或 'excel'")
    return df

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗和提取推荐所需的关键字段
    """
    # 保留核心字段（根据你的列名调整）
    keep_cols = [
        "name",           # 店铺名
        "地址",           # 地址
        "价格",           # 人均价格
        "评分",           # 综合评分
        "大类",           # 菜系分类
        "标签",           # 口味标签
        "标签.1",         # 备选标签
        "商圈",           # 商圈
        "菜单"
        "菜品",           # 推荐菜品（可能是JSON字符串）
        "营业状态",       # 是否营业
        "主图",
    ]
    # 只保留存在的列
    existing_cols = [c for c in keep_cols if c in df.columns]
    df_clean = df[existing_cols].copy()

    # 价格转数值（去掉¥符号等）
    if "价格" in df_clean.columns:
        df_clean["价格"] = df_clean["价格"].astype(str).str.replace(r"[^\d.]", "", regex=True)
        df_clean["价格"] = pd.to_numeric(df_clean["价格"], errors="coerce").fillna(0)

    # 评分转数值
    def extract_avg_score(score_text):
        if isinstance(score_text, str):
            nums = [float(x) for x in re.findall(r"\d+\.?\d*", score_text)]
            if nums:
                return round(sum(nums) / len(nums), 2)
        return 0.0

    if "评分" in df_clean.columns:
        df_clean["综合评分"] = df_clean["评分"].apply(extract_avg_score)
    else:
        df_clean["综合评分"] = 0.0   # 如果没有原始评分列，给默认值


    # 合并标签列，形成一个口味关键词列表
    df_clean["口味标签组合"] = df_clean.apply(
        lambda row: " ".join(
            str(row.get("标签", "")) + " " + str(row.get("标签.1", ""))
        ).strip(),
        axis=1
    )
    return df_clean

def export_for_assistant(df: pd.DataFrame, output_file: str = "menu_cache.json"):
    """
    将清洗后的数据导出为JSON文件，供外卖助手加载
    """
    records = df.to_dict(orient="records")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"已导出 {len(records)} 条数据到 {output_file}")

if __name__ == "__main__":
    # 使用示例：
    # 1. 如果是CSV文件
    # df = load_restaurant_data("your_file.csv", "csv")

    # 2. 如果是Excel文件
    df = load_restaurant_data("店铺名单.xlsx", "excel")

    # 数据清洗
    df_clean = preprocess_data(df)
    print("数据预览：")
    print(df_clean.head())

    # 导出给助手使用
    export_for_assistant(df_clean)