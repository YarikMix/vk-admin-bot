# -*- coding: utf-8 -*-
import time
import io
import re
from pathlib import Path

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from pytils import numeral
import requests, yaml

from functions import get_time


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR.joinpath("config.yaml")


with open(CONFIG_PATH) as ymlFile:
    config = yaml.load(ymlFile.read(), Loader=yaml.Loader)


class Utils(object):
    def __init__(self, upload):
        self.upload = upload

    def get_photo_by_url(self, url: str) -> str:
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

    def get_username(self, user_id: int) -> str:
        user_info = self.vk.users.get(user_ids=user_id)[0]
        username = "{} {}".format(
            user_info["first_name"],
            user_info["last_name"]
        )
        return f"[id{user_id}|{username}]"

    def get_user_last_activity(self, user_id: int, sex: int) -> str:
        last_activity = self.vk.messages.getLastActivity(
            user_id=user_id
        )
        if last_activity["online"]:
            return "Сейчас онлайн\n"
        else:
            delta = time.time() - last_activity["time"]
            if sex == 1:
                return f"Была в сети {get_time(delta)} назад\n"
            elif sex == 2:
                return f"Был в сети {get_time(delta)} назад\n"
            else:
                pass  # Attack helicopter

    def get_user_profile_photo(self) -> str:
        photo_url = self.user_info["photo_max_orig"]
        if photo_url == "https://vk.com/images/camera_400.png":
            # У пользователя нет аватарки
            return ""
        else:
            attachment = utils.get_photo_by_url(photo_url)
            return attachment

    def get_user_status(self) -> str:
        """Возвращает статус пользователя"""
        status = self.user_info["status"]
        if status != "":
            return f"Статус: {status}\n"

        return ""

    def get_user_photos(self) -> str:
        if "photos" in self.user_info["counters"]:
            count = self.user_info["counters"]["photos"]
            if count != 0:
                return f"{count} фото\n"
        return ""

    def get_user_audios(self) -> str:
        if "audios" in self.user_info["counters"]:
            count = self.user_info["counters"]["audios"]
            if count != 0:
                return "{}\n".format(
                    numeral.get_plural(count, "аудиозапись, аудиозаписи, аудиозаписей")
                )
        return ""

    def get_user_videos(self) -> str:
        if "videos" in self.user_info["counters"]:
            count = self.user_info["counters"]["videos"]
            if count != 0:
                return f"{count} видео\n"

        return ""

    def get_user_friends(self) -> str:
        if "friends" in self.user_info["counters"]:
            count = self.user_info["counters"]["friends"]
            if count != 0:
                return "{}\n".format(
                    numeral.get_plural(count, "друг, друга, друзей")
                )

        return ""

    def get_user_followers(self) -> str:
        if "followers" in self.user_info["counters"]:
            count = self.user_info["counters"]["followers"]
            if count != 0:
                return "{}\n".format(
                    numeral.get_plural(count, "подписчик, подписчика, подписчиков")
                )

        return ""

    def get_user_groups(self) -> str:
        if "groups" in self.user_info["counters"]:
            count = self.user_info["counters"]["groups"]
            if count != 0:
                return "{}\n".format(
                    numeral.get_plural(count, "группа, группы, групп")
                )

        return ""

    def get_user_info(self, user_id: int) -> dict:
        self.user_info = self.vk.users.get(
            user_ids=user_id,
            fields="sex, status, counters, photo_max_orig"
        )[0]

        message = ""
        message += self.get_username(user_id) + "\n"
        message += f"id - {user_id}\n"
        message += self.get_user_last_activity(user_id, self.user_info['sex'])
        message += self.get_user_status()

        if self.user_info["is_closed"]:
            # Профиль пользователя закрыт
            message += "Профиль закрыт ❌\n"
        else:
            # Профиль пользователя открыт
            message += "Профиль открыт ✅\n"
            message += self.get_user_photos()
            message += self.get_user_audios()
            message += self.get_user_videos()
            message += self.get_user_friends()
            message += self.get_user_followers()
            message += self.get_user_groups()

        return {
            "message": message,
            "attachment": self.get_user_profile_photo()
        }


class Group(object):
    """Функции для работы с группами"""
    def __init__(self, vk, upload):
        self.vk = vk
        self.upload = upload

    def get_group_owner(self, group_id: int) -> str:
        try:
            owner_id = self.vk.groups.getMembers(
                group_id=group_id,
                filter="managers"
            )["items"][0]["id"]
            return f"Создатель - {user.get_username(owner_id)}\n"

        except vk_api.exceptions.ApiError:
            return ""

    def get_group_info(self, group_id: int) -> dict:
        """Отправляет сообщение с информацией о группе."""
        group_info = self.vk.groups.getById(group_id=group_id)[0]

        max_size = list(group_info)[-1]
        photo_url = group_info[max_size]

        message = ""
        message += f"{group_info['name']}\n"
        message += f"id - {group_info['id']}\n"
        message += self.get_group_owner(group_id)
        message += "Аватарка"

        return {
            "message": message,
            "attachment": utils.get_photo_by_url(photo_url)
        }


class Chat(object):
    def __init__(self, vk, upload, bot):
        self.vk = vk
        self.upload = upload
        self.bot = bot

    def get_chat_photo(self, chat_info: dict) -> str:
        """
        Вовращает фото беседы если оно у неё есть,
        иначе вовращает пустую строку.
        """
        if "photo" in chat_info:
            sizes = chat_info["photo"]
            max_size = list(sizes)[-2]
            photo_url = sizes[max_size]

            return utils.get_photo_by_url(photo_url)
        else:
            return ""

    def get_chat_info(self, chat_id: int) -> dict:
        """Отправляет сообщение с информацией о беседе."""

        chat_info = self.bot.messages.getConversationsById(
            peer_ids=2000000000 + chat_id,
            group_id=config["group"]["group_id"]
        )["items"][0]["chat_settings"]

        chat_name = chat_info["title"]
        members_count = chat_info["members_count"]
        owner_id = chat_info["owner_id"]

        message = ""
        message += "Название - {chat_name}\n"
        message += "{}\n".format(numeral.get_plural(members_count, "участник, участника, участников"))
        message += f"Создатель - {user.get_username(owner_id)}\n"
        message += "Аватарка"

        return {
            "message": message,
            "attachment": self.get_chat_photo(chat_info)
        }

    def is_admin(self, user_id: int, chat_id: int) -> bool:
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

    def ban_user(self, from_id: int, user_id: int, chat_id: int):
        if from_id == user_id:
            self.bot.messages.send(
                chat_id=chat_id,
                message="Вы не можете забанить себя",
                random_id=get_random_id()
            )

        elif not self.is_admin(from_id,chat_id):
            self.bot.messages.send(
                chat_id=chat_id,
                message="У вас недостаточно прав для использования этой команды",
                random_id=get_random_id()
            )

        elif self.is_admin(from_id, chat_id):
            self.bot.messages.removeChatUser(
                chat_id=chat_id,
                user_id=user_id
            )

            self.bot.messages.send(
                chat_id=chat_id,
                message="Пользователь {} забанен".format(
                    user.get_username(user_id=user_id)
                ),
                random_id=get_random_id()
            )


class Bot(object):
    def __init__(self, bot, longpoll):
        self.bot = bot
        self.longpoll = longpoll

    def _get_help(self, chat_id: int):
        message = "Список команд\n" \
                  "!инфо беседа\n" \
                  "!инфо @(Имя пользователя) или id(id пользователя)\n" \
                  "!инфо @(название группы) или @public(id группы)\n\n" \
                  "Доступно только администраторам\n" \
                  "!бан @(Имя пользователя)"

        self.bot.messages.send(
            chat_id=chat_id,
            message=message,
            random_id=get_random_id()
        )

    def check_message(self, received_message, chat_id):
        if re.match("!инфо", received_message):
            if received_message == "!инфо беседа":
                data = chat.get_chat_info(chat_id=chat_id)
                self.bot.messages.send(
                    chat_id=chat_id,
                    message=data["message"],
                    attachment=data["attachment"],
                    random_id=get_random_id()
                )
            elif re.match("!инфо id", received_message):
                user_id = int(received_message.split("id")[1].split("|")[0])
                data = user.get_user_info(user_id)
                self.bot.messages.send(
                    chat_id=chat_id,
                    message=data["message"],
                    attachment=data["attachment"],
                    random_id=get_random_id()
                )
            elif re.match("!инфо club", received_message):
                group_id = int(received_message.split("club")[1].split("|")[0])
                data = group.get_group_info(group_id)
                self.bot.messages.send(
                    chat_id=chat_id,
                    message=data["message"],
                    attachment=data["attachment"],
                    random_id=get_random_id()
                )
            else:
                self.bot.messages.send(
                    chat_id=chat_id,
                    message="Такой команды не существует",
                    random_id=get_random_id()
                )

        elif re.match("!бан id", received_message):
            user_id = int(received_message.split("id")[1].split("|")[0])
            chat.ban_user(
                from_id=self.from_id,
                user_id=user_id,
                chat_id=chat_id
            )
        elif received_message == "!помощь":
            self._get_help(chat_id)

    def listen(self):
        print("Начинаю мониторинг сообщений...")

        while True:
            try:
                """Отслеживаем каждое событие в беседе."""
                for event in self.longpoll.listen():
                    if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat and event.message.get("text") != "":
                        received_message = event.message.get("text").lower().replace("[", "").replace("]", "")
                        chat_id = event.chat_id
                        self.from_id = event.message.get("from_id")
                        self.check_message(received_message, chat_id)
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                print(e)

                
if __name__ == "__main__":
    # Авторизируем бота
    authorize = vk_api.VkApi(token=config["group"]["group_token"])
    longpoll = VkBotLongPoll(
        authorize,
        group_id=config["group"]["group_id"]
    )
    upload = vk_api.VkUpload(authorize)
    bot = authorize.get_api()

    # Авторизируем пользователя
    vk_session = vk_api.VkApi(
        token=config["user"]["user_token"]
    )
    vk = vk_session.get_api()

    vkbot = Bot(
        longpoll=longpoll,
        bot=bot
    )

    utils = Utils(
        upload=upload
    )

    user = User(
        vk=vk,
        upload=upload
    )

    group = Group(
        vk=vk,
        upload=upload
    )

    chat = Chat(
        vk=vk,
        upload=upload,
        bot=bot
    )

    vkbot.listen()  # Запускаем мониторинг бесед
