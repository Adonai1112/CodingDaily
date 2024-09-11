import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import base64
from flask import make_response
from. import app


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
        tmp_str = hashlib.sha1(tmp_str.encode('utf - 8')).hexdigest()

        if tmp_str == signature:
            return echostr
        else:
            return '验证失败'

    elif request.method == 'POST':
        xml_data = request.data
        root = ET.fromstring(xml_data)

        msg_type = root.find('MsgType').text
        if msg_type == 'text':
            content = root.find('Content').text
            print(f"收到文本消息: {content}")

            # 发送文本消息到飞书
            send_text_to_feishu(content)

            # 回复文本消息
            reply_text = """
            <xml>
            <ToUserName><![CDATA[{}]]></ToUserName>
            <FromUserName><![CDATA[{}]]></FromUserName>
            <CreateTime>{}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[你发送的是文本消息：{}]]></Content>
            </xml>
            """.format(root.find('FromUserName').text, root.find('ToUserName').text,
                       int(time.time()), content)
            response = make_response(reply_text)
            response.content_type = 'text/xml'
            return response

        elif msg_type == 'image':
            media_id = root.find('MediaId').text
            print(f"收到图片消息，MediaId: {media_id}")

            # 获取图片并发送到飞书
            image_data = get_image_from_wechat(media_id)
            feishu_webhook_url = app.config.get('FEISHU_WEBHOOK_URL')
            if feishu_webhook_url:
                send_image_to_feishu(image_data, feishu_webhook_url)
            else:
                print("未配置飞书 Webhook 地址")


def send_text_to_feishu(text):
    feishu_webhook_url = app.config.get('FEISHU_WEBHOOK_URL')
    if feishu_webhook_url:
        headers = {'Content-Type': 'application/json'}
        data = {"msg_type": "text", "content": {"text": text}}
        try:
            response = requests.post(feishu_webhook_url, json=data, headers=headers)
            if response.status_code!= 200:
                print(f"发送文本消息到飞书失败: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"发送文本消息到飞书时发生网络错误: {e}")
    else:
        print("未配置飞书 Webhook 地址")


def get_image_from_wechat(media_id):
    access_token = get_wechat_access_token()
    if access_token:
        url = f"https://api.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                image_data = response.content
                return image_data
            else:
                print(f"获取图片失败: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"获取图片时发生网络错误: {e}")
    else:
        print("获取微信 access token 失败，无法获取图片")
        return None


def get_wechat_access_token():
    app_id = os.environ.get('WECHAT_APP_ID')
    app_secret = os.environ.get('WECHAT_APP_SECRET')

    if app_id and app_secret:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            else:
                print(f"获取微信 access token 失败: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"获取微信 access token 时发生网络错误: {e}")
    else:
        print("未配置微信 APP ID 或 APP Secret，无法获取 access token")
        return None


def send_image_to_feishu(image_data, feishu_webhook_url):
    if image_data and feishu_webhook_url:
        image_base64 = base64.b64encode(image_data).decode('utf - 8')
        headers = {'Content-Type': 'application/json'}
        data = {
            "msg_type": "image",
            "content": {
                "image_key": image_base64
            }
        }

        try:
            response = requests.post(feishu_webhook_url, json=data, headers=headers)
            if response.status_code!= 200:
                print(f"发送图片消息到飞书失败: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"发送图片消息到飞书时发生网络错误: {e}")
    elif not feishu_webhook_url:
        print("未配置飞书 Webhook 地址")
    else:
        print("没有图片数据可发送")