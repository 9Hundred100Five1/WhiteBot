import discord
from discord.ext import commands
from discord.commands import ApplicationContext, Option
from utils.commands import slash_command
from discord.ui import View, Button
import sqlite3
import os
import re
import logging

logger = logging.getLogger(__name__)

class vote(commands.Cog):
    def __init__(self):
        db_path = os.getenv("DATABASE_PATH") or ":memory:"
        self.service = vote_service(db_path)
        self.service.create_tables()

    @slash_command(description="투표를 시작합니다")
    async def vote(
        self,
        ctx: ApplicationContext,
        name: Option(str, description="투표 이름"),
        choices: Option(str, description="선택지(쉼표로 구분, 최대 25개)")
    ):
        await ctx.defer()

        vote_id = self.service.create_vote(name, ctx.author.id, ctx.interaction.token)
        logger.info(f"vote entity created(id: {vote_id}, name: {name})")

        choices = choices.split(",", 25)
        view = View()
        for choice in choices:
            choice_name = choice.strip()
            choice_id = self.service.create_vote_choice(choice_name, vote_id)
            logger.info(f"vote choice entity created(id: {choice_id}, name: {choice_name}, vote: {vote_id})")

            button = Button(style = discord.ButtonStyle.primary, label = choice_name, custom_id = str(choice_id))
            button.callback = self.button_callback
            view.add_item(button)

        await ctx.respond(
            embed=discord.Embed(title=name, description="아래 버튼을 눌러 투표에 참여해주세요.", color=0xFFFFFF)
                .set_footer(text=f"Started by {ctx.author.display_name}", icon_url=ctx.author.display_avatar),
            view=view
        )

    async def button_callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        choice_id = interaction.data["custom_id"]

        self.service.create_voter(user_id, choice_id)
        logger.info(f"voter entity created(id: {user_id}, choice: {choice_id})")


class vote_service():
    CREATE_TABLES = [
        "CREATE TABLE IF NOT EXISTS votes(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, state INTEGER, user_id INTEGER, interaction_token TEXT)",
        "CREATE TABLE IF NOT EXISTS vote_choices(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, value INTEGER, vote REFERENCES votes)",
        "CREATE TABLE IF NOT EXISTS voters(id INTEGER PRIMARY KEY, choice REFERENCES voice_choices)"
    ]
    CREATE_VOTE = "INSERT INTO votes (name, state, user_id, interaction_token) VALUES (?, 0, ?, ?)"
    CREATE_VOTE_CHOICE = "INSERT INTO vote_choices (name, value, vote) VALUES (?, 0, ?)"
    CREATE_VOTER = "INSERT INTO voters (id, choice) VALUES (?, ?)"

    GET_VOTER = "SELECT * FROM voters WHERE id=? AND choice=?"

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def create_tables(self):
        with self.conn.cursor() as cursor:
            for smt in self.CREATE_TABLES:
                cursor.execute(smt)

    def create_vote(self, name, user_id, interaction_token) -> int:
        with self.conn.execute(self.CREATE_VOTE, (name, user_id, interaction_token)) as cursor:
            return cursor.lastrowid

    def create_vote_choice(self, name, vote) -> int:
        with self.conn.execute(self.CREATE_VOTE_CHOICE, (name, vote)) as cursor:
            return cursor.lastrowid

    def create_voter(self, id, choice) -> int:
        with self.conn.execute(self.CREATE_VOTER, (id, choice)) as cursor:
            return cursor.lastrowid


def setup(bot: discord.Bot):
    bot.add_cog(vote())
