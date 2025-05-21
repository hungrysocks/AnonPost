import discord
from discord.ext import commands
import os

TOKEN = ''
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord')
    try:
        commands_path = os.path.join(os.path.dirname(__file__), 'commands')
        if not os.path.exists(commands_path):
            os.makedirs(commands_path)
        
        for filename in os.listdir(commands_path):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = filename[:-3]  
                try:
                    await bot.load_extension(f'commands.{cog_name}')
                    print(f'Loaded: {cog_name}')
                except Exception as e:
                    print(f'failed to load {cog_name}: {e}')
        
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error during setup: {e}')

if __name__ == '__main__':
    if not TOKEN:
        raise ValueError("No or improper token provided")
    
    bot.run(TOKEN)
