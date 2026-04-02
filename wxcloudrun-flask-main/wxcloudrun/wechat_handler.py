import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import io
from flask import make_response, request
from wxcloudrun import app
from wxcloudrun import feishu_service


def wechat():
    if request.method == 'GET':
        token = os.environ.get('WECHAT_TOKEN')
        signature = request.args.get('signature')
        timestamp = request.args.get('timestamp')
        nonce = request.args.get('nonce')
        echostr = request.args.get('echostr')

        # 验证消息来自微信服务器
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
            print(f"收到文本消息: {content}")

            # 发送到飞书话题
            feishu_service.send_to_feishu_topic("text", {"text": content})

            # 回复确认
            return reply_text(root, "已收到文本消息")

        elif msg_type == 'image':
            media_id = root.find('MediaId').text
            print(f"收到图片消息，MediaId: {media_id}")

            # 下载图片
            image_data = get_image_from_wechat(media_id)
            if image_data:
                # 上传到飞书
                image_key = feishu_service.upload_image(image_data)
                if image_key:
                    feishu_service.send_to_feishu_topic("image", {"image_key": image_key})

            return reply_text(root, "已收到图片")

        elif msg_type == 'news':
            # 图文消息
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

            # 发送到飞书
            for article in articles:
                feishu_service.send_to_feishu_topic("news", article)

            return reply_text(root, "已收到图文消息")

        return "success"


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


def get_image_from_wechat(media_id):
    """从微信获取图片数据"""
    access_token = get_wechat_access_token()
    if not access_token:
        return None

    url = f"https://api.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            print(f"获取图片失败: {response.text}")
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
            return data.get('access_token')
    except Exception as e:
        print(f"获取 access token 异常: {e}")

    return None
