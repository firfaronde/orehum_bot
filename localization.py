import aiohttp
import socket

jobs = {} # ключ джобки к переведенной джобке
species = {} # ключ расы к переведенной расе
sexes = {} # пол к переведенному полу
lifepaths = {} # жизненный путь к переведенному пути

async def load():
    global jobs, species, sexes, lifepaths
    jobs = await load_ftl("https://raw.githubusercontent.com/BohdanNovikov0207/Orehum-Project/refs/heads/master/Resources/Locale/ru-RU/job/job-names.ftl")
    jobs["Overall"] = "Общее"
    jobs["Admin"] = "Админ"
    print("Jobs localization loaded")
    species = await load_ftl("https://raw.githubusercontent.com/BohdanNovikov0207/Orehum-Project/refs/heads/master/Resources/Locale/ru-RU/species/species.ftl")
    species["species-name-ipc"] = "КПБ"
    species["species-name-thaven"] = "Тавен"
    species["species-name-tajaran"] = "Таяр"
    species["species-name-felinid"] = "Фелинид"
    species["species-name-feroxi"] = "Ферокси"
    print("Species localization loaded")
    sexes = {}
    sexes["male"] = "Мужской"
    sexes["female"] = "Женский"
    sexes["unsexed"] = "Бесполый"
    print("Sexes localization loaded")
    lifepaths = await load_ftl("https://raw.githubusercontent.com/BohdanNovikov0207/Orehum-Project/refs/heads/master/Resources/Locale/ru-RU/_Orehum/contractors/lifepath.ftl")
    print("Lifepaths localization loaded")

async def load_ftl(url: str) -> dict[str, str]:
    constr = {}

    connector = aiohttp.TCPConnector(family=socket.AF_INET) # IPv4 only
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Error while loading jobs ftl: {resp.status}")
            text = await resp.text()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            constr[key.strip()] = val.strip().strip('"')
    return constr

def get_job_name(job_id: str) -> str:
    return jobs.get(job_id, job_id)

def get_specie_name(spec_id: str) -> str:
    return species.get("species-name-"+spec_id.lower(), spec_id)

def get_sex_name(sex: str) -> str:
    return sexes.get(sex.lower(), sex)

def get_lifepath_name(id: str) -> str:
    return lifepaths.get("lifepath_name_"+id.lower(), id)