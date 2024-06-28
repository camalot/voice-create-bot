import datetime
import json
import random
import re
import string
import typing

import discord
import requests


def dict_get(dictionary, key, default_value=None) -> typing.Any:
    if key in dictionary.keys():
        return dictionary[key] or default_value
    else:
        return default_value


def get_scalar_result(conn, sql, default_value=None, *args) -> typing.Any:
    cursor = conn.cursor()
    try:
        cursor.execute(sql, args)
        return cursor.fetchone()[0]
    except Exception as ex:
        return default_value


def str2bool(v) -> bool:
    return v.lower() in ("yes", "true", "yup", "1", "t", "y", "on")


def chunk_list(lst, size):
    # looping till length l
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def get_random_string(length: int = 10) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def get_random_name(noun_count=1, adjective_count=1) -> str:
    fallback_nouns = [
        "Aardvark",
        "Albatross",
        "Alligator",
        "Alpaca",
    ]
    fallback_adjectives = [
        "Able",
        "Acidic",
        "Adorable",
        "Aggressive",
    ]
    try:
        adjectives = load_from_gist("adjectives", adjective_count)
        nouns = load_from_gist("nouns", noun_count)
        results = adjectives + nouns
        return " ".join(w.title() for w in results)
    except Exception as ex:
        try:
            nouns = requests.get(f"https://random-word-form.herokuapp.com/random/noun?count={str(noun_count)}").json()
            adjectives = requests.get(
                f"https://random-word-form.herokuapp.com/random/adjective?count={str(adjective_count)}"
            ).json()
            results = adjectives + nouns
            return " ".join(w.title() for w in results)
        except Exception as ex:
            try:
                results = requests.get(
                    f"https://random-word-api.herokuapp.com/word?number={str(noun_count + adjective_count)}&swear=0"
                ).json()
                return " ".join(w.title() for w in results)
            except Exception as ex:
                return " ".join(
                    random.sample(fallback_adjectives, adjective_count) + random.sample(fallback_nouns, noun_count)
                )


def get_user_display_name(user: typing.Union[discord.User, discord.Member]) -> str:
    """
    Gets the display name for the user.
    If the user has a discriminator of 0, then it will return the display name (new format).
    Otherwise it will return the display name and discriminator (old format)."""
    if user.discriminator == "0":
        return user.display_name
    else:
        return f"{user.display_name}#{user.discriminator}"


def to_timestamp(date, tz: typing.Optional[datetime.timezone] = None) -> float:
    date = date.replace(tzinfo=tz)
    return (date - datetime.datetime(1970, 1, 1, tzinfo=tz)).total_seconds()


def from_timestamp(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


def get_timestamp() -> float:
    return to_timestamp(datetime.datetime.utcnow())


def load_from_gist(type, count) -> typing.List[str]:
    types = [ "adjectives", "nouns", "verbs" ]
    if type not in types:
        type = "nouns"
    if count <= 0:
        count = 1
    elif count > 10:
        count = 10
    data = requests.get(f"https://gist.githubusercontent.com/camalot/8d2af3796ac86083e873995eab98190d/raw/b39de3a6ba03205380caf5d58e0cae8a869ac36d/{type}.js").text
    data = re.sub(r"(var\s(adjectives|nouns|verbs)\s=\s)|;$","", data)
    jdata = json.loads(data)
    return random.sample(jdata, count)


def get_args_dict(func, args, kwargs) -> dict:
    args_names = func.__code__.co_varnames[:func.__code__.co_argcount]
    return {**dict(zip(args_names, args)), **kwargs}


def str_replace(input_string: str, *args, **kwargs) -> str:
    xargs = get_args_dict(str_replace, args, kwargs)
    result = input_string
    for a in xargs:
        result = result.replace(f"{{{{{a}}}}}", str(kwargs[a]))
    return result


def get_by_name_or_id(iterable, nameOrId: typing.Optional[typing.Union[int, str]]):
    if isinstance(nameOrId, str):
        val = discord.utils.get(iterable, name=str(nameOrId))
        if val is None:
            val = discord.utils.get(iterable, id=int(nameOrId))
        return val
    elif isinstance(nameOrId, int):
        val = discord.utils.get(iterable, id=int(nameOrId))
        return val
    else:
        print("get_by_name_or_id: nameOrId is not a string or int")
        return None

def get_last_section_in_url(name) -> str:
    if "/" in name:
        # if the name has a slash in it, then it is a url. Remove everything before and including the slash
        name_split = name.rsplit("/", 1)
        if len(name_split) > 1:
            name = name_split[1]
    return name

def format_text_channel_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-_]", "", name.replace(" ", "-").replace("_", "-").lower())

def format_voice_channel_name(name: str) -> str:
    # replace dashes with spaces, remove all non-alphanumeric characters, and convert each word to Title Case
    return re.sub(r"[^a-zA-Z0-9-_]", "", name.replace("-", " ").replace("_", " ").title())
