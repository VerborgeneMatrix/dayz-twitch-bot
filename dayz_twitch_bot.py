import os
import openai
import twitchio
from twitchio.ext import commands
import sqlite3
import json
import websockets
import asyncio

# Twitch & OpenAI API-Keys (Hier deine Keys einfügen!)
TWITCH_TOKEN = "your_twitch_oauth_token"
TWITCH_CHANNEL = "your_channel_name"
OPENAI_API_KEY = "your_openai_api_key"
OBS_WEBSOCKET_URL = "ws://localhost:4444"

# OpenAI API initialisieren
openai.api_key = OPENAI_API_KEY

# SQLite-Datenbank einrichten
conn = sqlite3.connect("dayz_bot.db")
cursor = conn.cursor()

# Tabellen für Missionen & Inventar erstellen
cursor.execute("""
    CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        status TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        quantity INTEGER
    )
""")

conn.commit()

class DayZChatbot(commands.Bot):
    def __init__(self):
        super().__init__(token=TWITCH_TOKEN, prefix="!", initial_channels=[TWITCH_CHANNEL])
        self.conversation_history = []  # Gesprächsverlauf für KI

    async def event_ready(self):
        print(f"Bot ist online als {self.nick}")

    async def event_message(self, message):
        if message.echo:
            return

        print(f"{message.author.name}: {message.content}")
        await self.handle_commands(message)

    @commands.command(name="help")
    async def help_command(self, ctx):
        await ctx.send("Verfügbare Befehle: !frage <Text>, !mission, !addmission <Text>, !inventar, !additem <Item> <Anzahl>, !vote <Option1> <Option2>, !status, !loot")

    @commands.command(name="frage")
    async def ai_chat(self, ctx, *, query: str):
        self.conversation_history.append({"role": "user", "content": query})
        
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)  # Begrenze Gesprächsverlauf
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=self.conversation_history
            )
            answer = response["choices"][0]["message"]["content"]
            self.conversation_history.append({"role": "assistant", "content": answer})
            await ctx.send(answer)
        except Exception as e:
            await ctx.send(f"Fehler: {e}")

    @commands.command(name="mission")
    async def mission_command(self, ctx):
        missions = cursor.execute("SELECT id, description, status FROM missions").fetchall()
        if not missions:
            await ctx.send("Es gibt derzeit keine aktiven Missionen.")
        else:
            msg = "🧭 **Aktuelle Missionen:**\n"
            for m in missions:
                msg += f"{m[0]}. {m[1]} - Status: {m[2]}\n"
            await ctx.send(msg)

    @commands.command(name="addmission")
    async def add_mission(self, ctx, *, mission_text: str):
        cursor.execute("INSERT INTO missions (description, status) VALUES (?, 'offen')", (mission_text,))
        conn.commit()
        await ctx.send(f"✅ Mission hinzugefügt: {mission_text}")

    @commands.command(name="inventar")
    async def inventory_command(self, ctx):
        inventory = cursor.execute("SELECT item, quantity FROM inventory").fetchall()
        if not inventory:
            await ctx.send("🎒 Dein Inventar ist leer.")
        else:
            msg = "🛠 **Inventar:**\n"
            for item in inventory:
                msg += f"{item[0]}: {item[1]}\n"
            await ctx.send(msg)

    @commands.command(name="additem")
    async def add_item(self, ctx, item: str, quantity: int):
        cursor.execute("INSERT INTO inventory (item, quantity) VALUES (?, ?)", (item, quantity))
        conn.commit()
        await ctx.send(f"✅ {quantity}x {item} wurde dem Inventar hinzugefügt!")

    @commands.command(name="vote")
    async def vote_command(self, ctx, option1: str, option2: str):
        await ctx.send(f"🗳 Abstimmung gestartet: 1️⃣ {option1} | 2️⃣ {option2}")
        await asyncio.sleep(30)  # 30 Sekunden warten
        await ctx.send("🗳 Die Abstimmung ist beendet!")

    async def send_obs_command(self, command):
        async with websockets.connect(OBS_WEBSOCKET_URL) as websocket:
            await websocket.send(json.dumps(command))

    @commands.command(name="alarm")
    async def alarm_command(self, ctx):
        await ctx.send("🚨 **Alarm ausgelöst!** Zombies gesichtet! ⚠️")
        await self.send_obs_command({"request-type": "TriggerHotkeyByName", "hotkeyName": "ZombieAlert"})

    @commands.command(name="status")
    async def status_command(self, ctx):
        await ctx.send("💀 Dein Charakter ist gesund. Kein Blutverlust festgestellt.")

    @commands.command(name="loot")
    async def loot_command(self, ctx):
        loots = ["Medikit", "Munitionskiste", "Überlebensmesser", "Verbandszeug", "Energieriegel"]
        loot_item = random.choice(loots)
        await ctx.send(f"🎒 Du hast '{loot_item}' gefunden!")

bot = DayZChatbot()
bot.run()
