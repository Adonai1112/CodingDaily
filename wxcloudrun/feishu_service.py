import json
import time
import requests
import lark_oapi as lark
from lark_oapi import Client

# 飞书配置
FEISHU_APP_ID = "cli_a9387bd30a38dcef"
FEISHU_APP_SECRET = "nhW0zacGRkbMT1BVwbQ5IiHqEEoWEGfI"
FEISHU_CHAT_ID = "oc_46287e9324ccb3a4d5f64ee920c79142"

# 初始化飞书客户端
client = Client.builder() \
    .app_id(FEISHU_APP_ID) \
    .app_secret(FEISHU_APP_SECRET) \
    .build()


def create_topic(topic_name: str) -> str:
    """创建话题并返回话题ID"""
    try:
        response = client.im.v1.chats[f"{FEISHU_CHAT_ID}"].topics.post(
            lark.CreateChatTopicRequest(
                name=topic_name,
                topic_mode="普通话题"
            )
        )

        if response.code == 0:
            topic_id = response.data.topic.topic_id
            print(f"话题创建成功: {topic_name}, topic_id: {topic_id}")
            return topic_id
        else:
            print(f"创建话题失败: {response.msg}")
            return None
    except Exception as e:
        print(f"创建话题异常: {e}")
        return None


def upload_image(image_data: bytes) -> str:
    """上传图片到飞书并返回 image_key"""
    try:
        response = client.im.v1.images.post(
            lark.CreateImageRequest(
                image_type="message",
                image=image_data
            )
        )

        if response.code == 0:
            return response.data.image_key
        else:
            print(f"上传图片失败: {response.msg}")
            return None
    except Exception as e:
        print(f"上传图片异常: {e}")
        return None


def send_image_message(chat_id: str, image_key: str):
    """发送图片消息到指定话题"""
    try:
        response = client.im.v1.messages.create(
            lark.CreateMessageRequest(
                receive_id_type="chat_id",
                lark.CreateMessageRequestBody(
                    receive_id=chat_id,
                    msg_type="image",
                    content=json.dumps({"image_key": image_key})
                )
            )
        )

        if response.code == 0:
            print(f"图片消息发送成功")
        else:
            print(f"发送图片消息失败: {response.msg}")
    except Exception as e:
        print(f"发送图片消息异常: {e}")


def send_card_message(chat_id: str, title: str, description: str, url: str, image_url: str = None):
    """发送富文本卡片消息"""
    try:
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"📝 {title}"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "markdown",
                    "content": description
                }
            }
        ]

        if url:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "查看原文"
                        },
                        "type": "primary",
                        "url": url
                    }
                ]
            })

        card = {
            "config": {"wide_screen_mode": True},
            "elements": elements
        }

        response = client.im.v1.messages.create(
            lark.CreateMessageRequest(
                receive_id_type="chat_id",
                lark.CreateMessageRequestBody(
                    receive_id=chat_id,
                    msg_type="interactive",
                    content=json.dumps(card)
                )
            )
        )

        if response.code == 0:
            print(f"卡片消息发送成功")
        else:
            print(f"发送卡片消息失败: {response.msg}")
    except Exception as e:
        print(f"发送卡片消息异常: {e}")


def send_to_feishu_topic(msg_type: str, content: dict):
    """统一发送到飞书话题"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    topic_name = f"消息 {timestamp}"

    # 创建话题
    topic_id = create_topic(topic_name)
    if not topic_id:
        print("无法创建话题，发送失败")
        return False

    if msg_type == "image":
        # 发送图片
        image_key = content.get("image_key")
        if image_key:
            send_image_message(topic_id, image_key)

    elif msg_type == "news":
        # 发送图文卡片
        title = content.get("title", "图文消息")
        description = content.get("description", "")
        url = content.get("url", "")
        send_card_message(topic_id, title, description, url)

    elif msg_type == "text":
        # 发送文本
        try:
            response = client.im.v1.messages.create(
                lark.CreateMessageRequest(
                    receive_id_type="chat_id",
                    lark.CreateMessageRequestBody(
                        receive_id=topic_id,
                        msg_type="text",
                        content=json.dumps({"text": content.get("text", "")})
                    )
                )
            )
        except Exception as e:
            print(f"发送文本消息异常: {e}")

    return True
