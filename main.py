import discord
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

class selection(discord.ui.View):
    @discord.ui.select(
        placeholder="Wybierz opcję...",
        min_values=1,  # minimalna liczba wybranych opcji
        max_values=2,  # maksymalna liczba wybranych opcji
        options=[
            discord.SelectOption(label="Opcja 1", description="To jest pierwsza opcja", emoji="🍎"),
            discord.SelectOption(label="Opcja 2", description="To jest druga opcja", emoji="🍌"),
            discord.SelectOption(label="Opcja 3", description="To jest trzecia opcja", emoji="🍇"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected = ", ".join(select.values)
        await interaction.response.send_message(f'Wybrałeś: {selected}', ephemeral=True)

class catbutton(discord.ui.View):
    @discord.ui.button(
        style=discord.ButtonStyle.primary,
        label="cats!!",
        emoji="🍎"
    )
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("one cat... two cats... three cats...", ephemeral=True)

class otherCatButton(discord.ui.View):
    @discord.ui.button(
        style=discord.ButtonStyle.danger,
        label="cats!!!!!!!!!!!!!!!!!!!1 ",
    )
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("other cat moments!!!!!!!!!!!!!!!", ephemeral=True)

class profileButton(discord.ui.View):
    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        label="click this",
    )
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Embedded fookin button response boi wthat the fok haha",
            description="lol wuuut",
            color=discord.Color.random()
        )
        embed.add_field(
            name="ONE",
            value=f"{interaction.user.display_name}'s search history",
            inline=True
        )
        embed.add_field(
            name="TWO",
            value=f"{interaction.user.display_name}'s DELETED search history",
            inline=True
        )

        embed.add_field(
            name="THREE",
            value=f"{interaction.user.display_name}'s something...",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

@bot.command()
async def wybierz(ctx):
    view = selection()
    await ctx.send(view=view)

@bot.command()
async def catthing(ctx):
    view = catbutton()
    await ctx.send(view=view)

@bot.command()
async def cats(ctx):
    view = otherCatButton()
    await ctx.send(view=view)

# --- GLOBAL SLASH COMMAND CAUSE IM THE FUCKING BEST YO (global) ---
@bot.tree.command(name="ping", description="(global) ping")
async def global_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong `GLOBAL`! 🏓 {round(bot.latency * 1000)}ms", ephemeral=True)

# --- GUILD SLASH COMMAND CAUSE IM THE FUCKING WORST YO (guild) ---
@bot.tree.command(name="ping", description="(guild) ping", guild=guild)
async def guild_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong `GUILD`! 🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="embed", description="(guild) embedded message", guild=guild)
async def embedded_msg(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Profile",
        description=(
            "Gold: 0\n"
            "Silver: 0\n"
            "Platinum: 0\n"
            "Cats: 0\n"
            "Dogs: 1"
        ),
        color=discord.Color.random()
    )
    embed.set_footer(text="made with HATE by lolsye")
    embed.set_thumbnail(url=interaction.user.avatar)

    view = profileButton()

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="testdb", description="send a query to the database", guild=guild)
async def testdb(interaction: discord.Interaction):
    user_id = interaction.user.id

    #get the user from db
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone();

    #check if user exists in db
    if result is None:
        #add to db
        cursor.execute("INSERT INTO users (user_id, money) VALUES (%s, %s)", (user_id, 100))
        db.commit()
        await interaction.response.send_message(f"You have been added to the database {interaction.user.display_name}!")
    else:
        await interaction.response.send_message(f"what the fuck you doing bro smh!")

#RUN THAT BITCH LOL
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
