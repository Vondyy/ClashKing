import disnake
import coc
import asyncio
import calendar
import operator

from datetime import date, timedelta, datetime
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from utils.clash import *
from utils.general import acronym, create_superscript
from utils.discord_utils import interaction_handler
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from numerize import numerize
from CustomClasses.PlayerHistory import StayType
from typing import List
from pytz import utc
from coc.raid import RaidMember, RaidLogEntry

async def create_profile_stats(bot: CustomClient, ctx, player: MyCustomPlayer):

    discord_id = await bot.link_client.get_link(player.tag)
    member = await bot.pingToMember(ctx, str(discord_id))
    super_troop_text = profileSuperTroops(player)

    clan = f"{player.clan.name}, " if player.clan is not None else "None"
    role = player.role if player.role is not None else ""

    if member is not None:
        link_text = f"Linked to {member.mention}"
    elif member is None and discord_id is not None:
        link_text = "*Linked, but not on this server.*"
    else:
        link_text = "Not linked. Owner? Use </link:1033741922180796451>"

    last_online = f"<t:{player.last_online}:R>, {len(player.season_last_online())} times"
    if player.last_online is None:
        last_online = "`Not Seen Yet`"

    loot_text = ""
    if player.gold_looted != 0:
        loot_text += f"- {bot.emoji.gold}Gold Looted: {'{:,}'.format(player.gold_looted)}\n"
    if player.elixir_looted != 0:
        loot_text += f"- {bot.emoji.elixir}Elixir Looted: {'{:,}'.format(player.elixir_looted)}\n"
    if player.dark_elixir_looted != 0:
        loot_text += f"- {bot.emoji.dark_elixir}DE Looted: {'{:,}'.format(player.dark_elixir_looted)}\n"

    capital_stats = player.clan_capital_stats(start_week=0, end_week=4)
    hitrate = (await player.hit_rate())[0]
    profile_text = f"{link_text}\n" \
        f"Tag: [{player.tag}]({player.share_link})\n" \
        f"Clan: {clan} {role}\n" \
        f"Last Seen: {last_online}\n" \
        f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{player.tag.strip('#')})\n\n" \
        f"**Season Stats:**\n" \
        f"__Attacks__\n" \
        f"- {league_emoji(player)}Trophies: {player.trophies}\n" \
        f"- {bot.emoji.thick_sword}Attack Wins: {player.attack_wins}\n" \
        f"- {bot.emoji.brown_shield}Defense Wins: {player.defense_wins}\n" \
        f"{loot_text}" \
        f"__War__\n" \
        f"- {bot.emoji.hitrate}Hitrate: `{round(hitrate.average_triples * 100, 1)}%`\n" \
        f"- {bot.emoji.avg_stars}Avg Stars: `{round(hitrate.average_stars, 2)}`\n" \
        f"- {bot.emoji.war_stars}Total Stars: `{hitrate.total_stars}, {hitrate.num_attacks} atks`\n" \
        f"__Donations__\n" \
        f"- <:warwon:932212939899949176>Donated: {player.donos().donated}\n" \
        f"- <:warlost:932212154164183081>Received: {player.donos().received}\n" \
        f"- <:winrate:932212939908337705>Donation Ratio: {player.donation_ratio()}\n" \
        f"__Event Stats__\n" \
        f"- {bot.emoji.capital_gold}CG Donated: {'{:,}'.format(sum([sum(cap.donated) for cap in capital_stats]))}\n" \
        f"- {bot.emoji.thick_sword}CG Raided: {'{:,}'.format(sum([sum(cap.raided) for cap in capital_stats]))}\n" \
        f"- {bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.clan_games())}\n" \
        f"{super_troop_text}" \
        f"\n**All Time Stats:**\n" \
        f"Best Trophies: {bot.emoji.trophy}{player.best_trophies} | {bot.emoji.versus_trophy}{player.best_versus_trophies}\n" \
        f"War Stars: {bot.emoji.war_star}{player.war_stars}\n" \
        f"CWL Stars: {bot.emoji.war_star} {player.get_achievement('War League Legend').value}\n" \
        f"{bot.emoji.troop}Donations: {'{:,}'.format(player.get_achievement('Friend in Need').value)}\n" \
        f"{bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.get_achievement('Games Champion').value)}\n" \
        f"{bot.emoji.thick_sword}CG Raided: {'{:,}'.format(player.get_achievement('Aggressive Capitalism').value)}\n" \
        f"{bot.emoji.capital_gold}CG Donated: {'{:,}'.format(player.get_achievement('Most Valuable Clanmate').value)}"

    embed = disnake.Embed(title=f"{player.town_hall_cls.emoji} **{player.name}**",
                          description=profile_text,
                          color=disnake.Color.green())
    embed.set_thumbnail(url=player.town_hall_cls.image_url)
    if member is not None:
        embed.set_footer(text=str(member), icon_url=member.display_avatar)

    ban = await bot.banlist.find_one({"$and": [
        {"VillageTag": f"{player.tag}"},
        {"server": ctx.guild.id}
    ]})

    if ban is not None:
        date = ban.get("DateCreated")
        date = date[:10]
        notes = ban.get("Notes")
        if notes == "":
            notes = "No Reason Given"
        embed.add_field(name="__**Banned Player**__",
                        value=f"Date: {date}\nReason: {notes}")
    return embed


async def history(bot: CustomClient, ctx, player):

    clan_history = await bot.get_player_history(player_tag=player.tag)
    previous_clans = clan_history.previous_clans(limit=5)
    clan_summary = clan_history.summary(limit=5)

    top_5 = ""
    if previous_clans == "Private History":
        return disnake.Embed(title=f"{player.name} Clan History",description="This player has made their clash of stats history private.", color=disnake.Color.green())
    embed = disnake.Embed(title=f"{player.name} Clan History", description=f"This player has been seen in a total of {clan_history.num_clans} different clans\n"
                                        f"[Full History](https://www.clashofstats.com/players/{player.tag.strip('#')}/history/)", color=disnake.Color.green())

    for clan in clan_summary:
        years = clan.duration.days // 365
        # Calculating months
        months = (clan.duration.days - years * 365) // 30
        # Calculating days
        days = (clan.duration.days - years * 365 - months * 30)
        date_text = []
        if years >= 1:
            date_text.append(f"{years} Years")
        if months >= 1:
            date_text.append(f"{months} Months")
        if days >= 1:
            date_text.append(f"{days} Days")
        if date_text:
            date_text = ', '.join(date_text)
        else:
            date_text = "N/A"
        top_5 += f"[{clan.clan_name}]({clan.share_link}) - {date_text}\n"

    if top_5 == "":
        top_5 = "No Clans Found"
    embed.add_field(name="**Top 5 Clans Player has stayed the most:**",
                        value=top_5, inline=False)

    last_5 = ""
    for clan in previous_clans:
        if clan.stay_type == StayType.unknown:
            continue
        last_5 += f"[{clan.clan_name}]({clan.share_link}), {clan.role.in_game_name}"
        if clan.stay_type == StayType.stay:
            last_5 += f", {clan.stay_length.days} days" if clan.stay_length.days >= 1 else ""
            last_5 += f"\n<t:{int(clan.start_stay.time.timestamp())}:D> to <t:{int(clan.end_stay.time.timestamp())}:D>\n"
        elif clan.stay_type == StayType.seen:
            last_5 += f"\nSeen on <t:{int(clan.seen_date.time.timestamp())}:D>\n"

    if last_5 == "":
        last_5 = "No Clans Found"
    embed.add_field(name="**Last 5 Clans Player has been seen at:**", value=last_5, inline=False)

    embed.set_footer(text="Data from ClashofStats.com")
    return embed


async def create_profile_troops(bot, result):
    player = result
    hero = heros(bot=bot, player=player)
    pets = heroPets(bot=bot, player=player)
    troop = troops(bot=bot, player=player)
    deTroop = deTroops(bot=bot, player=player)
    siege = siegeMachines(bot=bot, player=player)
    spell = spells(bot=bot, player=player)

    embed = disnake.Embed(title="You are looking at " + player.name,
                           description="Troop, hero, & spell levels for this account.",
                           color=disnake.Color.green())
    embed.add_field(name=f'__**{player.name}** (Th{player.town_hall})__ {player.trophies}', value="Profile: " + f'[{player.tag}]({player.share_link})',
                     inline=False)

    if (hero is not None):
        embed.add_field(name="**Heroes:** ", value=hero, inline=False)

    if (pets is not None):
        embed.add_field(name="**Pets:** ", value=pets, inline=False)

    if (troop is not None):
        embed.add_field(name="**Elixir Troops:** ", value=troop, inline=False)

    if (deTroop is not None):
        embed.add_field(name="**Dark Elixir Troops:** ", value=deTroop, inline=False)

    if (siege is not None):
        embed.add_field(name="**Siege Machines:** ", value=siege, inline=False)

    if (spell is not None):
        embed.add_field(name="**Spells:** ", value=spell, inline=False)

    return embed


async def upgrade_embed(bot: CustomClient, player: coc.Player):
    home_elixir_troops = ""
    home_de_troops = ""
    siege_machines = ""
    bb_troops = ""

    troops_found = []
    troop_levels = 0
    troop_levels_missing = 0
    for troop in player.troops:
        if troop.is_super_troop:
            continue
        troops_found.append(troop.name)
        troop_emoji = bot.fetch_emoji(name=troop.name)
        prev_level_max = troop.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = troop.level

        th_max = troop.get_max_level_for_townhall(player.town_hall)
        troop_levels += th_max
        troop_levels_missing += (th_max - troop.level)
        th_max = f"{th_max}".ljust(2)
        level = f"{troop.level}".rjust(2)
        days = f"{int(troop.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(troop.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(troop.upgrade_cost)}".ljust(5)
        if troop.level < prev_level_max:  # rushed
            if troop.is_siege_machine:
                siege_machines += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif troop.is_elixir_troop:
                home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif troop.is_dark_troop:
                home_de_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif troop.is_builder_base:
                bb_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"

        elif troop.level < troop.get_max_level_for_townhall(player.town_hall):  # not max
            if troop.is_elixir_troop:
                if troop.is_siege_machine:
                    siege_machines += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
                else:
                    home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif troop.is_dark_troop:
                home_de_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif troop.is_builder_base:
                bb_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"

    for troop in coc.HOME_TROOP_ORDER:
        if troop not in troops_found:
            troop: coc.Troop = bot.coc_client.get_troop(name=troop, is_home_village=True, townhall=player.town_hall)
            troop_emoji = bot.fetch_emoji(name=troop.name)
            th_max = troop.get_max_level_for_townhall(player.town_hall)
            troop_unlock = troop.lab_level[2]
            convert_lab = troop.lab_to_townhall
            troop_unlock = convert_lab[troop_unlock]
            if player.town_hall >= troop_unlock:
                troop_levels += th_max
                troop_levels_missing += (th_max)
                th_max = f"{th_max}".ljust(2)
                level = f"0".rjust(2)
                if troop.is_siege_machine:
                    siege_machines += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"
                elif troop.is_elixir_troop:
                    home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"
                elif troop.is_dark_troop:
                    home_de_troops += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"

    elixir_spells = ""
    de_spells = ""
    found_spells = []
    spell_levels= 0
    spell_levels_missing = 0
    for spell in player.spells:
        troop_emoji = bot.fetch_emoji(name=spell.name)
        found_spells.append(spell.name)
        prev_level_max = spell.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = spell.level


        th_max = spell.get_max_level_for_townhall(player.town_hall)
        spell_levels += th_max
        spell_levels_missing += (th_max - spell.level)
        th_max = f"{th_max}".ljust(2)
        level = f"{spell.level}".rjust(2)
        days = f"{int(spell.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(spell.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(spell.upgrade_cost)}".ljust(5)
        if spell.level < prev_level_max:  # rushed
            if spell.is_elixir_spell:
                elixir_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif spell.is_dark_spell:
                de_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
        elif spell.level < spell.get_max_level_for_townhall(player.town_hall):  # not max
            if spell.is_elixir_spell:
                elixir_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif spell.is_dark_spell:
                de_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"


    for spell in coc.SPELL_ORDER:
        if spell not in found_spells:
            spell: coc.Spell = bot.coc_client.get_spell(name=spell, townhall=player.town_hall)
            troop_emoji = bot.fetch_emoji(name=spell.name)
            th_max = spell.get_max_level_for_townhall(player.town_hall)
            if th_max is None:
                continue
            spell_levels += th_max
            spell_levels_missing += (th_max)
            troop_unlock = spell.lab_level[2]
            convert_lab = spell.lab_to_townhall
            troop_unlock = convert_lab[troop_unlock]
            if player.town_hall >= troop_unlock:
                th_max = f"{th_max}".ljust(2)
                level = f"0".rjust(2)
                if spell.is_elixir_spell:
                    elixir_spells += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"
                elif spell.is_dark_spell:
                    de_spells += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"

    hero_levels = 0
    hero_levels_missing = 0
    hero_text = ""
    for hero in player.heroes:
        troop_emoji = bot.fetch_emoji(name=hero.name)
        hero_levels += hero.level
        if hero.required_th_level == player.town_hall:
            prev_level_max = None
        else:
            prev_level_max = hero.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = hero.level


        th_max = hero.get_max_level_for_townhall(player.town_hall)
        hero_levels_missing += (th_max - hero.level)
        th_max = f"{th_max}".ljust(2)
        level = f"{hero.level}".rjust(2)
        days = f"{int(hero.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(hero.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(hero.upgrade_cost)}".ljust(5)
        if hero.level < prev_level_max:  # rushed
            hero_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"

        elif hero.level < hero.get_max_level_for_townhall(player.town_hall):  # not max
            hero_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"

    pet_text = ""

    for pet in player.pets:
        troop_emoji = bot.fetch_emoji(name=pet.name)
        new_pets = ["Diggy", "Frosty", "Phoenix", "Poison Lizard"]

        th_max = f"{10}".ljust(2)
        level = f"{pet.level}".rjust(2)
        days = f"{int(pet.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(pet.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(pet.upgrade_cost)}".ljust(5)
        if pet.level < 10 and pet.name not in new_pets and player.town_hall == 15:  # rushed
            pet_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
        elif pet.level < 10:  # not max
            pet_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"


    full_text = ""
    if home_elixir_troops != "":
        full_text += f"**Elixir Troops**\n{home_elixir_troops}\n"
    if home_de_troops != "":
        full_text += f"**Dark Elixir Troops**\n{home_de_troops}\n"
    if hero_text != "":
        full_text += f"**Heros**\n{hero_text}\n"
    if pet_text != "":
        full_text += f"**Hero Pets**\n{pet_text}\n"
    if elixir_spells != "":
        full_text += f"**Elixir Spells**\n{elixir_spells}\n"
    if de_spells != "":
        full_text += f"**Dark Elixir Spells**\n{de_spells}\n"
    if siege_machines != "":
        full_text += f"**Siege Machines**\n{siege_machines}\n"

    embed2 = False
    if bb_troops != "":
        embed2 = disnake.Embed(description=f"**Builder Base Troops**\n{bb_troops}\n",colour=disnake.Color.green())

    if full_text == "":
        full_text = "No Heros, Pets, Spells, or Troops left to upgrade\n"

    if hero_levels_missing == 0:
        hero_levels_missing = "0.00%"
    else:
        hero_levels_missing = f"{round((hero_levels_missing/(hero_levels+hero_levels_missing)) * 100, 2)}%"

    if troop_levels_missing == 0:
        troop_levels_missing = "0.00%"
    else:
        troop_levels_missing = f"{round((troop_levels_missing / (troop_levels)) * 100, 2)}%"

    if spell_levels_missing == 0:
        spell_levels_missing = "0.00%"
    else:
        spell_levels_missing = f"{round((spell_levels_missing / (spell_levels)) * 100, 2)}%"

    #print(full_text)
    embed = disnake.Embed(title=f"{player.name} | TH{player.town_hall}", description=full_text, colour=disnake.Color.green())
    if embed2 is not False:
        embeds = [embed, embed2]
    else:
        embeds = [embed]
    embeds[-1].set_footer(text="✗ = rushed for th level")
    embeds[-1].description += f"Hero Lvl Left: {hero_levels_missing}\n" \
                 f"Troop Lvl Left: {troop_levels_missing}\n" \
                 f"Spell Lvl Left: {spell_levels_missing}\n"
    return embeds


async def create_player_list(bot: CustomClient, discord_user: disnake.Member, players: List[MyCustomPlayer], embed_color = disnake.Color.green()):
    total_stats = {"donos" : 0, "rec" : 0, "war_stars" : 0, "th" : 0, "attacks" : 0, "trophies" : 0, "total_donos" : 0}
    text = ""
    for count, player in enumerate(players):
        if count < 20:
            opt_emoji = bot.emoji.opt_in if player.war_opted_in else bot.emoji.opt_out
            heros = ""
            for hero in player.heroes:
                if hero.is_home_base:
                    level = f"{hero.level}" if hero.is_max_for_townhall else f"{hero.level}"
                    heros += f"{acronym(hero.name)}{level} "
            if heros != "" and len([h for h in player.heroes if h.is_home_base]) >= 2:
                heros += f"{sum([h.level for h in player.heroes if h.is_home_base])}"

            text += f"{opt_emoji}**[{player.clear_name}{create_superscript(player.town_hall)}]({player.share_link})** | {league_to_emoji(player.league_as_string)}{player.trophies}\n" \

            if heros != "":
                text += f"- `{heros}`\n"

            text += f"- Donos: ▲`{player.donos().donated:<4}` ▼`{player.donos().received:<4}`\n"

            text += "\n"
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"{discord_user.display_name} Accounts ({len(players)})", icon_url=discord_user.display_avatar)
    if len(players) > 20:
        embed.set_footer(text="Only top 20 accounts are shown due to character limitations")
    return embed


async def to_do_embed(bot: CustomClient, discord_user, linked_accounts , embed_color = disnake.Color.green()):
    embed = disnake.Embed(title=f"{discord_user.display_name} To-Do List", color=disnake.Color.green())
    if linked_accounts == []:
        embed.description = "No accounts linked, use `/link` to get started!"
        return embed

    war_hits_to_do = await get_war_hits(bot=bot, linked_accounts=linked_accounts)
    if war_hits_to_do != "":
        embed.add_field(name="War Hits", value=war_hits_to_do, inline=False)

    legend_hits_to_do = await get_legend_hits(linked_accounts=linked_accounts)
    if legend_hits_to_do != "":
        embed.add_field(name="Legend Hits", value=legend_hits_to_do, inline=False)

    raid_hits_to_do = await get_raid_hits(bot=bot, linked_accounts=linked_accounts)
    if raid_hits_to_do != "":
        embed.add_field(name="Raid Hits", value=raid_hits_to_do, inline=False)

    clangames_to_do = await get_clan_games(linked_accounts=linked_accounts)
    if clangames_to_do != "":
        embed.add_field(name="Clan Games", value=clangames_to_do, inline=False)

    pass_to_do = await get_pass(bot=bot, linked_accounts=linked_accounts)
    if pass_to_do != "":
        embed.add_field(name="Season Pass", value=pass_to_do, inline=False)

    inactive_to_do = await get_inactive(linked_accounts=linked_accounts)
    if inactive_to_do != "":
        embed.add_field(name="Inactive Accounts (48+ hr)", value=inactive_to_do, inline=False)

    if len(embed.fields) == 0:
        embed.description = "You're all caught up chief!"

    return embed


async def get_war_hits(bot:CustomClient, linked_accounts: List[MyCustomPlayer]):
    async def get_clan_wars(clan_tag, player):
        war = await bot.get_clanwar(clanTag=clan_tag)
        if war is not None and str(war.state) == "notInWar":
            war = None
        if war is not None and war.end_time.seconds_until <= 0:
            war = None
        return (player, war)

    tasks = []
    for player in linked_accounts:
        if player.clan is not None:
            task = asyncio.ensure_future(get_clan_wars(clan_tag=player.clan.tag, player=player))
            tasks.append(task)
    wars = await asyncio.gather(*tasks)

    war_hits = ""
    for player, war in wars:
        if war is None:
            continue
        war: coc.ClanWar
        our_player = coc.utils.get(war.members, tag=player.tag)
        if our_player is None:
            continue
        attacks = our_player.attacks
        required_attacks = war.attacks_per_member
        if len(attacks) < required_attacks:
            war_hits += f"({len(attacks)}/{required_attacks}) | <t:{int(war.end_time.time.replace(tzinfo=utc).timestamp())}:R> - {player.name}\n"
    return war_hits


async def get_legend_hits(linked_accounts: List[MyCustomPlayer]):
    legend_hits_remaining = ""
    for player in linked_accounts:
        if player.is_legends():
            if player.legend_day().num_attacks.integer < 8:
                legend_hits_remaining += f"({player.legend_day().num_attacks.integer}/8) - {player.name}\n"
    return legend_hits_remaining


async def get_raid_hits(bot:CustomClient, linked_accounts: List[MyCustomPlayer]):
    async def get_raid(clan_tag, player):
        if player.town_hall <= 5:
            return (player, None)
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=player.clan, weekend=weekend, bot=bot, limit=2)
        if weekend_raid_entry is not None and str(weekend_raid_entry.state) == "ended":
            weekend_raid_entry = None
        return (player, weekend_raid_entry)

    tasks = []
    for player in linked_accounts:
        if player.clan is not None:
            task = asyncio.ensure_future(get_raid(clan_tag=player.clan.tag, player=player))
            tasks.append(task)
    wars = await asyncio.gather(*tasks)

    raid_hits = ""
    for player, raid_log_entry in wars:
        if raid_log_entry is None:
            continue
        our_player = coc.utils.get(raid_log_entry.members, tag=player.tag)
        if our_player is None:
            attacks = 0
            required_attacks = 6
        else:
            attacks = our_player.attack_count
            required_attacks = our_player.attack_limit + our_player.bonus_attack_limit
        if attacks < required_attacks:
            raid_hits += f"({attacks}/{required_attacks}) - {player.name}\n"
    return raid_hits


async def get_inactive(linked_accounts: List[MyCustomPlayer]):
    now = int(datetime.now(tz=utc).timestamp())
    inactive_text = ""
    for player in linked_accounts:
        last_online = player.last_online
        # 48 hours in seconds
        if last_online is None:
            continue
        if now - last_online >= (48 * 60 * 60):
            inactive_text += f"<t:{last_online}:R> - {player.name}\n"
    return inactive_text


async def get_clan_games(linked_accounts: List[MyCustomPlayer]):
    missing_clan_games = ""
    zeros = ""
    num_zeros = 0
    if is_clan_games():
        for player in linked_accounts:
            points = player.clan_games()
            if points < 4000:
                if points == 0:
                    zeros += f"({points}/4000) - {player.name}\n"
                    num_zeros += 1
                else:
                    missing_clan_games += f"({points}/4000) - {player.name}\n"

    if num_zeros == len(linked_accounts):
        missing_clan_games = "(0/4000) on All Accounts "
    elif num_zeros >= 5:
        missing_clan_games += "(0/4000) on All Other Accounts"
    else:
        missing_clan_games += zeros

    return missing_clan_games


async def get_pass(bot: CustomClient, linked_accounts: List[MyCustomPlayer]):
    pass_text = ""
    points = 3000 if bot.gen_games_season() == "2023-06" else 4000
    l = sorted(linked_accounts, key=lambda x: x.season_pass(), reverse=True)
    for player in l:
        season_pass_points = player.season_pass()
        if season_pass_points < points and season_pass_points != 0:
            pass_text += f"({season_pass_points}/3000) - {player.name}\n"
    return pass_text


def is_clan_games():
    now = datetime.utcnow().replace(tzinfo=utc)
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    first = datetime(year, month, 22, hour=8, tzinfo=utc)
    end = datetime(year, month, 28, hour=8, tzinfo=utc)
    if (day >= 22 and day <= 28):
        if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
            is_games = False
        else:
            is_games = True
    else:
        is_games = False
    return is_games


async def cwl_stalk(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
    tags = await bot.link_client.get_linked_players(discord_id=member.id)
    if not tags:
        return await ctx.send("No players linked.")
    # players = await self.bot.get_players(tags=tags)
    first_of_month = int(datetime.now().replace(day=1, hour=1).timestamp())
    true_month = datetime.now().month
    month = calendar.month_name[true_month]

    townhalls_attacked = []
    my_townhalls = []
    hits = defaultdict(list)
    percents = defaultdict(list)
    embeds = []
    townhalls_defended = []
    defense_hits = defaultdict(list)
    defense_percents = defaultdict(list)

    for player in tags:
        results = await bot.warhits.find({"$and": [
            {"tag": player},
            {"war_type": "cwl"},
            {"_time": {"$gte": first_of_month}}
        ]}).sort("_time", 1).to_list(length=10)
        text = ""
        if not results:
            continue

        f = []
        for result in results:
            if result in f:
                continue
            else:
                f.append(result)
        results = f
        townhall = 1
        name = ""
        clan_tag = ""
        for day, result in enumerate(results, 1):
            hits[f"{result['townhall']}v{result['defender_townhall']}"].append(result['stars'])
            percents[f"{result['townhall']}v{result['defender_townhall']}"].append(result['destruction'])
            my_townhalls.append(result['townhall'])
            townhalls_attacked.append([result['defender_townhall']])
            star_str = ""
            stars = result['stars']
            for x in range(0, stars):
                star_str += "★"
            for x in range(0, 3 - stars):
                star_str += "☆"
            text += f"`Day {day} `| {star_str}`{result['destruction']:3}%`{emojiDictionary(result['townhall'])}" \
                    f" **►** " \
                    f"{emojiDictionary(result['defender_townhall'])}\n"
            townhall = result['townhall']
            name = result['name']
            clan_tag = result['clan']

        defense_text = ""
        defense_results = await bot.warhits.find({"$and": [
            {"defender_tag": player},
            {"war_type": "cwl"},
            {"_time": {"$gte": first_of_month}}
        ]}).sort("_time", 1).to_list(length=10)
        for day, result in enumerate(defense_results, 1):
            defense_hits[f"{result['defender_townhall']}v{result['townhall']}"].append(result['stars'])
            defense_percents[f"{result['defender_townhall']}v{result['townhall']}"].append(result['destruction'])
            townhalls_defended.append([result['defender_townhall']])
            star_str = ""
            stars = result['stars']
            for x in range(0, stars):
                star_str += "★"
            for x in range(0, 3 - stars):
                star_str += "☆"
            defense_text += f"`Day {day} `| {star_str}`{result['destruction']:3}%` {emojiDictionary(result['townhall'])}" \
                            f" **►** " \
                            f"{emojiDictionary(result['defender_townhall'])}\n"
        if defense_text == "":
            defense_text = "No Defenses Yet"

        others_in_same_clan = await bot.warhits.find({"$and": [
            {"clan": clan_tag},
            {"war_type": "cwl"},
            {"_time": {"$gte": first_of_month}}
        ]}).to_list(length=1000)
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        for result in others_in_same_clan:
            star_dict[result["tag"]] += result["stars"]
            dest_dict[result["tag"]] += result["destruction"]

        star_list = []
        for tag, stars in star_dict.items():
            star_list.append([tag, stars, dest_dict[tag]])
        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)

        placement = 0
        for count, item in enumerate(sorted_list, 1):
            if item[0] == player:
                placement = count
                break

        clan = await bot.getClan(clan_tag=clan_tag)
        embed = disnake.Embed(title=f"{name} | {clan.name}", color=disnake.Color.green())
        embed.add_field(name="Attacks", value=text, inline=False)
        embed.add_field(name="Defenses", value=defense_text, inline=False)
        embed.set_footer(icon_url=clan.badge.url,
                         text=f"#{placement}/{len(sorted_list)} in CWL Group | {clan.war_league.name}")
        embeds.append(embed)

    last_30_days = await bot.warhits.find({"$and": [
        {"tag": {"$in": tags}},
        {"war_type": {"$in": ["cwl", "random"]}},
        {"_time": {"$gte": int((datetime.now() - timedelta(days=35)).timestamp())}}
    ]}).sort("_time", 1).to_list(length=1000)
    seconds = []
    for result in last_30_days:
        time = datetime.fromtimestamp(result['_time'])
        seconds.append((time.hour * 60 * 60) + (time.minute * 60) + (time.second))
    average_seconds = int(sum(seconds) / len(seconds))
    now = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    average_time = datetime.fromtimestamp(now + average_seconds)
    average_time = f"<t:{int(average_time.timestamp())}:t>"

    def average(item):
        return (round(sum(item) / len(item), 2))

    def sort_by_th(item: str):
        return int(item.split("v")[0])

    def sort_by_other_th(item: str):
        return int(item.split("v")[-1])

    sorted_hits = sorted(hits.items(), key=lambda x: (sort_by_th(x[0]), sort_by_other_th(x[0])), reverse=True)
    # sorted_hits = sorted(sorted_hits.items(), key=lambda item: item[1])
    sorted_hits = dict(sorted_hits)
    th_text = "THvTH";
    stars_text = "Stars";
    perc_text = "Perc%"
    hitrate_text = f"`{th_text:>5} {stars_text:>4}{perc_text:>6}`\n"
    for type, stars in sorted_hits.items():
        hitrate_text += f"`{type:>5} {average(stars):>4.2f} {average(percents[type]):>5.1f}%`\n"
    if not embeds:
        return await ctx.send(embed=disnake.Embed(description=f"No CWL Stats found for {member.display_name}",
                                                  color=disnake.Color.red()))
    main_embed = disnake.Embed(title=f"{member.display_name} CWL Stats | {month} {datetime.now().year}",
                               description=f"Avg. Attacks Around: {average_time}\n"
                                           f"**Average Hitrates:**\n{hitrate_text}",
                               color=disnake.Color.gold())

    buttons = []
    if len(embeds) > 4:
        buttons = [disnake.ui.ActionRow(
            disnake.ui.Button(label=f"Next {min(5, len(embeds[4:9]))} Accounts", style=disnake.ButtonStyle.grey,
                              custom_id="more_accounts"))]

    start_page = -1
    end_page = 4
    await ctx.send(embeds=([main_embed] + embeds)[:5], components=buttons)
    if len(embeds) <= 4:
        return
    message = await ctx.original_message()
    while True:
        try:
            res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, msg=message)
        except:
            return await message.edit(components=[])
        start_page += 5
        end_page += 5
        await message.edit(components=[])
        buttons = None
        if len(embeds[start_page + 5:end_page + 5]) >= 1:
            buttons = [disnake.ui.ActionRow(
                disnake.ui.Button(label=f"Next {min(5, len(embeds[start_page + 5:end_page + 5]))} Accounts",
                                  style=disnake.ButtonStyle.grey, custom_id="more_accounts"))]
        message = await ctx.followup.send(embeds=embeds[start_page:end_page], components=buttons)


async def raid_stalk(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
    tags = await bot.link_client.get_linked_players(discord_id=member.id)
    # players = await self.bot.get_players(tags=tags)
    first_of_month = int(datetime.now().replace(day=1, hour=1).timestamp())
    true_month = datetime.now().month
    month = calendar.month_name[true_month]
    if not tags:
        return await ctx.send(content="No players linked.")
    embeds = []
    total_looted = 0
    total_medals = 0
    clans = []
    highest_looted = 0
    highest_medals = 0
    num_accounts = 0
    for player in tags:
        member_looted = 0
        member_medals = 0
        results = await bot.raid_weekend_db.find({"data.members.tag": player}).sort("data.startTime",1).to_list(length=8)
        if not results:
            continue
        text = ""
        member = None
        num_accounts += 1
        for result in results:
            member_result = next((item for item in result["data"]["members"] if item['tag'] == player), None)
            member = RaidMember(client=bot.coc_client, data=member_result,
                                    raid_log_entry=RaidLogEntry(client=bot.coc_client, data=result["data"], clan_tag=result["clan_tag"]))
            member = member
            raid: RaidLogEntry = member.raid_log_entry
            text += f"{bot.emoji.capital_gold}`{member.capital_resources_looted:5} | `{bot.emoji.thick_sword}`{member.attack_count:1} " \
                    f"| `{bot.emoji.raid_medal}`{(raid.offensive_reward * member.attack_count) + raid.defensive_reward:4} | {raid.end_time.time.strftime('%m-%d')}`\n"
            total_looted += member.capital_resources_looted
            if member.capital_resources_looted > highest_looted:
                highest_looted = member.capital_resources_looted
            member_looted += member.capital_resources_looted
            total_medals += (raid.offensive_reward * member.attack_count) + raid.defensive_reward

            if (raid.offensive_reward * member.attack_count) + raid.defensive_reward > highest_medals:
                highest_medals = (raid.offensive_reward * member.attack_count) + raid.defensive_reward
            member_medals += (raid.offensive_reward * member.attack_count) + raid.defensive_reward
            clans.append(result["clan_tag"])

        text = f"**Totals: {bot.emoji.capital_gold}{'{:,}'.format(member_looted)} | {bot.emoji.raid_medal}{member_medals}**\n{text}"
        embed = disnake.Embed(title=f"{member.name} Raid Performance", description=text,
                              color=disnake.Color.green())
        embeds.append(embed)

    if not embeds:
        return await ctx.send("No Clan Capital Stats Found")
    main_embed = disnake.Embed(title=f"{ctx.author.display_name} Raid Stats | (last 8 weeks)",
                               description=f"*Raided from {len(set(clans))} different clans w/ {num_accounts} accounts*\n"
                                           f"**Highest Medals:** {bot.emoji.raid_medal}{highest_medals}\n"
                                           f"**Highest Looted:** {bot.emoji.capital_gold}{'{:,}'.format(highest_looted)}\n"
                                           f"**Totals:** {bot.emoji.capital_gold}{'{:,}'.format(total_looted)} | {bot.emoji.raid_medal}{'{:,}'.format(total_medals)}",
                               color=disnake.Color.gold())
    buttons = []
    if len(embeds) > 4:
        buttons = [disnake.ui.ActionRow(
            disnake.ui.Button(label=f"Next {min(5, len(embeds[4:9]))} Accounts", style=disnake.ButtonStyle.grey,
                              custom_id="more_accounts"))]

    start_page = -1
    end_page = 4
    await ctx.send(embeds=([main_embed] + embeds)[:5], components=buttons)
    if len(embeds) <= 4:
        return
    message = await ctx.original_message()
    while True:
        try:
            res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, msg=message)
        except:
            return await message.edit(components=[])
        start_page += 5
        end_page += 5
        await message.edit(components=[])
        buttons = None
        if len(embeds[start_page + 5:end_page + 5]) >= 1:
            buttons = [disnake.ui.ActionRow(
                disnake.ui.Button(label=f"Next {min(5, len(embeds[start_page + 5:end_page + 5]))} Accounts",
                                  style=disnake.ButtonStyle.grey, custom_id="more_accounts"))]
        message = await ctx.followup.send(embeds=embeds[start_page:end_page], components=buttons)


async def create_player_hr(bot: CustomClient, player: MyCustomPlayer, start_date, end_date):
    embed = disnake.Embed(title=f"{player.name} War Stats", colour=disnake.Color.green())
    time_range = f"{datetime.fromtimestamp(start_date).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_date).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=player.town_hall_cls.image_url, text=time_range)
    hitrate = await player.hit_rate(start_timestamp=start_date, end_timestamp=end_date)
    hr_text = ""
    for hr in hitrate:
        hr_type = f"{hr.type}".ljust(5)
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        hr_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
    if hr_text == "":
        hr_text = "No war hits tracked.\n"
    embed.add_field(name="**Triple Hit Rate**", value=hr_text + "­\n", inline=False)

    defrate = await player.defense_rate(start_timestamp=start_date, end_timestamp=end_date)
    def_text = ""
    for hr in defrate:
        hr_type = f"{hr.type}".ljust(5)
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        def_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
    if def_text == "":
        def_text = "No war defenses tracked.\n"
    embed.add_field(name="**Triple Defense Rate**", value=def_text + "­\n", inline=False)

    text = ""
    hr = hitrate[0]
    footer_text = f"Avg. Off Stars: `{round(hr.average_stars, 2)}`"
    if hr.total_zeros != 0:
        hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
        text += f"`Off 0 Stars` | `{hr_nums}` | {round(hr.average_zeros * 100, 1)}%\n"
    if hr.total_ones != 0:
        hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
        text += f"`Off 1 Stars` | `{hr_nums}` | {round(hr.average_ones * 100, 1)}%\n"
    if hr.total_twos != 0:
        hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
        text += f"`Off 2 Stars` | `{hr_nums}` | {round(hr.average_twos * 100, 1)}%\n"
    if hr.total_triples != 0:
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        text += f"`Off 3 Stars` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"

    hr = defrate[0]
    footer_text += f"\nAvg. Def Stars: `{round(hr.average_stars, 2)}`"
    if hr.total_zeros != 0:
        hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
        text += f"`Def 0 Stars` | `{hr_nums}` | {round(100 - (hr.average_zeros * 100), 1)}%\n"
    if hr.total_ones != 0:
        hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
        text += f"`Def 1 Stars` | `{hr_nums}` | {round(100 - (hr.average_ones * 100), 1)}%\n"
    if hr.total_twos != 0:
        hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
        text += f"`Def 2 Stars` | `{hr_nums}` | {round(100 - (hr.average_twos * 100), 1)}%\n"
    if hr.total_triples != 0:
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        text += f"`Def 3 Stars` | `{hr_nums}` | {round(100 - (hr.average_triples * 100), 1)}%\n"

    if text == "":
        text = "No attacks/defenses yet.\n"
    embed.add_field(name="**Star Count %'s**", value=text + "­\n", inline=False)

    fresh_hr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
    nonfresh_hr = await player.hit_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
    fresh_dr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
    nonfresh_dr = await player.defense_rate(fresh_type=[False], start_timestamp=start_date,
                                            end_timestamp=end_date)
    hitrates = [fresh_hr, nonfresh_hr, fresh_dr, nonfresh_dr]
    names = ["Fresh HR", "Non-Fresh HR", "Fresh DR", "Non-Fresh DR"]
    text = ""
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f"{names[count]}".ljust(12)
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
    if text == "":
        text = "No attacks/defenses yet.\n"
    embed.add_field(name="**Fresh/Not Fresh**", value=text + "­\n", inline=False)

    random = await player.hit_rate(war_types=["random"], start_timestamp=start_date, end_timestamp=end_date)
    cwl = await player.hit_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
    friendly = await player.hit_rate(war_types=["friendly"], start_timestamp=start_date, end_timestamp=end_date)
    random_dr = await player.defense_rate(war_types=["random"], start_timestamp=start_date,
                                          end_timestamp=end_date)
    cwl_dr = await player.defense_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
    friendly_dr = await player.defense_rate(war_types=["friendly"], start_timestamp=start_date,
                                            end_timestamp=end_date)
    hitrates = [random, cwl, friendly, random_dr, cwl_dr, friendly_dr]
    names = ["War HR", "CWL HR", "Friendly HR", "War DR", "CWL DR", "Friendly DR"]
    text = ""
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f"{names[count]}".ljust(11)
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
    if text == "":
        text = "No attacks/defenses yet.\n"
    embed.add_field(name="**War Type**", value=text + "­\n", inline=False)

    war_sizes = list(range(5, 55, 5))
    hitrates = []
    for size in war_sizes:
        hr = await player.hit_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
        hitrates.append(hr)
    for size in war_sizes:
        hr = await player.defense_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
        hitrates.append(hr)

    text = ""
    names = [f"{size}v{size} HR" for size in war_sizes] + [f"{size}v{size} DR" for size in war_sizes]
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f"{names[count]}".ljust(8)
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
    if text == "":
        text = "No attacks/defenses yet.\n"
    embed.add_field(name="**War Size**", value=text + "­\n", inline=False)

    lost_hr = await player.hit_rate(war_statuses=["lost", "losing"], start_timestamp=start_date,
                                    end_timestamp=end_date)
    win_hr = await player.hit_rate(war_statuses=["winning", "won"], start_timestamp=start_date,
                                   end_timestamp=end_date)
    lost_dr = await player.defense_rate(war_statuses=["lost", "losing"], start_timestamp=start_date,
                                        end_timestamp=end_date)
    win_dr = await player.defense_rate(war_statuses=["winning", "won"], start_timestamp=start_date,
                                       end_timestamp=end_date)
    hitrates = [lost_hr, win_hr, lost_dr, win_dr]
    names = ["Losing HR", "Winning HR", "Losing DR", "Winning DR"]
    text = ""
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f"{names[count]}".ljust(11)
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
    if text == "":
        text = "No attacks/defenses yet.\n"
    embed.add_field(name="**War Status**", value=text + "­\n", inline=False)
    embed.description = footer_text

    return embed