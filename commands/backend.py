import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import random
import string
import sqlite3
import aiohttp
from io import BytesIO


class AnonPost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.post_cooldowns = {}
        self.db = sqlite3.connect("anon_channels.db")
        self.cursor = self.db.cursor()
        self._initialize_db()

    def _initialize_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS anon_channels (
            channel_id INTEGER PRIMARY KEY
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            ban_end REAL
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_mappings (
            post_id TEXT PRIMARY KEY,
            message_id INTEGER,
            channel_id INTEGER
        )
        """)
        self.db.commit()
        self.banned_users = {}
        self.cursor.execute("SELECT user_id, ban_end FROM banned_users")
        for user_id, ban_end in self.cursor.fetchall():
            self.banned_users[user_id] = ban_end

    def _add_anon_channel(self, channel_id):
        self.cursor.execute("INSERT OR IGNORE INTO anon_channels (channel_id) VALUES (?)", (channel_id,))
        self.db.commit()

    def _remove_anon_channel(self, channel_id):
        self.cursor.execute("DELETE FROM anon_channels WHERE channel_id = ?", (channel_id,))
        self.db.commit()

    def _is_anon_channel(self, channel_id):
        self.cursor.execute("SELECT 1 FROM anon_channels WHERE channel_id = ?", (channel_id,))
        return self.cursor.fetchone() is not None

    def _add_ban(self, user_id, ban_end):
        self.cursor.execute("INSERT OR REPLACE INTO banned_users (user_id, ban_end) VALUES (?, ?)", (user_id, ban_end))
        self.db.commit()
        self.banned_users[user_id] = ban_end

    def _check_ban(self, user_id):
        if user_id in self.banned_users:
            ban_end = self.banned_users[user_id]
            current_time = asyncio.get_event_loop().time()
            if ban_end is None or current_time < ban_end:
                return True
            else:
                self.cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
                self.db.commit()
                del self.banned_users[user_id]
        return False

    def _save_post_mapping(self, post_id, message_id, channel_id):
        self.cursor.execute("INSERT OR REPLACE INTO post_mappings (post_id, message_id, channel_id) VALUES (?, ?, ?)", 
                          (post_id, message_id, channel_id))
        self.db.commit()

    def _get_post_mapping(self, post_id):
        self.cursor.execute("SELECT message_id, channel_id FROM post_mappings WHERE post_id = ?", (post_id,))
        return self.cursor.fetchone()

    @app_commands.command(name='setupanonch', description='Set up a channel to handle anonymous posts')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel='✅ Set up the channel')
    async def setup_anon_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if self._is_anon_channel(channel.id):
            await interaction.response.send_message('❌ This channel is already set up.', ephemeral=True)
            return
        self._add_anon_channel(channel.id)
        embed = discord.Embed(title='👻 This channel is now accepting Anonymous posts', description='', color=discord.Color.green())
        view = ui.View()
        view.add_item(ui.Button(label='Post 👻', style=discord.ButtonStyle.success, custom_id='post_button'))
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f'Anonymous channel set up in {channel.mention}.', ephemeral=True)

    @app_commands.command(name='removeanonch', description='Remove an anonymous channel setup')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel='The channel to remove from anonymous posts')
    async def remove_anon_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not self._is_anon_channel(channel.id):
            await interaction.response.send_message('❌ This channel is not set up as anonymous.', ephemeral=True)
            return
        self._remove_anon_channel(channel.id)
        await interaction.response.send_message(f'✅ Anonymous setup removed from {channel.mention}.', ephemeral=True)

    @app_commands.command(name='banuser', description='Ban a user from posting in anonymous channels')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user_id='The ID of the user to ban',
        duration='Duration of the ban'
    )
    @app_commands.choices(duration=[
        app_commands.Choice(name='1 Day', value='1_day'),
        app_commands.Choice(name='1 Month', value='1_month'),
        app_commands.Choice(name='Permanent', value='permanent')
    ])
    async def ban_user(self, interaction: discord.Interaction, user_id: str, duration: app_commands.Choice[str]):
        try:
            user_id = int(user_id)
        except ValueError:
            await interaction.response.send_message('Invalid user ID.', ephemeral=True)
            return
        ban_end = None
        if duration.value == '1_day':
            ban_end = asyncio.get_event_loop().time() + 86400
        elif duration.value == '1_month':
            ban_end = asyncio.get_event_loop().time() + 2592000
        self._add_ban(user_id, ban_end)
        await interaction.response.send_message(f'User {user_id} banned from posting for {duration.name}.', ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get('custom_id')
        if custom_id not in ('post_button',) and not custom_id.startswith('reply_'):
            return

        if self._check_ban(interaction.user.id):
            await interaction.response.send_message('❌ You are banned from posting.', ephemeral=True)
            return

        if interaction.user.id in self.post_cooldowns:
            cooldown_end = self.post_cooldowns[interaction.user.id]
            current_time = asyncio.get_event_loop().time()
            if current_time < cooldown_end:
                await interaction.response.send_message(f'❌ You are on cooldown. Try again in {int(cooldown_end - current_time)} seconds.', ephemeral=True)
                return

        if custom_id == 'post_button':
            modal = PostModal(self)
            await interaction.response.send_modal(modal)
        elif custom_id.startswith('reply_'):
            post_id = custom_id.split('_')[1]
            mapping = self._get_post_mapping(post_id)
            if not mapping:
                await interaction.response.send_message('❌ Post not found for replying.', ephemeral=True)
                return

            message_id, channel_id = mapping
            try:
                channel = self.bot.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
                await interaction.response.send_modal(ReplyModal(self, message, post_id))
            except discord.errors.NotFound:
                await interaction.response.send_message('❌ Original post not found.', ephemeral=True)
                return

class PostModal(ui.Modal, title='Create a Post'):
    name_input = ui.TextInput(label='Name (optional)', style=discord.TextStyle.short, placeholder='Leave blank for anonymous', required=False)
    title_input = ui.TextInput(label='Title (optional)', style=discord.TextStyle.short, placeholder='Enter post title', required=False)
    body_input = ui.TextInput(label='Body', style=discord.TextStyle.long, placeholder='Enter post body', required=True)
    image_input = ui.TextInput(label='Image URL (optional)', style=discord.TextStyle.short, placeholder='Enter image URL', required=True)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        if not self.cog._is_anon_channel(interaction.channel_id):
            await interaction.response.send_message('❌ This channel is not set up for anonymous posts.', ephemeral=True)
            return

        try:
            title = self.title_input.value or ''
            body = self.body_input.value
            image_url = self.image_input.value
            name = self.name_input.value or 'Anonymous'
            post_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            embed = discord.Embed(title=title, description=body, color=0x000001)
            embed.set_author(name=name, icon_url=interaction.client.user.avatar.url)
            embed.set_footer(text=f'Post ID: {post_id}')

            files = []
            if image_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            image_buffer = BytesIO(image_data)
                            file = discord.File(image_buffer, filename='image.png')
                            files.append(file)
                            embed.set_image(url='attachment://image.png')
                        else:
                            await interaction.response.send_message('❌ Failed to download image.', ephemeral=True)
                            return

            view = ui.View()
            view.add_item(ui.Button(label='Post 👻', style=discord.ButtonStyle.success, custom_id='post_button'))
            view.add_item(ui.Button(label='Reply 💬', style=discord.ButtonStyle.danger, custom_id=f'reply_{post_id}'))

            message = await interaction.channel.send(embed=embed, view=view, files=files)
            self.cog._save_post_mapping(post_id, message.id, interaction.channel_id)
            self.cog.post_cooldowns[interaction.user.id] = asyncio.get_event_loop().time() + 10

            await interaction.response.send_message('✅ Post created successfully.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'❌ Error creating post: {str(e)}', ephemeral=True)

class ReplyModal(ui.Modal, title='Reply to Post'):
    name_input = ui.TextInput(label='Your Name (optional)', style=discord.TextStyle.short, placeholder='Leave blank for anonymous', required=False)
    body_input = ui.TextInput(label='Reply Body', style=discord.TextStyle.long, placeholder='Enter your reply', required=True)
    image_input = ui.TextInput(label='Image URL (optional)', style=discord.TextStyle.short, placeholder='Enter image URL', required=False)

    def __init__(self, cog, message, post_id):
        super().__init__()
        self.cog = cog
        self.message = message
        self.post_id = post_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            body = self.body_input.value
            image_url = self.image_input.value
            name = self.name_input.value or 'Anonymous'
            embed = discord.Embed(description=body, color=0x26C6DA)
            embed.set_author(name=name, icon_url=interaction.client.user.avatar.url)
            embed.set_footer(text=f'Replied by {name}')

            files = []
            if image_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            image_buffer = BytesIO(image_data)
                            file = discord.File(image_buffer, filename='image.png')
                            files.append(file)
                            embed.set_image(url='attachment://image.png')
                        else:
                            await interaction.response.send_message('❌ Failed to download image.', ephemeral=True)
                            return

            thread = self.message.thread
            if not thread:
                thread = await self.message.create_thread(name=f'Replies to {self.post_id}', auto_archive_duration=60)

            await thread.send(embed=embed, files=files)
            self.cog.post_cooldowns[interaction.user.id] = asyncio.get_event_loop().time() + 10
            await interaction.response.send_message('✅ Reply sent successfully.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'❌ Error sending reply: {str(e)}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(AnonPost(bot))
