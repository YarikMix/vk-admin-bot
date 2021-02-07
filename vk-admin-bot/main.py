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


class Bot():
    def write_message(self, message="", attachment=""):
        """Отправляем в беседу сообщение."""
        self.authorize.method("messages.send", {
            "chat_id": self.chat_id,
            "message": message,
            "attachment": attachment,
            "random_id": get_random_id()
        })

    def auth_handler(self, remember_device=None):
        code = input("Введите код подтверждения\n> ")
        if remember_device is None:
            remember_device = True
        return code, remember_device

    def auth(self):
        # Авторизация бота
        self.authorize = vk_api.VkApi(token=config["group"]["group_key"])
        self.longpoll = VkBotLongPoll(
            self.authorize,
            group_id=config["group"]["group_id"]
        )
        self.upload = vk_api.VkUpload(self.authorize)

        vk_session = vk_api.VkApi(
            token=config["access_token"]["token"],
            auth_handler=self.auth_handler
        )
        try:
            vk_session.auth(token_only=True)
        except Exception as e:
            print("Не получилось авторизоваться, попробуйте снова.")
            print(e)
        finally:
            print('Вы успешно авторизовались.')
            self.vk = vk_session.get_api()

    # Утилиты
    def get_photo_by_url(self, url):
        r = requests.get(url)
        image = io.BytesIO(r.content)

        # Отправляем фото в беседу
        response = self.upload.photo_messages(photos=image)[0]
        attachment = "photo{}_{}".format(response["owner_id"], response["id"])
        return attachment

    # Функции для работы с группами
    def get_group_owner(self, group_id):
        try:
            test = self.vk.groups.getMembers(group_id=group_id, filter="managers")
            owner_id = test["items"][0]["id"]
            return f"Создатель - {self.get_username(owner_id)}"

        except vk_api.exceptions.ApiError:
            return ""

    def get_group_info(self, group_id):
        group_info = self.vk.groups.getById(group_id=group_id)[0]

        max_size = list(group_info)[-1]
        photo_url = group_info[max_size]

        res = "{} {} {} {}".format(
            f"{group_info['name']}\n",
            f"id - {group_info['id']}\n",
            self.get_group_owner(group_id),
            "Аватарка",
        )
        self.write_message(message=res, attachment=self.get_photo_by_url(photo_url))

    # Функции для работы с беседой
    def get_chat_info(self):
        chat_info = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + self.chat_id,
            group_id=config["group"]["group_id"]
        )["items"][0]["chat_settings"]

        chat_name = chat_info["title"]
        members_count = chat_info["members_count"]
        owner_id = chat_info["owner_id"]

        # Получаем url фото
        sizes = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + self.chat_id,
            group_id=config["group"]["group_id"]
        )["items"][0]["chat_settings"]["photo"]
        max_size = list(sizes)[-2]
        photo_url = sizes[max_size]

        res = "{} {} {} {}".format(
            f"Название - {chat_name}\n",
            "{}\n".format(numeral.get_plural(members_count, "участник, участника, участников")),
            f"Создатель - {self.get_username(owner_id)}\n",
            "Аватарка"
        )
        self.write_message(message=res, attachment=self.get_photo_by_url(photo_url))

    # Функции для работы с пользователями
    def get_username(self, user_id):
        user_info = self.vk.users.get(user_ids=user_id)[0]
        username = "{} {}\n".format(
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

    def get_user_status(self, user_id):
        user_info = self.vk.users.get(
            user_ids=user_id,
            fields="status"
        )[0]
        if user_info["status"] != "":
            status = f"Статус: {user_info['status']}\n"
        else:
            status = ""
        return status

    def get_user_photos(self, user_id):
        count = self.vk.users.get(
            user_id=user_id,
            fields="counters"
        )[0]["counters"]["photos"]
        return f"{count} фото\n"

    def get_user_audios(self, user_id):
        count = self.vk.users.get(
            user_id=user_id,
            fields="counters"
        )[0]["counters"]["audios"]
        return "{}\n".format(
            numeral.get_plural(count, "аудиозапись, аудиозаписи, аудиозаписей")
        )

    def get_user_videos(self, user_id):
        count = self.vk.users.get(
            user_id=user_id,
            fields="counters"
        )[0]["counters"]["videos"]
        return f"{count} видео\n"

    def get_user_friends(self, user_id):
        count = self.vk.users.get(
            user_id=user_id,
            fields="counters"
        )[0]["counters"]["friends"]
        return "{}\n".format(
            numeral.get_plural(count, "друг, друга, друзей")
        )

    def get_user_followers(self, user_id):
        count = self.vk.users.get(
            user_id=user_id,
            fields="counters"
        )[0]["counters"]["followers"]
        return "{}\n".format(
            numeral.get_plural(count, "подписчик, подписчика, подписчиков")
        )

    def get_user_groups(self, user_id):
        count = self.vk.users.get(
            user_id=user_id,
            fields="counters"
        )[0]["counters"]["groups"]
        return "{}\n".format(
            numeral.get_plural(count, "группа, группы, групп")
        )

    def get_user_profile_photo(self, user_id):
        photo_id = self.vk.photos.get(
            owner_id=user_id,
            album_id="profile"
        )["items"][-1]["id"]
        attachment = "photo{}_{}".format(user_id, photo_id)
        return attachment

    def get_user_info(self, user_id):
        is_closed = self.vk.users.get(
            user_ids=user_id
        )[0]["is_closed"]

        if is_closed:
            # Профиль пользователя закрыт
            res = "{} {} {} {} {} {}".format(
                self.get_username(user_id),
                f"id - {user_id}\n",
                self.get_user_last_activity(user_id),
                self.get_user_status(user_id),
                "Профиль закрыт ❌\n",
                "Аватарка"
            )
        else:
            # Профиль пользователя открыт
            res = "{} {} {} {} {} {} {} {} {} {} {} {}".format(
                self.get_username(user_id),
                f"id - {user_id}\n",
                self.get_user_last_activity(user_id),
                self.get_user_status(user_id),
                "Профиль открыт ✅\n",
                self.get_user_photos(user_id),
                self.get_user_audios(user_id),
                self.get_user_videos(user_id),
                self.get_user_friends(user_id),
                self.get_user_followers(user_id),
                self.get_user_groups(user_id),
                "Аватарка"
            )

        self.write_message(
            message = res,
            attachment = self.get_user_profile_photo(user_id)
        )

    def ban_user(self, user_id):
        data = self.authorize.get_api().messages.getConversationMembers(
            peer_id=2000000000 + 1,
            group_id=1,
        )["items"]

        is_admin = {}

        for user in data:
            if "is_admin" in user:
                is_admin[user["member_id"]] = True
            else:
                is_admin[user["member_id"]] = False

        if is_admin[self.from_id]:
            self.authorize.get_api().messages.removeChatUser(
                chat_id=self.chat_id,
                user_id=user_id
            )
            self.write_message("Забанен")
        else:
            self.write_message("Вам не доступна эта команда")

    def get_help(self):
        res = "{}{}{}{}".format(
            "Список команд\n",
            "!инфо беседа\n",
            "!инфо @(Имя пользователя)\n\n",
            "Доступно только администраторам\n"
            "!бан @(Имя пользователя)"
        )
        self.write_message(res)

    def check_message(self, received_message):
        if re.match("!инфо", received_message):
            if received_message == "!инфо беседа":
                self.get_chat_info()
            elif re.match("!инфо id\d*", received_message):
                user_id = int(received_message[8:17])
                self.get_user_info(user_id)
            elif re.match("!инфо club\d*", received_message):
                club_id = int(received_message[10:19])
                self.get_group_info(club_id)
            else:
                self.write_message(message="Такой команды не существует.")
        elif re.match("!бан id\d*", received_message):
            user_id = int(received_message[7:16])
            self.ban_user(user_id)
        elif received_message == "!help":
            self.get_help()

    def watch(self):
        """Отслеживаем каждое событие в беседе."""
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat and event.message.get("text") != "":
                received_message = event.message.get("text").lower().replace("[", "").replace("]", "")
                self.chat_id = event.chat_id
                self.from_id = event.message.get("from_id")
                self.check_message(received_message)

    def start_watch(self):
        self.auth()

        self.watch()


if __name__ == "__main__":
    VkBot = Bot()
    VkBot.start_watch()
    