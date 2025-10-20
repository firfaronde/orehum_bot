from flask import Flask

api = Flask(__name__)

async def load(bot, api_port: int = 80):
    api.run(port=api_port)
    print("Sponsor api loaded!")