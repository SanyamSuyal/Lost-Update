import discord
from discord.ext import commands
import asyncio
import os
import sys
import importlib
import traceback
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cogs_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cogs_fix")

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Create a test bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='s!', intents=intents)

# Event to check loaded commands
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    
    # Check all commands
    command_list = list(bot.commands)
    logger.info(f"Total commands registered: {len(command_list)}")
    
    # Group commands by cog
    cog_commands = {}
    standalone_commands = []
    
    for command in command_list:
        cog_name = command.cog_name if command.cog else "No Cog"
        if cog_name not in cog_commands:
            cog_commands[cog_name] = []
        cog_commands[cog_name].append(command.name)
    
    # Log commands by cog
    for cog_name, commands_list in cog_commands.items():
        logger.info(f"Cog '{cog_name}' has {len(commands_list)} commands: {', '.join(commands_list)}")
    
    # Check loaded cogs
    loaded_cogs = list(bot.cogs.keys())
    logger.info(f"Loaded cogs: {loaded_cogs}")
    
    # Stop the bot after checking
    await bot.close()

# Load cogs
async def load_cogs():
    cogs_dir = os.path.join(current_dir, 'cogs')
    if not os.path.exists(cogs_dir):
        logger.error(f"Cogs directory not found: {cogs_dir}")
        return False
    
    logger.info(f"Found cogs directory: {cogs_dir}")
    
    success_count = 0
    error_count = 0
    
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py'):
            cog_name = filename[:-3]
            try:
                # Try reloading the module first to ensure fresh load
                try:
                    module = importlib.import_module(f'cogs.{cog_name}')
                    importlib.reload(module)
                except ModuleNotFoundError:
                    # If it fails, it wasn't loaded before
                    pass
                
                # Now load the extension
                await bot.load_extension(f'cogs.{cog_name}')
                logger.info(f"Successfully loaded cog: {cog_name}")
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {e}")
                logger.error(traceback.format_exc())
                error_count += 1
    
    logger.info(f"Cog loading complete. Success: {success_count}, Failed: {error_count}")
    return success_count > 0

async def main():
    try:
        # Load cogs
        loaded = await load_cogs()
        if not loaded:
            logger.error("No cogs were loaded successfully!")
            return
        
        # Start the bot
        await bot.start(TOKEN)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 