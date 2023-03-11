import coc
import disnake
from disnake.ext import commands
from datetime import datetime
clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
import asyncio
from CustomClasses.CustomBot import CustomClient
from pymongo import UpdateOne
from PIL import Image, ImageDraw, ImageFont
#import chat_exporter
from ImageGen import WarEndResult as war_gen
from ImageGen import ClanCapitalResult as capital_gen
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry

class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("ready")


    @commands.Cog.listener()
    async def on_message(self, msg):
        # if not Mcknight, do nothing
        if msg.author.id != 310517079642079234:
            return
        message = "Thanks for inviting me to your server! I'm ClashKing, your friendly Clash of Clans bot. With me around, you can easily track legends, autoboards, clans/families, and much more. To get started, simply type in the `/help` command to see a list of available commands. If you need any further assistance, don't hesitate to check out our documentation or join our support server. We're always here to help you get the most out of your COC experience! Thanks again for having me on board."
        results = await self.bot.server_db.find_one({"server": msg.guild.id})
        botAdmin = msg.guild.get_member(self.bot.user.id).guild_permissions.administrator
        if results is None:
            pass
            # await self.bot.server_db.insert_one({
            #     "server": guild.id,
            #     "banlist": None,
            #     "greeting": None,
            #     "cwlcount": None,
            #     "topboardchannel": None,
            #     "tophour": None,
            #     "lbboardChannel": None,
            #     "lbhour": None
            # })
        # if there's a result and bot has admin permissions then no msg needed.
        if results and botAdmin == True:
            return
        # looping thorugh channels to find the first text channel where we have permissions to send message.
        
        for guildChannel in msg.guild.channels:
            permissions = guildChannel.permissions_for(guildChannel.guild.me)
            if str(guildChannel.type) == 'text' and permissions.send_messages == True:
                firstChannel = guildChannel
                break
        else:
            return
        embed = disnake.Embed(description=message,color=disnake.Color.blue())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Support Server", emoji="🔗", url="https://discord.gg/clashking"))
        buttons.append_item(disnake.ui.Button(label=f"Documentation",emoji="🔗", url="https://docs.clashking.xyz"))
        await msg.channel.send(components=buttons, embed=embed) if results is None else ''
        await msg.channel.send(f"I require admin permissions for full functionality. Please update my permissions, thank you!") if not botAdmin else ''
        
        
    @commands.command(name='reload', hidden=True)
    async def _reload(self,ctx, *, module: str):
        """Reloads a module."""
        if ctx.message.author.id == 706149153431879760:
            try:
                self.bot.unload_extension(module)
                self.bot.load_extension(module)
            except:
                await ctx.send('<a:no:862552093324083221> Could not reload module.')
            else:
                await ctx.send('<a:check:861157797134729256> Reloaded module successfully')
        else:
            await ctx.send("You aren't magic. <:PS_Noob:783126177970782228>")

    @commands.slash_command(name="owner_anniversary", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def anniversary(self, ctx: disnake.ApplicationCommandInteraction):
        guild = ctx.guild
        await ctx.send(content="Edited 0 members")
        x = 0
        twelve_month = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
        nine_month = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
        six_month = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
        three_month = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
        for member in guild.members:
            if member.bot:
                continue
            year = member.joined_at.year
            month = member.joined_at.month
            n_year = datetime.now().year
            n_month = datetime.now().month
            num_months = (n_year - year) * 12 + (n_month - month)
            if num_months >= 12:
                if twelve_month not in member.roles:
                    await member.add_roles(*[twelve_month])
                if nine_month in member.roles or six_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[nine_month, six_month, three_month])
            elif num_months >= 9:
                if nine_month not in member.roles:
                    await member.add_roles(*[nine_month])
                if twelve_month in member.roles or six_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[twelve_month, six_month, three_month])
            elif num_months >= 6:
                if six_month not in member.roles:
                    await member.add_roles(*[six_month])
                if twelve_month in member.roles or nine_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[twelve_month, nine_month, three_month])
            elif num_months >= 3:
                if three_month not in member.roles:
                    await member.add_roles(*[three_month])
                if twelve_month in member.roles or nine_month in member.roles or six_month in member.roles:
                    await member.remove_roles(*[twelve_month, nine_month, six_month])
            x += 1
            if x % 5 == 0:
                await ctx.edit_original_message(content=f"Edited {x} members")
        await ctx.edit_original_message(content="Done")


    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")

    '''@commands.slash_command(name="transcript",guild_ids=[923764211845312533] )
    @commands.is_owner()
    async def create_transcript(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        message = await chat_exporter.quick_export(ctx.channel)
        await chat_exporter.quick_link(ctx.channel, message)
        await ctx.edit_original_message(content="Here is your transcript!")'''


    @commands.slash_command(name="test", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def testfwlog(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        clan_tag = "#YVUPY0R"
        clan = await self.bot.getClan(clan_tag)
        weekend = gen_raid_weekend_datestrings(number_of_weeks=2)[-1]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot)
        file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
        await ctx.edit_original_message(file=file)


def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))