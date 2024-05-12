import glob
import inspect
import json
import os
import sys
import traceback
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.settings import SettingsDatabase


class Settings:
    APP_VERSION = "1.0.0-snapshot"

    def __init__(self):
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

        self.commands = {}
        self.strings = {}
        self.languages = {}
        self.name = None
        self.version = None
        self.init_message = None

        try:
            with open('app.manifest', encoding="UTF-8") as json_file:
                self.__dict__.update(json.load(json_file))
        except Exception as e:
            print(e, file=sys.stderr)

        self.db_url = utils.dict_get(os.environ, "VCB_MONGODB_URL", default_value="")

        self.bot_owner = utils.dict_get(os.environ, 'VCB_BOT_OWNER', default_value= '262031734260891648')
        self.log_level = utils.dict_get(os.environ, 'VCB_LOG_LEVEL', default_value = 'DEBUG')
        self.language = utils.dict_get(os.environ, "VCB_LANGUAGE", default_value = "en-us").lower()
        self.db_name = utils.dict_get(os.environ, "VCB_MONGODB_DBNAME", default_value = "voicecreate_v2")

        self.db = SettingsDatabase()

        self.load_language_manifest()
        self.load_strings()

    def to_dict(self):
        return self.__dict__

    def load_strings(self):
        _method = inspect.stack()[1][3]
        self.strings = {}

        lang_files = glob.glob(os.path.join(os.path.dirname(__file__), "../../../languages", "[a-z][a-z]-[a-z][a-z].json"))
        languages = [os.path.basename(f)[:-5] for f in lang_files if os.path.isfile(f)]
        for lang in languages:
            self.strings[lang] = {}
            try:
                lang_json = os.path.join("languages", f"{lang}.json")
                if not os.path.exists(lang_json) or not os.path.isfile(lang_json):
                    self.db.log(
                        guildId=0,
                        level=LogLevel.FATAL,
                        method=f"{self._module}.{self._class}.{_method}",
                        message=f"Language file {lang_json} does not exist",
                        stackTrace=traceback.format_exc(),
                    )
                    # THIS SHOULD NEVER GET HERE
                    continue

                with open(lang_json, encoding="UTF-8") as lang_file:
                    self.strings[lang].update(json.load(lang_file))

            except Exception as e:
                self.db.log(
                    guildId=0,
                    level=LogLevel.FATAL,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"{e}",
                    stackTrace=traceback.format_exc(),
                )
                raise e

    def load_language_manifest(self):
        lang_manifest = os.path.join(os.path.dirname(__file__), "../../../languages/manifest.json")
        self.languages = {}
        if os.path.exists(lang_manifest):
            with open(lang_manifest, encoding="UTF-8") as manifest_file:
                self.languages.update(json.load(manifest_file))

    def get_string(self, guildId: int, key: str, *args, **kwargs) -> str:
        _method = inspect.stack()[1][3]
        print(f"get_string: {guildId}, {key}, {args}, {kwargs}")
        print(f"self.strings: {self.strings}")
        print(f"self.language: {self.language}")
        if not key:
            return ''
        if str(guildId) in self.strings:
            if key in self.strings[str(guildId)]:
                return utils.str_replace(self.strings[str(guildId)][key], *args, **kwargs)
            elif key in self.strings[self.language]:
                return utils.str_replace(self.strings[self.language][key], *args, **kwargs)
            else:
                return utils.str_replace(f"{key}", *args, **kwargs)
        else:
            # get guild language
            lang = self.get_language(guildId)
            if key in self.strings[lang]:
                return utils.str_replace(self.strings[lang][key], *args, **kwargs)
            elif key in self.strings[self.language]:
                return utils.str_replace(self.strings[self.language][key], *args, **kwargs)
            else:
                return utils.str_replace(f"{key}", *args, **kwargs)

    def set_guild_strings(self, guildId: int, lang: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[1][3]
        if not lang:
            lang = self.language
        self.strings[str(guildId)] = self.strings[lang]

    def get_language(self, guildId: int) -> str:
        guild_setting = self.db.get(guildId)
        if not guild_setting:
            return self.language
        return guild_setting.language or self.language

    def get(self, name, default_value=None) -> typing.Any:
        return utils.dict_get(self.to_dict(), name, default_value)

    def get_settings(self, db, guildId: int, name:str) -> typing.Any:
        return db.get_settings(guildId, name)
