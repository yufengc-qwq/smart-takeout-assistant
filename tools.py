import json
from user_profile import load_profile, save_profile

# 加载商家数据
try:
    with open("menu_cache.json", "r", encoding="utf-8") as f:
        MENU_DB = json.load(f)
except:
    MENU_DB = []

fake_orders = {
    "12345": {"status": "骑手已取餐", "eta": "15分钟"},
    "67890": {"status": "商家备餐中", "eta": "25分钟"},
}

def get_order_status(order_id: str) -> str:
    if order_id in fake_orders:
        o = fake_orders[order_id]
        return f"订单 {order_id} 状态：{o['status']}，预计 {o['eta']} 送达。"
    return f"未找到订单 {order_id}，请检查订单号。"

def recommend_food(preference="", max_price=None, min_rating=0.0):
    profile = load_profile()
    candidates = MENU_DB.copy()

    if preference:
        # 将用户输入拆成多个关键词（过滤掉太短的助词）
        keywords = [kw for kw in preference.replace("，", " ").replace(",", " ").split() if len(kw) >= 1]
        if keywords:
            # 条件：只要标签中包含任意一个关键词，即可通过
            candidates = [
                r for r in candidates
                if any(kw in r.get("口味标签组合", "") for kw in keywords)
            ]
    if max_price is not None:
        candidates = [r for r in candidates if r.get("价格", 0) <= max_price]
    if min_rating > 0:
        candidates = [r for r in candidates if r.get("评分", 0) >= min_rating]

    if not candidates:
        return "没有完全匹配的餐厅，试试放宽条件吧～"

    # 融合历史偏好
    def score(r):
        base = r.get("评分", 0)
        tags = r.get("口味标签组合", "")
        bonus = 0.0
        for tag, weight in profile["preferences"].items():
            if tag in tags:
                bonus += weight * 0.5
        for tag, weight in profile["favorite_tags"].items():
            if tag in tags:
                bonus += weight * 0.3
        return base + bonus

    candidates.sort(key=score, reverse=True)
    top3 = candidates[:3]

    rec_text = "🍽️ **为您推荐以下餐厅**\n\n"
    for i, r in enumerate(top3, 1):
        name = r.get("name", "未知")
        price = r.get("价格", "暂无")
        rating = r.get("评分", "暂无")
        tags = r.get("口味标签组合", "")
        dishes = r.get("菜品", "招牌菜待查")
        rec_text += f"{i}. **{name}**  | 人均 ¥{price} | ⭐{rating}\n   🏷️ {tags}\n   🍜 推荐菜：{dishes}\n\n"

    # 记录偏好
    if preference:
        for tag in preference.split():
            profile["preferences"][tag] = profile["preferences"].get(tag, 0) + 0.5
    profile["history"].append({"action": "recommend", "preference": preference})
    save_profile(profile)
    return rec_text

def confirm_choice(restaurant_name: str):
    profile = load_profile()
    r = next((r for r in MENU_DB if r.get("name") == restaurant_name), None)
    if not r:
        return f"没有找到名为 {restaurant_name} 的餐厅。"
    tags = r.get("口味标签组合", "")
    for tag in tags.split():
        profile["favorite_tags"][tag] = profile["favorite_tags"].get(tag, 0) + 2.0
    profile["history"].append({"action": "confirm", "restaurant": restaurant_name})
    save_profile(profile)
    return f"✅ 已记住您喜欢 **{restaurant_name}**，下次会优先推荐类似口味！"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "查询外卖订单状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_food",
            "description": "根据口味、价格和评分推荐餐厅",
            "parameters": {
                "type": "object",
                "properties": {
                    "preference": {"type": "string", "description": "口味偏好，如辣、清淡、日料等"},
                    "max_price": {"type": "number", "description": "最高人均价格"},
                    "min_rating": {"type": "number", "description": "最低评分 (0-5)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_choice",
            "description": "当用户明确选择或喜欢某家餐厅时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_name": {"type": "string", "description": "餐厅名称"}
                },
                "required": ["restaurant_name"]
            }
        }
    }
]

def execute_tool(name: str, arguments: dict) -> str:
    if name == "get_order_status":
        return get_order_status(arguments.get("order_id", ""))
    elif name == "recommend_food":
        return recommend_food(
            arguments.get("preference", ""),
            arguments.get("max_price"),
            arguments.get("min_rating", 0.0)
        )
    elif name == "confirm_choice":
        return confirm_choice(arguments.get("restaurant_name", ""))
    return "未知工具"

def get_top_rated_restaurants(n=6):
    """获取评分最高的 n 家餐厅（用于首页默认展示）"""
    # 过滤掉没有评分或图片的脏数据
    valid = [r for r in MENU_DB if r.get("综合评分", 0) > 0 and r.get("主图")]
    valid.sort(key=lambda x: x.get("综合评分", 0), reverse=True)
    return valid[:n]


def recommend_food_with_images(preference="", max_price=None, min_rating=0.0):
    """
    和 recommend_food 逻辑一致，但返回结构化的结果列表（包含图片等信息），
    供前端直接渲染卡片。
    """
    profile = load_profile()
    candidates = MENU_DB.copy()

    if preference:
        candidates = [r for r in candidates if preference in r.get("口味标签组合", "")]
    if max_price is not None:
        candidates = [r for r in candidates if r.get("价格", 0) <= max_price]
    if min_rating > 0:
        candidates = [r for r in candidates if r.get("综合评分", 0) >= min_rating]

    if not candidates:
        return []

    # 偏好加权（与 recommend_food 一致）
    def score(r):
        base = r.get("综合评分", 0)
        tags = r.get("口味标签组合", "")
        bonus = 0.0
        for tag, weight in profile["preferences"].items():
            if tag in tags:
                bonus += weight * 0.5
        for tag, weight in profile["favorite_tags"].items():
            if tag in tags:
                bonus += weight * 0.3
        return base + bonus

    candidates.sort(key=score, reverse=True)
    top3 = candidates[:3]

    # 记录偏好（如需）
    if preference:
        for tag in preference.split():
            profile["preferences"][tag] = profile["preferences"].get(tag, 0) + 0.5
    profile["history"].append({"action": "recommend", "preference": preference})
    save_profile(profile)

    return top3   # 返回原始字典列表，前端直接取用
