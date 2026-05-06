import streamlit as st
import os
import json
from openai import OpenAI

# ---------- 导入工具模块 ----------
from tools import (
    get_top_rated_restaurants,
    recommend_food_with_images,
    TOOLS,
    execute_tool,
)

# ---------- 页面配置 ----------
st.set_page_config(page_title=" 智能外卖助手", page_icon="🍜", layout="wide")
st.title(" 智能外卖助手")

# ---------- 初始化 DeepSeek 客户端 ----------
client = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

# ---------- 会话状态初始化 ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是智能外卖助手。你可以查订单、推荐美食、记住用户的偏好。请友好简洁地回复。当用户说'就这家'时，主动调用 confirm_choice 记录喜好。"}
    ]

if "display_restaurants" not in st.session_state:
    # 默认展示高分店铺
    st.session_state.display_restaurants = get_top_rated_restaurants(6)
    st.session_state.is_recommendation = False

# ---------- 辅助函数：渲染店铺卡片 ----------
def render_restaurant_cards(restaurants, title="🏆 为你推荐"):
    st.subheader(title)
    if not restaurants:
        st.info("暂无符合条件的餐厅，请试试其他条件")
        return

    # 每行显示 3 个卡片
    cols_per_row = 3
    for i in range(0, len(restaurants), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, restaurant in enumerate(restaurants[i:i+cols_per_row]):
            with cols[j]:
                img_url = restaurant.get("主图", "")
                if img_url:
                    try:
                        st.image(img_url, use_container_width=True)
                    except:
                        st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)

                # 餐厅名称 + 评分
                st.markdown(f"**{restaurant.get('name', '未知')}**")
                score = restaurant.get("综合评分", restaurant.get("评分", 0))
                price = restaurant.get("价格", "N/A")
                st.caption(f"⭐ {score} | 人均 ¥{price}")

                tags = restaurant.get("口味标签组合", "")
                if tags:
                    st.caption(f"🏷️ {tags}")

                dishes = restaurant.get("菜品", "")
                if dishes:
                    # 限制显示长度，避免卡片过高
                    short_dishes = dishes[:60] + "..." if len(dishes) > 60 else dishes
                    st.caption(f"🍽️ {short_dishes}")

# ---------- 渲染当前卡片区域 ----------
if st.session_state.is_recommendation:
    render_restaurant_cards(st.session_state.display_restaurants, "🎯 智能推荐结果")
else:
    render_restaurant_cards(st.session_state.display_restaurants, "🏆 高分好店")

# ---------- 聊天历史显示 ----------
st.markdown("---")
with st.container():
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                # 如果消息中包含 tool_calls，折叠显示（避免干扰）
                if "tool_calls" in msg:
                    st.caption("🔧 调用工具中...")
                else:
                    st.markdown(msg.get("content", ""))

# ---------- 用户输入 ----------
prompt = st.chat_input("输入您的问题，例如：推荐辣的餐厅，或者'就这家吧'")
if prompt:
    # 1. 添加用户消息到历史
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用 DeepSeek 进行工具调用循环
    with st.chat_message("assistant"):
        # 用于 API 调用的消息列表（不含界面工具消息）
        api_messages = st.session_state.messages.copy()
        # 循环控制
        max_turns = 5
        turn = 0
        final_reply = ""

        while turn < max_turns:
            turn += 1
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=api_messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=False
            )
            msg = response.choices[0].message

            # 如果没有工具调用，直接显示回复
            if not msg.tool_calls:
                final_reply = msg.content or "好的，请告诉我更多需求。"
                st.markdown(final_reply)
                st.session_state.messages.append({"role": "assistant", "content": final_reply})
                break

            # 有工具调用
            # 将助手消息（含 tool_calls）加入历史
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in msg.tool_calls
                ]
            }
            st.session_state.messages.append(assistant_msg)
            api_messages.append(assistant_msg)

            # 处理每个工具调用
            for tc in msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)

                # 特殊处理：如果是推荐，更新卡片数据，并生成简短回复
                if func_name == "recommend_food":
                    rec_list = recommend_food_with_images(
                        func_args.get("preference", ""),
                        func_args.get("max_price"),
                        func_args.get("min_rating", 0.0)
                    )
                    # 更新页面卡片
                    st.session_state.display_restaurants = rec_list
                    st.session_state.is_recommendation = True

                    if rec_list:
                        text_result = "已为您找到以下餐厅，卡片已更新。"
                    else:
                        text_result = "没有完全匹配的餐厅，试试放宽条件吧～"
                else:
                    # 其他工具（查订单、确认偏好等）正常执行
                    text_result = execute_tool(func_name, func_args)

                # 将工具结果加入历史
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": text_result
                }
                st.session_state.messages.append(tool_msg)
                api_messages.append(tool_msg)

            # 循环继续，让模型根据工具结果生成最终回复
            continue

        # 如果循环结束却未获得回复（达到上限）
        if not final_reply and turn >= max_turns:
            final_reply = "抱歉，系统处理超时，请简化您的问题再试。"
            st.markdown(final_reply)
            st.session_state.messages.append({"role": "assistant", "content": final_reply})

    # 强制刷新，使卡片区域更新
    st.rerun()