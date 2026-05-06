import json
import os
from collections import defaultdict

PROFILE_FILE = "user_profile.json"

# 默认画像
DEFAULT_PROFILE = {
    "preferences": defaultdict(float),  # 口味偏好权重
    "price_range": {"min": 0, "max": 100},
    "favorite_tags": defaultdict(float),
    "history": []  # 最近10条行为记录
}

def load_profile():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 恢复 defaultdict
            data["preferences"] = defaultdict(float, data.get("preferences", {}))
            data["favorite_tags"] = defaultdict(float, data.get("favorite_tags", {}))
            return data
    return DEFAULT_PROFILE.copy()

def save_profile(profile):
    # 转换 defaultdict 为普通 dict 以便序列化
    profile_copy = profile.copy()
    profile_copy["preferences"] = dict(profile["preferences"])
    profile_copy["favorite_tags"] = dict(profile["favorite_tags"])
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile_copy, f, ensure_ascii=False, indent=2)