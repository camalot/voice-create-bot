import sys
import typing

from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.logs import LogsDatabase
from bot.cogs.lib.colors import Colors


class Log:
    def __init__(self, minimumLogLevel: LogLevel = LogLevel.DEBUG):
        self.logs_db = LogsDatabase()
        self.minimum_log_level = minimumLogLevel

    def __write(
        self,
        guildId: int,
        level: LogLevel,
        method: str,
        message: str,
        stackTrace: typing.Optional[str] = None,
        file: typing.IO = sys.stdout,
    ):
        color = Colors.get_color(level)
        m_level = Colors.colorize(color, f"[{level.name}]", bold=True)
        m_method = Colors.colorize(Colors.HEADER, f"[{method}]", bold=False)
        m_message = f"{Colors.colorize(color, message)}"
        m_guild = Colors.colorize(Colors.OKGREEN, f"[{guildId}]", bold=False)
        str_out = f"{m_level} {m_method} {m_guild} {m_message}"
        print(str_out, file=file)
        if stackTrace:
            print(Colors.colorize(color, stackTrace), file=file)

        if level >= self.minimum_log_level:
            self.logs_db.insert_log(guildId=guildId, level=level, method=method, message=message, stackTrace=stackTrace)

    def debug(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=LogLevel.DEBUG,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stdout,
        )

    def info(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=LogLevel.INFO,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stdout,
        )

    def warn(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=LogLevel.WARNING,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stdout,
        )

    def error(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=LogLevel.ERROR,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stderr,
        )

    def fatal(self, guildId: int, method: str, message: str, stackTrace: typing.Optional[str] = None):
        self.__write(
            guildId=guildId,
            level=LogLevel.FATAL,
            method=method,
            message=message,
            stackTrace=stackTrace,
            file=sys.stderr,
        )
