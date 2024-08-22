import inspect
import os
import socket
import time
import traceback

from prometheus_client import Gauge
from bot.cogs.lib.mongodb.exporter import ExporterMongoDatabase
from bot.cogs.lib.logger import Log
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib import settings


class VoiceCreateMetrics:
    def __init__(self, config):
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

        self.namespace = "voicecreate"
        self.polling_interval_seconds = config.metrics["pollingInterval"]
        self.config = config

        self.settings = settings.Settings()
        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG
        self.log = Log(minimumLogLevel=log_level)

        self.exporter_db = ExporterMongoDatabase()

        self.errors = Gauge(
            namespace=self.namespace,
            name=f"exporter_errors",
            documentation="The number of errors encountered",
            labelnames=["source"],
        )

        self.guilds = Gauge(
            namespace=self.namespace,
            name=f"guild",
            documentation="The guilds that the bot is in",
            labelnames=["guild_id", "name"],
        )

        self.user_settings = Gauge(
            namespace=self.namespace,
            name=f"user_settings",
            documentation="The number of user settings",
            labelnames=["guild_id"],
        )

        self.user_duration = Gauge(
            namespace=self.namespace,
            name=f"user_duration",
            documentation="The duration of a user in a channel",
            labelnames=["guild_id", "user_id", "username"],
        )

        self.channel_history = Gauge(
            namespace=self.namespace,
            name=f"channel_history",
            documentation="The number of channel history entries",
            labelnames=["guild_id", "user_id", "username"],
        )

        self.active_channels = Gauge(
            namespace=self.namespace,
            name=f"active_channels",
            documentation="The number of active channels",
            labelnames=["guild_id"],
        )

        self.healthy = Gauge(
            namespace=self.namespace, name=f"healthy", documentation="The health of the bot", labelnames=[]
        )

        self.sum_logs = Gauge(
            namespace=self.namespace, name=f"logs", documentation="The number of logs", labelnames=["guild_id", "level"]
        )

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Metrics initialized")

    def check_health(self):
        """Check the health of the bot"""
        _method = inspect.stack()[1][3]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.settimeout(10)
                    s.connect(("127.0.0.1", 40404))
                    data = s.recv(1024)
                except (ConnectionError, socket.timeout, ConnectionRefusedError) as ex:
                    data = b""

            self.healthy.set(1 if data == b"healthy" else 0)
            self.errors.labels(source="healthy").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.healthy.set(0)
            self.errors.labels(source="healthy").set(1)

    def run_metrics_loop(self):
        """Metrics fetching loop"""
        _method = inspect.stack()[0][3]
        while True:
            try:
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Begin metrics fetch")
                self.fetch()
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"End metrics fetch")
                self.log.debug(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sleeping for {self.polling_interval_seconds} seconds",
                )
                time.sleep(self.polling_interval_seconds)
            except Exception as ex:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    def fetch(self):
        _method = inspect.stack()[0][3]

        self.check_health()

        # 0 is the "global" guild for anything that isn't guild aware
        known_guilds = ["0"]
        try:
            q_guilds = self.exporter_db.get_guilds() or []
            for row in q_guilds:
                known_guilds.append(row['guild_id'])
                self.guilds.labels(guild_id=row['guild_id'], name=row['name']).set(1)
            self.errors.labels(source="guilds").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="guilds").set(1)

        try:
            q_user_settings = self.exporter_db.get_user_settings_count() or []
            for row in q_user_settings:
                self.user_settings.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="user_settings").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="user_settings").set(1)

        try:
            q_channel_history = self.exporter_db.get_tracked_channel_history() or []

            for row in q_channel_history:
                user = {"user_id": row["_id"]['owner_id'], "username": row["_id"]['owner_id']}
                if row["user"] is not None and len(row["user"]) > 0:
                    user = row["user"][0]
                else:
                    user = {
                        "name": "Unknown",
                    }
                labels = {
                    "guild_id": row['_id']["guild_id"],
                    "user_id": user["user_id"],
                    "username": user["name"],
                }
                self.channel_history.labels(**labels).set(row['total'])
            self.errors.labels(source="channel_history").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="channel_history").set(1)

        try:
            logs = self.exporter_db.get_logs() or []
            for gid in known_guilds:
                levels = LogLevel.names_to_list()
                for level in levels:
                    t_labels = {"guild_id": gid, "level": level}
                    self.sum_logs.labels(**t_labels).set(0)
            for row in logs:
                self.sum_logs.labels(guild_id=row['_id']['guild_id'], level=row['_id']['level']).set(row["total"])
            self.errors.labels("logs").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex))
            self.errors.labels("logs").set(1)

        try:
            for gid in known_guilds:
                self.active_channels.labels(guild_id=gid).set(0)

            q_active_channels = self.exporter_db.get_current_channel_count() or []
            for row in q_active_channels:
                self.active_channels.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="active_channels").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="active_channels").set(1)

        try:
            q_user_duration = self.exporter_db.get_user_channel_time() or []

            for row in q_user_duration:
                user = {"user_id": row["_id"]['user_id'], "username": row["_id"]['user_id']}
                if row["user"] is not None and len(row["user"]) > 0:
                    user = row["user"][0]
                else:
                    user = {
                        "name": "Unknown",
                    }
                labels = {
                    "guild_id": row['_id']["guild_id"],
                    "user_id": user["user_id"],
                    "username": user["name"],
                }
                self.user_duration.labels(**labels).set(row['total'])
            self.errors.labels(source="user_duration").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="user_duration").set(1)

        # try:
        #     q_user_history = self.exporter_db.get_user_channel_history() or []

        #     for row in q_user_history:
        #         user = {"user_id": row["_id"]['user_id'], "username": row["_id"]['user_id']}
        #         if row["user"] is not None and len(row["user"]) > 0:
        #             user = row["user"][0]
        #         else:
        #             user = {
        #                 "name": "Unknown",
        #             }
        #         labels = {
        #             "guild_id": row['_id']["guild_id"],
        #             "user_id": user["user_id"],
        #             "username": user["name"],
        #         }
        #         self.user_history.labels(**labels).set(row['total'])
        #     self.errors.labels(source="user_history").set(0)
        # except Exception as ex:
        #     self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
        #     self.errors.labels(source="user_history").set(1)
