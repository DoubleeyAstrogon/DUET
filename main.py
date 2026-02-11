import discord
import random
from discord import Permissions, app_commands
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

def ensure_user(user_id: int):
    cursor.execute("""
        INSERT IGNORE INTO users (user_id)
        VALUES (%s)
    """, (user_id,))
    db.commit()

#####################
#########VIEW########
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


# Pig Game command
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

# /balance command
@bot.tree.command(name="balance", description="Check your balance", guild=guild)
@app_commands.describe(
    user="the user you want to check the balance of"
)
async def balance(
    interaction: discord.Interaction,
    user: discord.Member = None
):
    target_user = user or interaction.user
    user_id = target_user.id
    ensure_user(user_id)

    cursor.execute(
        "SELECT balance FROM users WHERE user_id = %s",
        (user_id,)
    )
    balance = cursor.fetchone()[0]

    await interaction.response.send_message(
        f"💰 {target_user.display_name}'s balance: **{balance} coins**"
    )

# admin command for adding money, if subsract option is set to True then the amount set will be subsracted instead, fallback to false if not set (adding money)
@bot.tree.command(name="admin-economy", description="(ADMIN) money config", guild=guild)
@app_commands.describe(
    user="user",
    amount="money",
    subtract="boolean"
)
#check for perms
@app_commands.checks.has_permissions(administrator=True) 
async def money(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int,
    subtract: bool = False
):
    if amount <= 0:
        await interaction.response.send_message(
            "Amount must be greater than 0.",
            ephemeral=True
        )
        return
    
    ensure_user(user.id)

    if subtract:
        # Prevent negative balance
        cursor.execute(
            "SELECT balance FROM users WHERE user_id = %s",
            (user.id,)
        )
        current_balance = cursor.fetchone()[0]

        if current_balance < amount:
            await interaction.response.send_message(
                f"**{user.display_name}** does not have enough balance.",
                ephemeral=True
            )
            return

        cursor.execute(
            "UPDATE users SET balance = balance - %s WHERE user_id = %s",
            (amount, user.id)
        )

        action = "removed from"

    else:
        cursor.execute(
            "UPDATE users SET balance = balance + %s WHERE user_id = %s",
            (amount, user.id)
        )

        action = "added to"

    db.commit()

    await interaction.response.send_message(
        f"✅ {amount} coins {action} {user.display_name}'s balance."
    )

#if error on money which is the command def
@money.error
async def money_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

#RUN
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
