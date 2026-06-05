import json
import time
import requests
import urllib3

urllib3.disable_warnings()

# 飞书配置
FEISHU_APP_ID = "cli_a9387bd30a38dcef"
FEISHU_APP_SECRET = "nhW0zacGRkbMT1BVwbQ5IiHqEEoWEGfI"
FEISHU_CHAT_ID = "oc_d45999fdd3504c9567c52cea710a5314"


def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=data, verify=False, timeout=10)
    if resp.status_code == 200:
        result = resp.json()
        if "tenant_access_token" in result:
            return result["tenant_access_token"]
    print(f"获取飞书token失败: {resp.text}")
    return None


def upload_image(image_data) -> str:
    """上传图片到飞书（jpg/png专用）返回 image_key"""
    token = get_feishu_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers=headers,
            data={"image_type": "message"},
            files={"image": ("Image.jpg", image_data, "image/jpeg")},
            verify=False,
            timeout=20
        )
        result = resp.json()
        if result.get("code") == 0:
            return result["data"]["image_key"]
        else:
            print(f"上传图片失败: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"上传图片异常: {e}")
        return None


def upload_file(file_bytes, file_suffix="gif") -> str:
    token = get_feishu_token()
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    filename = f"temp.{file_suffix}"
    try:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/files",  # ✅ 去掉 /upload
            headers=headers,
            data={"file_type": "stream", "file_name": filename},  # ✅ stream + file_name
            files={"file": (filename, file_bytes, "image/gif")},
            verify=False,
            timeout=30
        )
        res = resp.json()
        if res.get("code") == 0:
            return res["data"]["file_key"]
        else:
            print(f"文件上传失败:{res.get('msg')}")
            return None
    except Exception as e:
        print(f"上传文件异常:{e}")
        return None


def send_image_message(chat_id: str, image_key: str):
    """发送图片消息"""
    token = get_feishu_token()
    if not token:
        return

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"receive_id": chat_id, "msg_type": "image", "content": json.dumps({"image_key": image_key})}

    try:
        resp = requests.post(url, headers=headers, json=data, verify=False, timeout=15)
        result = resp.json()
        if result.get("code") == 0:
            print("图片消息发送成功")
        else:
            print(f"发送图片消息失败: {result.get('msg')}")
    except Exception as e:
        print(f"发送图片消息异常: {e}")


def send_file_message(chat_id: str, file_key: str):
    """发送GIF/文件消息"""
    token = get_feishu_token()
    if not token:
        return
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "receive_id": chat_id,
        "msg_type": "file",
        "content": json.dumps({"file_key": file_key})
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        res = resp.json()
        if res.get("code") == 0:
            print("GIF动图发送成功")
        else:
            print(f"发送文件失败:{res.get('msg')}")
    except Exception as e:
        print(f"发送文件异常:{e}")


def send_text_message(chat_id: str, text: str):
    """发送文本消息"""
    token = get_feishu_token()
    if not token:
        return

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"receive_id": chat_id, "msg_type": "text", "content": json.dumps({"text": text})}

    try:
        resp = requests.post(url, headers=headers, json=data, verify=False, timeout=15)
        result = resp.json()
        if result.get("code") == 0:
            print("文本消息发送成功")
        else:
            print(f"发送文本消息失败: {result.get('msg')}")
    except Exception as e:
        print(f"发送文本消息异常: {e}")


def send_card_message(chat_id: str, title: str, description: str, url: str = ""):
    """发送卡片消息"""
    token = get_feishu_token()
    if not token:
        return

    api_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    elements = [
        {"tag": "div", "text": {"tag": "plain_text", "content": f"📝 {title}"}},
        {"tag": "div", "text": {"tag": "markdown", "content": description}}
    ]

    if url:
        elements.append({"tag": "action", "actions": [
            {"tag": "button", "text": {"tag": "plain_text", "content": "查看原文"}, "type": "primary", "url": url}]})

    card = {"config": {"wide_screen_mode": True}, "elements": elements}
    data = {"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(card)}

    try:
        resp = requests.post(api_url, headers=headers, json=data, verify=False, timeout=15)
        result = resp.json()
        if result.get("code") == 0:
            print("卡片消息发送成功")
        else:
            print(f"发送卡片消息失败: {result.get('msg')}")
    except Exception as e:
        print(f"发送卡片消息异常: {e}")


def send_to_feishu_topic(msg_type: str, content: dict):
    """统一分发发送：text/image/file/news"""
    if msg_type == "image":
        image_key = content.get("image_key")
        if image_key:
            send_image_message(FEISHU_CHAT_ID, image_key)
    elif msg_type == "file":
        file_key = content.get("file_key")
        if file_key:
            send_file_message(FEISHU_CHAT_ID, file_key)
    elif msg_type == "news":
        title = content.get("title", "图文消息")
        description = content.get("description", "")
        url = content.get("url", "")
        send_card_message(FEISHU_CHAT_ID, title, description, url)
    elif msg_type == "text":
        send_text_message(FEISHU_CHAT_ID, content.get("text", ""))

    return True