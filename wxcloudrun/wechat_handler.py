import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
from flask import make_response, request
from wxcloudrun import app
from wxcloudrun import feishu_service


def wechat():
    if request.method == 'GET':
        token = os.environ.get('WECHAT_TOKEN') or 'abc123'
        signature = request.args.get('signature')
        timestamp = request.args.get('timestamp')
        nonce = request.args.get('nonce')
        echostr = request.args.get('echostr')

        if not all([signature, timestamp, nonce, echostr]):
            return '参数缺失'

        tmp_list = [token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = ''.join(tmp_list)
        tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()

        if tmp_str == signature:
            return echostr
        else:
            return '验证失败'

    elif request.method == 'POST':
        xml_data = request.data
        root = ET.fromstring(xml_data)

        msg_type = root.find('MsgType').text
        print(f"收到消息类型: {msg_type}")

        if msg_type == 'text':
            content = root.find('Content').text
            if content:
                # 检查是否是表情包占位文本
                if content.startswith('[') and content.endswith(']'):
                    print(f"收到表情包占位文本: {content}")
                    feishu_service.send_to_feishu_topic("text", {"text": f"📨 {content}"})
                else:
                    print(f"收到文本消息: {content}")
                    feishu_service.send_to_feishu_topic("text", {"text": content})
            return reply_text(root, "已收到文本消息")

        elif msg_type == 'image':
            media_id = root.find('MediaId').text
            print(f"收到图片消息，MediaId: {media_id}")
            image_data = get_media_from_wechat(media_id)
            if image_data:
                image_key = feishu_service.upload_image(image_data)
                if image_key:
                    feishu_service.send_to_feishu_topic("image", {"image_key": image_key})
            return reply_text(root, "已收到图片")

        elif msg_type == 'video':
            media_id = root.find('MediaId').text
            thumb_media_id = root.find('ThumbMediaId').text if root.find('ThumbMediaId') is not None else ""
            print(f"收到视频消息，MediaId: {media_id}, ThumbMediaId: {thumb_media_id}")
            # 获取视频封面图
            if thumb_media_id:
                thumb_data = get_media_from_wechat(thumb_media_id)
                if thumb_data:
                    image_key = feishu_service.upload_image(thumb_data)
                    if image_key:
                        feishu_service.send_to_feishu_topic("image", {"image_key": image_key})
            return reply_text(root, "已收到视频")

        elif msg_type == 'voice':
            media_id = root.find('MediaId').text
            print(f"收到语音消息，MediaId: {media_id}")
            feishu_service.send_to_feishu_topic("text", {"text": "🔊 收到一条语音消息"})
            return reply_text(root, "已收到语音")

        elif msg_type == 'emoji':
            content = root.find('Content').text
            emoji_md5 = root.find('EmojiMd5').text if root.find('EmojiMd5') is not None else ""
            print(f"收到表情包消息: {content}, emoji_md5: {emoji_md5}")
            feishu_service.send_to_feishu_topic("text", {"text": "📨 收到一个微信表情包"})
            return reply_text(root, "已收到表情包")

        elif msg_type == 'location':
            location_x = root.find('Location_X').text
            location_y = root.find('Location_Y').text
            label = root.find('Label').text if root.find('Label') is not None else ""
            print(f"收到位置消息: ({location_x}, {location_y}), 标签: {label}")
            feishu_service.send_to_feishu_topic("text", {"text": f"📍 位置: {label}"})
            return reply_text(root, "已收到位置")

        elif msg_type == 'news':
            articles = []
            for item in root.findall('.//item'):
                article = {
                    "title": item.find('Title').text or "",
                    "description": item.find('Description').text or "",
                    "pic_url": item.find('PicUrl').text or "",
                    "url": item.find('Url').text or ""
                }
                articles.append(article)
            print(f"收到图文消息，共 {len(articles)} 篇文章")
            for article in articles:
                feishu_service.send_to_feishu_topic("news", article)
            return reply_text(root, "已收到图文消息")

        else:
            print(f"收到未处理的消息类型: {msg_type}")
            print(f"原始消息: {xml_data.decode('utf-8')}")
            return reply_text(root, f"收到消息类型: {msg_type}")


def reply_text(root, content):
    """回复文本消息"""
    reply_text = f"""