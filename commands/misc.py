import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp

class BotSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='setname', description='Change the bot\'s name')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(name='The new name for the bot')
    async def set_name(self, interaction: discord.Interaction, name: str):
        try:
            await self.bot.user.edit(username=name)
            await interaction.response.send_message(f'Bot name has been changed to {name}!', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I don\'t have permission to change my username.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='setav', description='Change the bot\'s avatar')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(avatar_url='The new avatar URL for the bot')
    async def set_avatar(self, interaction: discord.Interaction, avatar_url: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status != 200:
                        await interaction.response.send_message('Failed to fetch the avatar image. Please check the URL.', ephemeral=True)
                        return
                    avatar_bytes = await response.read()
            await self.bot.user.edit(avatar=avatar_bytes)
            await interaction.response.send_message('Bot avatar has been changed!', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I don\'t have permission to change my avatar.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='setbio', description='Change the bot\'s bio')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(bio='The new bio for the bot')
    async def set_bio(self, interaction: discord.Interaction, bio: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=bio))
            await interaction.response.send_message(f'Bot bio has been updated to: "{bio}"', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='setstatus', description='Change the bot\'s status')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(status='The new status for the bot')
    async def set_status(self, interaction: discord.Interaction, status: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=status))
            await interaction.response.send_message(f'Bot status has been set to: {status}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(BotSettings(bot))
