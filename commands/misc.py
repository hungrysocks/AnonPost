import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
from io import BytesIO

class BotSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def bot_owner_check(self, interaction: discord.Interaction) -> bool:
        return await self.bot.is_owner(interaction.user)

    @app_commands.command(name='setname', description='Change the bot\'s name')
    @app_commands.check(bot_owner_check)
    @app_commands.describe(name='The new name for the bot')
    async def set_name(self, interaction: discord.Interaction, name: str):
        try:
            await self.bot.user.edit(username=name)
            await interaction.response.send_message(f'Bot name has been changed to {name}!', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I don\'t have permission to change my username.', ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f'Failed to change name: {e}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='setavatar', description='Change the bot\'s avatar')
    @app_commands.check(bot_owner_check)
    @app_commands.describe(avatar_url='The URL of the new avatar image')
    async def set_avatar(self, interaction: discord.Interaction, avatar_url: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status != 200:
                        await interaction.response.send_message('Failed to fetch the avatar image. Please check the URL.', ephemeral=True)
                        return
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        await interaction.response.send_message('URL does not point to a valid image.', ephemeral=True)
                        return
                    avatar_bytes = await response.read()
                    avatar_buffer = BytesIO(avatar_bytes)
                    avatar_buffer.seek(0)
            await self.bot.user.edit(avatar=avatar_buffer.read())
            await interaction.response.send_message('Bot avatar has been changed!', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I don\'t have permission to change my avatar.', ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f'Failed to change avatar: {e}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='say', description='Make the bot send a message to a specified channel')
    @app_commands.check(bot_owner_check)
    @app_commands.describe(channel='The channel to send the message to', message='The message to send')
    async def say(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        try:
            await channel.send(message)
            await interaction.response.send_message(f'Message sent to {channel.mention}', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I don\'t have permission to send messages in that channel.', ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f'Failed to send message: {e}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='setbio', description='Change the bot\'s bio')
    @app_commands.check(bot_owner_check)
    @app_commands.describe(bio='The new bio for the bot')
    async def set_bio(self, interaction: discord.Interaction, bio: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=bio))
            await interaction.response.send_message(f'Bot bio has been updated to: "{bio}"', ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f'Failed to update bio: {e}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

    @app_commands.command(name='setstatus', description='Change the bot\'s status')
    @app_commands.check(bot_owner_check)
    @app_commands.describe(status='The new status for the bot')
    async def set_status(self, interaction: discord.Interaction, status: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=status))
            await interaction.response.send_message(f'Bot status has been set to: {status}', ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f'Failed to set status: {e}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(BotSettings(bot))
