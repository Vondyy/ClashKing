from disnake.ext import commands
from BoardCommands import Boards
from BoardCommands import Graphs

class BoardCog(Boards.BoardCreator, Graphs.GraphCreator, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(BoardCog(bot))