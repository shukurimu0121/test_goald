from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from app import app, connect_to_database
from flask_session import Session
from datetime import datetime
import random
import os
import psycopg2
import schedule
from time import sleep
import time
from psycopg2.extras import DictCursor
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
import pytz



# linebot 
#Token取得

# ローカル環境
# YOUR_CHANNEL_ACCESS_TOKEN = "Z14pLqOO864QqOaAEpqTkUwPRRGzmTYAHpVZz2W3CTuMv/CNWib8Qqpyj0q1ZckLH6uoOpmB5VEW1h8alKxVACy58y8IecCrsY5dciYaBD1v51p4189WlmnUauYwG8DWtsCxDnUDBvpxqKpc9FNAMwdB04t89/1O/w1cDnyilFU="
# YOUR_CHANNEL_SECRET = "d47e7c03339338aa4d2c39d6c2cb870d"


# 本番環境
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# アプリのURL
APP_URL = "https://pot-of-goald-f14a2468eebb.herokuapp.com/"

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# Webhook
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# Message handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # line menu message
    # 部屋を登録
    if event.message.text == "部屋を登録":
        # 部屋番号を入力してくださいと返信
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="部屋番号を入力してください")
        )

    if event.message.text == "登録を解除":
        # 新しい部屋番号を入力してくださいと返信
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="新しい部屋番号を入力してください")
        )
    
    # 正の整数が入力されたとき
    if event.message.text.isdigit():
        line_user_id = event.source.user_id
        room_id = int(event.message.text)

        # 有効な部屋番号か確認
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
                    room = cur.fetchall()
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"エラー: {str(e)}")
            )

        # 無効な部屋番号の場合
        if len(room) == 0:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="無効な部屋番号です")
            )
        
        # 既に部屋に登録されているか確認
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM line_users WHERE line_user_id = %s", (line_user_id,))
                    line_user = cur.fetchall()
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"エラー: {str(e)}")
            )
        
        # 既に部屋に登録されている場合、room_idを更新
        if len(line_user) != 0:
            try:
                with connect_to_database() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE line_users SET room_id = %s WHERE line_user_id = %s", (room_id, line_user_id))
                    conn.commit()
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"エラー: {str(e)}")
                )
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="部屋番号を更新しました")
            )
        
        # 部屋に登録されていない場合、部屋を登録
        else:
            try:
                with connect_to_database() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO line_users (line_user_id, room_id) VALUES (%s, %s)", (line_user_id, room_id))
                    conn.commit()
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"エラー: {str(e)}")
                )
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="部屋番号を登録しました")
            )
    
    # ランキング
    if event.message.text == "ランキング":
        # get line user id
        line_user_id = event.source.user_id

        # push message to the line user
        push_progress_message(line_user_id)
    
    # 使い方
    if event.message.text == "使い方":
        how_to_use_text = "部屋を登録：参加中のルームIDを入力して部屋を登録します\n登録を解除：登録している部屋を解除して、新たな部屋を登録します。\nランキング：部屋に参加しているメンバーの目標達成率ランキングを表示します\n使い方：使い方を表示します\nやる気がなくなった：やる気がなくなったときのヒントを表示します\nアプリ：アプリへ移動します"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=how_to_use_text)
        )
    
    # やる気がなくなったとき用のヒント
    TIPS = ["目標が難しすぎると、やる気がなくなります。目標を小さく設定してみましょう。",
            "ポモドーロテクニックを試してみましょう。25分間集中して作業し、5分間休憩します。これを繰り返します。",
            "目標を達成するためには、習慣化が必要です。毎日少しずつでも続けてみましょう。",
            "何のために目標を設定したのか、最終的な目標は何かを思い出しましょう。",
            "目標を達成することがどう自分の人生に影響するかを考えてみましょう。"
            ]

    # やる気がなくなった
    if event.message.text == "やる気がなくなった":
        # ランダムにヒントを表示
        tip = random.choice(TIPS)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=tip)
        )

    # else
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="個別のメッセージには対応していません。使い方を参考に、メニュー画面を操作してください。")
        )

# Push message to the line users
def push_progress_message(line_user_id):
    # where user in a room
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM line_users WHERE line_user_id = %s", (line_user_id,))
                line_user = cur.fetchall()
    except Exception as e:
        # send error to the line user
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=f"エラー: {str(e)}")
        )
    
    # get goals and progress rate in the room, and sort by progress rate
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT user_id FROM rooms WHERE room_id = %s", (line_user[0]["room_id"],))
                user_ids = [row[0] for row in cur.fetchall()]
    except Exception as e:
        # send error to the line user
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=f"エラー: {str(e)}")
        )

    # get goals and progress rate in the room, and sort by progress rate
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM goals WHERE user_id IN %s ORDER BY progress_rate DESC", (tuple(user_ids),))
                users_goals_info = cur.fetchall()
    except Exception as e:
        # send error to the line user
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=f"エラー: {str(e)}")
        )

    # count the number of members
    number_of_members = len(users_goals_info)

    # push message to the line user
    try:
        # send members' goals and progress rate to the line user
        message = f"現在のランキングをお知らせします\n\n"
        for i in range(number_of_members):
            message += f"{i+1}位：{users_goals_info[i]['goal']} {users_goals_info[i]['progress_rate']}%\n"
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=message)
        )        

    except Exception as e:
        # send error to the line user
        line_bot_api.push_message(
            line_user_id,
            TextSendMessage(text=f"エラー: {str(e)}")
        )

# scheduled message to the line users
def schedule_message():
    # get all line users
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM line_users")
                line_users = cur.fetchall()
    except Exception as e:
        return str(e)
    
    # push message to the line users
    for line_user in line_users:
        line_bot_api.push_message(
            line_user["line_user_id"],
            TextSendMessage(text="進捗を報告しましょう！" + APP_URL)
        )

# register scheduled message
schedule.every(2).minutes.do(schedule_message)

# run scheduled message
while True:
    schedule.run_pending()
    time.sleep(1)



