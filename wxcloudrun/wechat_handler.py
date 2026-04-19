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

        elif msg_type == 'location':
            location_x = root.find('Location_X').text
            location_y = root.find('Location_Y').text
            label = root.find('Label').text if root.find('Label') is not None else ""
            print(f"收到位置消息: ({location_x}, {location_y}), 标签: {label}")
            feishu_service.send_to_feishu_topic("text", {"text": f"📍 位置: {label}"})
            return reply_text(root, "已收到位置")


        elif msg_type == 'emoji':
            content = root.find('Content').text
            emoji_md5 = root.find('EmojiMd5').text if root.find('EmojiMd5') is not None else ""
            print(f"收到表情包消息: {content}, emoji_md5: {emoji_md5}")
            feishu_service.send_to_feishu_topic("text", {"text": "📨 收到一个微信表情包"})
            return reply_text(root, "已收到表情包")

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
            # 兜底处理：打印所有未处理的消息
            print(f"收到未处理的消息类型: {msg_type}")
            print(f"原始消息: {xml_data.decode('utf-8')}")
            return reply_text(root, f"收到消息类型: {msg_type}")


def reply_text(root, content):
    """回复文本消息"""
    reply_text = f"""<xml>
<ToUserName><![CDATA[{root.find('FromUserName').text}]]></ToUserName>
<FromUserName><![CDATA[{root.find('ToUserName').text}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
    response = make_response(reply_text)
    response.content_type = 'text/xml'
    return response


def get_media_from_wechat(media_id):
    """从微信获取图片数据"""
    access_token = get_wechat_access_token()
    if not access_token:
        print("获取图片失败: 无法获取微信 access_token")
        return None

    url = f"https://api.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"
    print(f"正在从微信获取图片...")

    try:
        response = requests.get(url, verify=False)
        content_type = response.headers.get('Content-Type', '')
        print(f"微信响应 Content-Type: {content_type}")

        if response.status_code == 200:
            if 'application/json' in content_type:
                error_data = response.json()
                print(f"获取图片失败(微信返回错误): {error_data}")
                return None
            print(f"获取图片成功，数据大小: {len(response.content)} bytes")
            return response.content
        else:
            print(f"获取图片失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"获取图片异常: {e}")

    return None


def get_wechat_access_token():
    """获取微信 Access Token"""
    app_id = os.environ.get('WECHAT_APP_ID')
    app_secret = os.environ.get('WECHAT_APP_SECRET')

    if not app_id or not app_secret:
        print("未配置微信 APP ID 或 APP Secret")
        return None

    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'errcode' in data and data['errcode'] != 0:
                print(f"微信 API 错误: errcode={data['errcode']}, errmsg={data.get('errmsg')}")
                return None
            token = data.get('access_token')
            if token:
                print(f"获取微信 access_token 成功")
                return token
    except Exception as e:
        print(f"获取 access token 异常: {e}")

    return None
