import discord
from discord.ext import commands, tasks
import aiosqlite
import os
import json
import asyncio
from datetime import datetime
import logging
from dotenv import load_dotenv
import random
import string
import sys

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("shop_bot")

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID', 0))
LTC_ADDRESS = os.getenv('LTC_ADDRESS')

# Print token info for debugging (don't log the full token for security)
if TOKEN:
    logger.info(f"Token loaded successfully. First 5 chars: {TOKEN[:5]}...")
    logger.info(f"Token length: {len(TOKEN)}")
else:
    logger.error("TOKEN NOT FOUND IN ENVIRONMENT VARIABLES!")
    logger.info("Environment variables available: " + str([k for k in os.environ.keys()]))
    logger.info("Current directory: " + os.getcwd())
    logger.info("Files in directory: " + str(os.listdir('.')))
    if os.path.exists('.env'):
        logger.info(".env file exists, checking content length")
        with open('.env', 'r') as f:
            env_content = f.read()
            logger.info(f".env file length: {len(env_content)} chars")
    else:
        logger.info(".env file does not exist")

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='s!', intents=intents, help_command=None)

# Store LTC address in bot so it can be accessed by cogs
bot.LTC_ADDRESS = LTC_ADDRESS

# Database path
DB_PATH = "shop_database.db"

# Enhanced colors for embeds with a more modern palette
COLORS = {
    "success": 0x43B581,  # Green
    "error": 0xF04747,    # Red
    "info": 0x7289DA,     # Blurple
    "warning": 0xFAA61A,  # Amber
    "shop": 0x36393F,     # Dark gray
    "payment": 0x5865F2,  # Discord blue
    "product": 0x9B59B6,  # Purple
    "admin": 0xE91E63,    # Pink
    "primary": 0x5865F2   # Discord blue
}

# Set bot's colors for easy access in cogs
bot.COLORS = COLORS

# Embed styling functions
def create_embed(title, description, color=COLORS["primary"], timestamp=True):
    """Create a beautifully styled embed with consistent formatting"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    if timestamp:
        embed.timestamp = datetime.now()
    
    # Add subtle footer branding
    embed.set_footer(text="Shop Bot 2.0", icon_url="https://i.imgur.com/1GMKahQ.png")
    return embed

# Make the embed function available to cogs
bot.create_embed = create_embed

# Function to generate confirmation keys
def generate_confirmation_key(length=8):
    """Generate a unique confirmation key for orders"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Initialize database
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Create items table
        await db.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price REAL,
            stock INTEGER,
            description TEXT,
            drive_link TEXT
        )
        ''')
        
        # Create orders table
        await db.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            ltc_amount REAL,
            status TEXT,
            confirmation_key TEXT,
            payment_confirmed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            delivered_at TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id)
        )
        ''')
        
        # Create banned users table
        await db.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
        ''')
        
        # Check for and add missing columns if needed
        # Check for payment_confirmed column in orders
        try:
            await db.execute("SELECT payment_confirmed FROM orders LIMIT 1")
        except aiosqlite.OperationalError:
            logger.info("Adding missing payment_confirmed column to orders table")
            await db.execute("ALTER TABLE orders ADD COLUMN payment_confirmed BOOLEAN DEFAULT 0")
        
        # Check for confirmation_key column in orders
        try:
            await db.execute("SELECT confirmation_key FROM orders LIMIT 1")
        except aiosqlite.OperationalError:
            logger.info("Adding missing confirmation_key column to orders table")
            await db.execute("ALTER TABLE orders ADD COLUMN confirmation_key TEXT")
        
        # Check for drive_link column in items
        try:
            await db.execute("SELECT drive_link FROM items LIMIT 1")
        except aiosqlite.OperationalError:
            logger.info("Adding missing drive_link column to items table")
            await db.execute("ALTER TABLE items ADD COLUMN drive_link TEXT")
        
        await db.commit()
        logger.info("Database initialization complete")

@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} has connected to Discord!')
    await init_db()
    check_payments.start()

# Tasks
@tasks.loop(minutes=2)
async def check_payments():
    """Check for pending payments and update if paid"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute(
                "SELECT id, user_id, item_id, total_price FROM orders WHERE status = 'pending' AND payment_confirmed = 0"
            ) as cursor:
                pending_orders = await cursor.fetchall()
        except aiosqlite.OperationalError as e:
            # If we still encounter an error with the column, log it and use a fallback query
            logger.error(f"Error in check_payments: {e}")
            async with db.execute(
                "SELECT id, user_id, item_id, total_price FROM orders WHERE status = 'pending'"
            ) as cursor:
                pending_orders = await cursor.fetchall()
        
        for order in pending_orders:
            order_id, user_id, item_id, total_price = order
            
            # In a real implementation, we would check the blockchain for payments
            # For this simplified version, we'll assume payments are manually confirmed
            
            # Fetch the user and send a reminder
            user = bot.get_user(user_id)
            if user:
                try:
                    payment_reminder = create_embed(
                        "💸 Payment Reminder",
                        f"Hey there! Just a reminder about your pending order.",
                        COLORS["info"]
                    )
                    payment_reminder.add_field(
                        name="Order Details",
                        value=f"**Order ID:** #{order_id}\n**Amount Due:** ${total_price:.2f}",
                        inline=False
                    )
                    payment_reminder.add_field(
                        name="Payment Instructions",
                        value=f"Please send **{total_price} LTC** to:\n`{LTC_ADDRESS}`\n\nAfter sending payment, use `s!confirm <confirmation_key>` to notify us.",
                        inline=False
                    )
                    
                    await user.send(embed=payment_reminder)
                except:
                    pass

@check_payments.before_loop
async def before_check_payments():
    await bot.wait_until_ready()

# Helper functions
async def is_admin(ctx):
    """Check if the user has admin permissions"""
    if not ctx.guild:
        return False
    
    admin_role = discord.utils.get(ctx.guild.roles, id=ADMIN_ROLE_ID)
    if admin_role and admin_role in ctx.author.roles:
        return True
    
    return ctx.author.guild_permissions.administrator

async def is_banned(user_id):
    """Check if a user is banned from using the shop"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None

# Add debug events to track command processing
@bot.event
async def on_message(message):
    # Don't process commands from the bot itself
    if message.author.bot:
        return
        
    # Debug message if it starts with command prefix
    if message.content.startswith('s!'):
        command_name = message.content.split()[0][2:] if ' ' in message.content else message.content[2:]
        logger.info(f"Command detected: {command_name} from {message.author}")
        
        # Check if the command exists
        cmd = bot.get_command(command_name)
        if cmd:
            logger.info(f"Found registered command: {cmd.name}")
        else:
            logger.warning(f"Command '{command_name}' not found in registered commands!")
    
    # Continue processing commands normally
    await bot.process_commands(message)

# Add a test command directly to the bot
@bot.command(name="ping")
async def ping(ctx):
    """Simple command to test if the bot is responding"""
    logger.info(f"Ping command received from {ctx.author}")
    await ctx.send(
        embed=create_embed(
            "🏓 Pong!",
            f"Bot is online and responding!\nLatency: {round(bot.latency * 1000)}ms",
            COLORS["success"]
        )
    )

# Error tracking for command processing
@bot.event
async def on_command_completion(ctx):
    logger.info(f"Command '{ctx.command.name}' completed successfully for {ctx.author}")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Error in command '{ctx.command.name if ctx.command else 'unknown'}': {error}")
    
    if isinstance(error, commands.CommandNotFound):
        logger.warning(f"Command not found: '{ctx.message.content}'")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            embed=create_embed(
                "❌ Error: Missing Argument",
                f"You're missing the `{error.param.name}` parameter.\nCheck `s!help` for proper command usage.",
                COLORS["error"]
            )
        )
    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            embed=create_embed(
                "❌ Error: Invalid Argument",
                "One of the values you provided isn't valid.\nCheck `s!help` for proper command usage.",
                COLORS["error"]
            )
        )
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(
            embed=create_embed(
                "🔒 Access Denied",
                "You don't have permission to use this command.",
                COLORS["error"]
            )
        )
    else:
        logger.error(f"Unhandled error: {error}")
        await ctx.send(
            embed=create_embed(
                "⚠️ Something Went Wrong",
                "An unexpected error occurred. Please try again later.",
                COLORS["error"]
            )
        )

# Load cogs
async def load_extensions():
    try:
        # Check if cogs directory exists
        if not os.path.exists('./cogs'):
            logger.error("Cogs directory not found!")
            logger.info(f"Current directory: {os.getcwd()}")
            logger.info(f"Directory contents: {os.listdir('.')}")
            
            # Try to find cogs in different locations
            possible_locations = ['./cogs', '/opt/render/project/src/cogs', '../cogs', '../../cogs']
            cogs_dir = None
            
            for loc in possible_locations:
                if os.path.exists(loc):
                    logger.info(f"Found cogs directory at: {loc}")
                    cogs_dir = loc
                    break
            
            if not cogs_dir:
                logger.error("Could not find cogs directory in any location!")
                return
        else:
            cogs_dir = './cogs'
            
        # Load the cogs from the found directory
        success = 0
        failed = 0
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py'):
                try:
                    logger.info(f"Attempting to load extension: cogs.{filename[:-3]}")
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Successfully loaded extension: {filename}")
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to load extension {filename}: {e}")
                    failed += 1
        
        logger.info(f"Cog loading complete - Success: {success}, Failed: {failed}")
    except Exception as e:
        logger.error(f"Error loading extensions: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Run the bot
async def main():
    # Start the monitoring server if imported
    if 'run_monitor' in globals():
        monitor_thread = run_monitor()
        logger.info("Monitor server started")
    
    # First connect to Discord
    async with bot:
        await load_extensions()
        
        # Sync app commands with Discord
        logger.info("Syncing commands with Discord...")
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        # Log all registered commands
        logger.info("Registered commands:")
        for command in bot.commands:
            logger.info(f"- {command.name}")
        
        # Start the bot
        await bot.start(TOKEN)

# Add a help command manually since we disabled the default
@bot.command(name="help")
async def custom_help(ctx, command_name=None):
    """Show help for all commands or a specific command"""
    logger.info(f"Help command invoked by {ctx.author}")
    
    if command_name:
        # Get specific command help
        command = bot.get_command(command_name)
        if command:
            embed = create_embed(
                f"Command: s!{command.name}",
                command.help or "No description available",
                COLORS["info"]
            )
            await ctx.send(embed=embed)
        else:
            embed = create_embed(
                "Command Not Found",
                f"No command named '{command_name}' was found. Use `s!help` to see all commands.",
                COLORS["error"]
            )
            await ctx.send(embed=embed)
        return
    
    # Create help embed for all commands
    embed = create_embed(
        "📋 Shop Bot Commands",
        "Here are all available commands:",
        COLORS["info"]
    )
    
    # Add general commands section
    general_commands = []
    admin_commands = []
    
    # Collect commands
    for command in sorted(bot.commands, key=lambda x: x.name):
        # Skip hidden commands
        if command.hidden:
            continue
            
        # Check if command is in AdminCommands cog
        is_admin = False
        if command.cog and command.cog.__class__.__name__ == 'AdminCommands':
            is_admin = True
            admin_commands.append(f"**s!{command.name}** - {command.help or 'No description'}")
        else:
            general_commands.append(f"**s!{command.name}** - {command.help or 'No description'}")
    
    # Add command sections
    if general_commands:
        embed.add_field(
            name="🛒 General Commands",
            value="\n".join(general_commands[:10]),
            inline=False
        )
        if len(general_commands) > 10:
            embed.add_field(
                name="🛒 More General Commands",
                value="\n".join(general_commands[10:]),
                inline=False
            )
    
    if admin_commands and await is_admin(ctx):
        embed.add_field(
            name="⚙️ Admin Commands",
            value="\n".join(admin_commands[:10]),
            inline=False
        )
        if len(admin_commands) > 10:
            embed.add_field(
                name="⚙️ More Admin Commands",
                value="\n".join(admin_commands[10:]),
                inline=False
            )
    
    await ctx.send(embed=embed)

# Add a status command to check if bot is responsive
@bot.command(name="status")
async def status_command(ctx):
    """Check the status of the bot and its components"""
    logger.info(f"Status command executed by {ctx.author}")
    
    embed = create_embed(
        "🤖 Bot Status",
        "Checking systems...",
        COLORS["info"]
    )
    
    # Add general bot info
    embed.add_field(
        name="Bot Information",
        value=f"**Name:** {bot.user.name}\n**ID:** {bot.user.id}\n**Latency:** {round(bot.latency * 1000)}ms",
        inline=False
    )
    
    # Count loaded cogs
    loaded_cogs = list(bot.cogs.keys())
    embed.add_field(
        name="Cogs Status",
        value=f"**Loaded Cogs:** {len(loaded_cogs)}\n" + 
              "\n".join([f"✅ {cog}" for cog in loaded_cogs]) or "No cogs loaded!",
        inline=False
    )
    
    # Count commands
    commands_count = len(bot.commands)
    embed.add_field(
        name="Commands Status",
        value=f"**Total Commands:** {commands_count}",
        inline=False
    )
    
    # Check database
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM items") as cursor:
                items_count = await cursor.fetchone()
                items_count = items_count[0] if items_count else 0
                
            async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
                orders_count = await cursor.fetchone()
                orders_count = orders_count[0] if orders_count else 0
                
        embed.add_field(
            name="Database Status",
            value=f"**Items:** {items_count}\n**Orders:** {orders_count}",
            inline=False
        )
    except Exception as e:
        embed.add_field(
            name="Database Status",
            value=f"❌ Error: {str(e)}",
            inline=False
        )
    
    # Token status check
    token_status = "✅ Valid" if bot.is_ready() else "❌ Invalid"
    embed.add_field(
        name="Environment Status",
        value=f"**Token:** {token_status}\n**LTC Address:** {'✅ Set' if LTC_ADDRESS else '❌ Missing'}",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Add debug command
@bot.command(name="debugcog")
async def debug_cog(ctx, cog_name: str = None):
    """Debug information about a specific cog or all cogs"""
    logger.info(f"Debug cog command executed by {ctx.author}")
    
    if not await is_admin(ctx):
        return await ctx.send(
            embed=create_embed(
                "🔒 Access Denied",
                "You don't have permission to use this command.",
                COLORS["error"]
            )
        )
    
    if cog_name:
        # Check specific cog
        cog = bot.get_cog(cog_name)
        if not cog:
            return await ctx.send(
                embed=create_embed(
                    "❌ Cog Not Found",
                    f"No cog named '{cog_name}' is loaded.",
                    COLORS["error"]
                )
            )
        
        # Get commands from this cog
        cog_commands = [command.name for command in bot.commands if command.cog_name == cog_name]
        
        embed = create_embed(
            f"🔍 Cog: {cog_name}",
            f"Debug information for cog {cog_name}",
            COLORS["info"]
        )
        
        embed.add_field(
            name="Commands",
            value="\n".join([f"• `s!{cmd}`" for cmd in cog_commands]) or "No commands registered",
            inline=False
        )
        
        embed.add_field(
            name="Type",
            value=f"`{type(cog).__name__}`",
            inline=False
        )
        
        # Attempt to get attributes
        attrs = []
        for attr in dir(cog):
            if not attr.startswith('_') and not callable(getattr(cog, attr)):
                attrs.append(f"• {attr}")
        
        if attrs:
            embed.add_field(
                name="Attributes",
                value="\n".join(attrs[:10]) + (f"\n... and {len(attrs) - 10} more" if len(attrs) > 10 else ""),
                inline=False
            )
    else:
        # List all cogs
        embed = create_embed(
            "🔍 All Cogs",
            f"Debug information for all loaded cogs",
            COLORS["info"]
        )
        
        for cog_name, cog in bot.cogs.items():
            cog_commands = [cmd.name for cmd in bot.commands if cmd.cog_name == cog_name]
            embed.add_field(
                name=f"Cog: {cog_name}",
                value=f"**Commands:** {len(cog_commands)}\n**Type:** `{type(cog).__name__}`",
                inline=False
            )
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    asyncio.run(main()) 