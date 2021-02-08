# -*- coding: utf-8 -*-
import time
import io
import re

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from pytils import numeral
import requests, yaml

from functions import get_time


with open("config.yaml") as ymlFile:
    config = yaml.load(ymlFile.read(), Loader=yaml.Loader)


class Utils(object):
    def __init__(self, upload):
        self.upload = upload

    def get_photo_by_url(self, url):
        r = requests.get(url)
        image = io.BytesIO(r.content)

        # Отправляем фото в беседу
        response = self.upload.photo_messages(photos=image)[0]
        attachment = "photo{}_{}".format(response["owner_id"], response["id"])
        return attachment

class User(object):
    """Функции для работы с пользователем"""
    def __init__(self, vk, upload):
        self.vk = vk
        self.upload = upload
        self.Utils = Utils(upload=upload)

    def get_username(self, user_id):
        user_info = self.vk.users.get(user_ids=user_id)[0]
        username = "{} {}".format(
            user_info["first_name"],
            user_info["last_name"]
        )
        return f"[id{user_id}|{username}]"

    def get_user_last_activity(self, user_id):
        last_activity = self.vk.messages.getLastActivity(
            user_id=user_id
        )
        if last_activity["online"]:
            return "Сейчас онлайн\n"
        else:
            delta = time.time() - last_activity["time"]
            return f"Был в сети {get_time(delta)} назад\n"

    def get_user_profile_photo(self, user_id):
        photo_id = self.vk.photos.get(
            owner_id=user_id,
            album_id="profile"
        )["items"][-1]["id"]
        attachment = "photo{}_{}".format(user_id, photo_id)
        return attachment

    def get_user_status(self):
        status = self.user_info["status"]
        if status != "":
            return f"Статус: {status}\n"
        return ""

    def get_user_photos(self):
        count = self.user_info["counters"]["photos"]
        return f"{count} фото\n"

    def get_user_audios(self):
        count = self.user_info["counters"]["audios"]
        return "{}\n".format(
            numeral.get_plural(count, "аудиозапись, аудиозаписи, аудиозаписей")
        )

    def get_user_videos(self):
        count = self.user_info["counters"]["videos"]
        return f"{count} видео\n"

    def get_user_friends(self):
        count = self.user_info["counters"]["friends"]
        return "{}\n".format(
            numeral.get_plural(count, "друг, друга, друзей")
        )

    def get_user_followers(self):
        count = self.user_info["counters"]["followers"]
        return "{}\n".format(
            numeral.get_plural(count, "подписчик, подписчика, подписчиков")
        )

    def get_user_groups(self):
        count = self.user_info["counters"]["groups"]
        return "{}\n".format(
            numeral.get_plural(count, "группа, группы, групп")
        )

    def get_user_info(self, user_id):
        self.user_info = self.vk.users.get(
            user_ids=user_id,
            fields="status, counters"
        )[0]

        if self.user_info["is_closed"]:
            # Профиль пользователя закрыт
            res = "{} {} {} {} {} {}".format(
                f"{self.get_username(user_id)}\n",
                f"id - {user_id}\n",
                self.get_user_last_activity(user_id),
                self.get_user_status(),
                "Профиль закрыт ❌\n",
                "Аватарка"
            )
        else:
            # Профиль пользователя открыт
            res = "{} {} {} {} {} {} {} {} {} {} {} {}".format(
                f"{self.get_username(user_id)}\n",
                f"id - {user_id}\n",
                self.get_user_last_activity(user_id),
                self.get_user_status(),
                "Профиль открыт ✅\n",
                self.get_user_photos(),
                self.get_user_audios(),
                self.get_user_videos(),
                self.get_user_friends(),
                self.get_user_followers(),
                self.get_user_groups(),
                "Аватарка"
            )

        return {
            "message": res,
            "attachment": self.get_user_profile_photo(user_id)
        }

class Group(object):
    # Функции для работы с группами
    def __init__(self, vk, upload):
        self.vk = vk
        self.upload = upload

        self.Utils = Utils(upload = self.upload)

        self.User = User(
            vk=vk,
            upload=upload
        )

    def get_group_owner(self, group_id):
        try:
            owner_id = self.vk.groups.getMembers(
                group_id=group_id,
                filter="managers"
            )["items"][0]["id"]
            return f"Создатель - {self.User.get_username(owner_id)}\n"

        except vk_api.exceptions.ApiError:
            return ""

    def get_group_info(self, group_id):
        """Отправляет сообщение с информацией о группе."""
        group_info = self.vk.groups.getById(group_id=group_id)[0]

        max_size = list(group_info)[-1]
        photo_url = group_info[max_size]

        res = "{} {} {} {}".format(
            f"{group_info['name']}\n",
            f"id - {group_info['id']}\n",
            self.get_group_owner(group_id),
            "Аватарка",
        )

        return {
            "message": res,
            "attachment": self.Utils.get_photo_by_url(photo_url)
        }

class Chat(object):
    def __init__(self, vk, upload, bot):
        self.vk = vk
        self.upload = upload
        self.bot = bot

        self.Utils = Utils(upload = self.upload)

        self.User = User(
            vk = self.vk,
            upload = self.upload
        )

    def get_chat_info(self, chat_id):
        """Отправляет сообщение с информацией о беседе."""
        chat_info = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + chat_id,
            group_id=config["group"]["group_id"]
        )["items"][0]["chat_settings"]

        chat_name = chat_info["title"]
        members_count = chat_info["members_count"]
        owner_id = chat_info["owner_id"]

        # Получаем url фото
        sizes = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + chat_id,
            group_id=config["group"]["group_id"]
        )["items"][0]["chat_settings"]["photo"]
        max_size = list(sizes)[-2]
        photo_url = sizes[max_size]

        res = "{} {} {} {}".format(
            f"Название - {chat_name}\n",
            "{}\n".format(numeral.get_plural(members_count, "участник, участника, участников")),
            f"Создатель - {self.User.get_username(owner_id)}\n",
            "Аватарка"
        )
        return {
            "message": res,
            "attachment": self.Utils.get_photo_by_url(photo_url)
        }

    def check_rights(self, user_id, chat_id):
        """Проверяем, является ли пользователь администратором беседы"""
        chat_members = self.bot.messages.getConversationMembers(
            peer_id=2000000000 + chat_id,
            group_id=config["group"]["group_id"],
        )["items"]

        is_admin = False

        for user in chat_members:
            if user["member_id"] == user_id and "is_admin" in user and not is_admin:
                is_admin = True
                break

        return is_admin

    def ban_user(self, from_id, user_id, chat_id):
        if self.check_rights(from_id, chat_id):
            self.bot.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )
            return True
        else:
            return False

class Bot:
    def auth(self):
        """Авторизация бота."""
        self.authorize = vk_api.VkApi(token=config["group"]["group_token"])
        self.longpoll = VkBotLongPoll(
            self.authorize,
            group_id=config["group"]["group_id"]
        )

        self.upload = vk_api.VkUpload(self.authorize)
        self.bot = self.authorize.get_api()

        vk_session = vk_api.VkApi(
            token=config["access_token"]["token"]
        )

        self.vk = vk_session.get_api()

        self.Utils = Utils(upload=self.upload)

        self.User = User(
            vk=self.vk,
            upload=self.upload
        )

        self.Group = Group(
            vk=self.vk,
            upload=self.upload
        )

        self.Chat = Chat(
            vk=self.vk,
            upload=self.upload,
            bot=self.bot
        )

    def get_help(self):
        res = "{}{}{}{}".format(
            "Список команд\n",
            "!инфо беседа\n",
            "!инфо @(Имя пользователя)\n\n",
            "Доступно только администраторам\n"
            "!бан @(Имя пользователя)"
        )
        return res

    def check_message(self, received_message):
        if re.match("!инфо", received_message):
            if received_message == "!инфо беседа":
                data = self.Chat.get_chat_info(chat_id=self.chat_id)
                self.bot.messages.send(
                    chat_id=self.chat_id,
                    message=data["message"],
                    attachment=data["attachment"],
                    random_id=get_random_id()
                )
            elif re.match("!инфо id", received_message):
                user_id = int(received_message[8:17])
                data = self.User.get_user_info(user_id)
                self.bot.messages.send(
                    chat_id=self.chat_id,
                    message=data["message"],
                    attachment=data["attachment"],
                    random_id=get_random_id()
                )
            elif re.match("!инфо club", received_message):
                group_id = int(received_message[10:19])
                data = self.Group.get_group_info(group_id)
                self.bot.messages.send(
                    chat_id=self.chat_id,
                    message=data["message"],
                    attachment=data["attachment"],
                    random_id=get_random_id()
                )
            else:
                self.bot.messages(
                    chat_id=self.chat_id,
                    message="Такой команды не существует",
                    random_id=get_random_id()
                )
        elif re.match("!бан id", received_message):
            user_id = int(received_message[7:16])
            success = self.Chat.ban_user(
                from_id=self.from_id,
                user_id=user_id,
                chat_id=self.chat_id
            )

            if success:
                self.bot.messages.send(
                    chat_id=self.chat_id,
                    message="Пользователь {} забанен".format(
                        self.User.get_username(user_id=user_id)
                    ),
                    random_id=get_random_id()
                )
            else:
                self.bot.messages.send(
                    chat_id=self.chat_id,
                    message="У вас недостаточно прав для использования этой команды",
                    random_id=get_random_id()
                )
        elif received_message == "!help":
            self.bot.messages.send(
                chat_id=self.chat_id,
                message=self.get_help(),
                random_id=get_random_id()
            )

    def run(self):
        self.auth()

        print("Начинаю мониторинг сообщений...")

        """Отслеживаем каждое событие в беседе."""
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat and event.message.get("text") != "":
                received_message = event.message.get("text").lower().replace("[", "").replace("]", "")
                self.chat_id = event.chat_id
                self.from_id = event.message.get("from_id")
                self.check_message(received_message)


if __name__ == "__main__":
    VkBot = Bot()
    VkBot.run()
