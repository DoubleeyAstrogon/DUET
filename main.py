import discord
import random
from discord import app_commands
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import mysql.connector

#load the envoirement variables
load_dotenv()

#get db parameters from env
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")

#database connect
db = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_pass,
    database=db_name
)

#run db
cursor = db.cursor()

#get token from env
token = os.getenv("TOKEN")
#this is for guild slash commands, useless for you really
guild_id = int(os.getenv("DEVELOPER_GUILD"))
guild = discord.Object(id=guild_id)

#error handler to log the errors, useless for you
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

#disscord intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='?', intents=intents)

#####################
########VIEW#########
#####################

class PigGameView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=30 * 60)
        self.user_id = user_id
        self.score = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your game.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🎲 Roll", style=discord.ButtonStyle.primary)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        roll = random.randint(1, 6)

        if roll == 1:
            self.score = 0
            self.clear_items()
            self.add_item(PlayAgainButton(self.user_id))

            await interaction.response.edit_message(
                content="💀 You rolled **1**!\nYou lost everything.",
                view=self
            )
            return

        self.score += roll

        await interaction.response.edit_message(
            content=f"🎲 You rolled **{roll}**\nCurrent score: **{self.score}**",
            view=self
        )

    @discord.ui.button(label="🏁 End Game", style=discord.ButtonStyle.success)
    async def end_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        cursor.execute("""
            INSERT INTO user_stats (user_id, pig_score)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
            pig_score = GREATEST(pig_score, VALUES(pig_score))
        """, (self.user_id, self.score))

        db.commit()

        self.clear_items()

        await interaction.response.edit_message(
            content=f"✅ Game ended!\nSaved **{self.score}** points to your account.",
            view=None
        )

    async def on_timeout(self):
        self.clear_items()

class PlayAgainButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="🔁 Play Again",
            style=discord.ButtonStyle.secondary
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your game.",
                ephemeral=True
            )
            return

        view = PigGameView(self.user_id)
        await interaction.response.edit_message(
            content="🐷 Pig Game started!\nRoll the dice!",
            view=view
        )

#################################
@bot.event
async def on_ready():
    print(f"{bot.user.id} is online!")

    # Registering global slash commands
    synced_global = await bot.tree.sync()
    print(f"Registered {len(synced_global)} Global Commands")

    # Registering dev guild slash commands
    synced_guild = await bot.tree.sync(guild=guild)
    print(f"Registered {len(synced_guild)} Guild Commands")
#################################

######################
#######COMMANDS#######
######################

@bot.tree.command(name="pig", description="Play Pig dice game")
async def pig(interaction: discord.Interaction):
    user_id = interaction.user.id
    cursor.execute("SELECT pig_score FROM user_stats WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    highscore = result[0] if result else 0;
    view = PigGameView(interaction.user.id)
    await interaction.response.send_message(
        f"🐷 Pig Game started!\nRoll the dice!\nHighscore: **{highscore}**",

        view=view
    )

#RUN THAT BITCH LOL
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
