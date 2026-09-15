import os
import asyncio
import discord
from discord import app_commands, Intents
from discord.ext import commands
import sqlite3

from db import init_db
from commands.ticket import setup as ticket_setup
from views.ticket_panel import TicketPanelView

intents = Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    init_db()
    ticket_setup(bot)
    bot.add_view(TicketPanelView())
    try:
        if guild_id := os.getenv("DISCORD_GUILD_ID"):
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild)
            bot.tree.sync(guild)
            print(f"Synced commands to guild {guild_id}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s) globally")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
