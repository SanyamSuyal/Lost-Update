import os
import shutil
import sys
import importlib
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_permissions.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fix_permissions")

def ensure_cogs_directory():
    """Make sure the cogs directory exists and is accessible"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if cogs directory exists
    cogs_dir = os.path.join(current_dir, 'cogs')
    if not os.path.exists(cogs_dir):
        logger.info(f"Creating cogs directory at: {cogs_dir}")
        os.makedirs(cogs_dir, exist_ok=True)
        
    # Make sure it's a directory
    if not os.path.isdir(cogs_dir):
        logger.error(f"Cogs path exists but is not a directory: {cogs_dir}")
        # Rename the file and create directory
        backup_path = cogs_dir + '.bak'
        logger.info(f"Renaming to {backup_path} and creating directory")
        os.rename(cogs_dir, backup_path)
        os.makedirs(cogs_dir, exist_ok=True)
    
    return cogs_dir

def fix_permissions(directory):
    """Fix permissions on directory and contents"""
    logger.info(f"Fixing permissions for: {directory}")
    
    # Make directory executable and writable
    try:
        os.chmod(directory, 0o755)  # rwxr-xr-x
        logger.info(f"Changed directory permissions: {directory}")
    except Exception as e:
        logger.error(f"Failed to change directory permissions: {e}")
    
    # Fix file permissions
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                os.chmod(item_path, 0o644)  # rw-r--r--
                logger.info(f"Changed file permissions: {item_path}")
            elif os.path.isdir(item_path):
                fix_permissions(item_path)  # Recursive for subdirectories
    except Exception as e:
        logger.error(f"Error listing directory: {e}")

def ensure_python_files(directory):
    """Ensure Python files have a .py extension and check for __init__.py"""
    logger.info(f"Checking Python files in: {directory}")
    
    # Check for __init__.py
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        logger.info(f"Creating __init__.py in {directory}")
        with open(init_file, 'w') as f:
            f.write("# This file makes the directory a Python package\n")
    
    # Check file extensions
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path) and not item.startswith('__'):
            # Check if it looks like Python but doesn't have .py extension
            if not item.endswith('.py'):
                with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read(500)  # Read first 500 chars
                        if 'import' in content and ('def' in content or 'class' in content):
                            # Looks like Python, rename it
                            new_path = item_path + '.py'
                            logger.info(f"Renaming {item_path} to {new_path}")
                            os.rename(item_path, new_path)
                    except Exception as e:
                        logger.error(f"Error reading file {item_path}: {e}")

def verify_cog_files(directory):
    """Verify that cog files have proper structure"""
    logger.info(f"Verifying cog files in: {directory}")
    
    for item in os.listdir(directory):
        if item.endswith('.py') and not item.startswith('__'):
            item_path = os.path.join(directory, item)
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for basic requirements
                has_cog_class = 'commands.Cog' in content
                has_setup_func = 'async def setup' in content
                
                if not has_cog_class:
                    logger.warning(f"File {item} missing Cog class definition")
                
                if not has_setup_func:
                    logger.warning(f"File {item} missing setup function")
                    # Add setup function if missing
                    if has_cog_class:
                        cog_name = None
                        for line in content.split('\n'):
                            if 'class' in line and '(commands.Cog)' in line:
                                cog_name = line.split('class')[1].split('(')[0].strip()
                                break
                        
                        if cog_name:
                            with open(item_path, 'a') as f:
                                f.write(f"\n\nasync def setup(bot):\n    await bot.add_cog({cog_name}(bot))\n")
                            logger.info(f"Added setup function to {item}")
            except Exception as e:
                logger.error(f"Error processing file {item_path}: {e}")

def create_sample_cog(directory):
    """Create a sample cog file if no cogs exist"""
    cog_files = [f for f in os.listdir(directory) if f.endswith('.py') and not f.startswith('__')]
    
    if not cog_files:
        logger.info("No cog files found. Creating a sample cog.")
        sample_cog_path = os.path.join(directory, 'example_commands.py')
        
        sample_cog = """import discord
from discord.ext import commands
import logging

logger = logging.getLogger("shop_bot.example_commands")

class ExampleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "shop_database.db"
        
    @commands.command(name="hello")
    async def hello(self, ctx):
        """A simple hello command"""
        await ctx.send("Hello! I'm working properly now!")
        
    @commands.command(name="echo")
    async def echo(self, ctx, *, message):
        """Repeats what you say"""
        await ctx.send(f"You said: {message}")

async def setup(bot):
    await bot.add_cog(ExampleCommands(bot))
"""
        
        with open(sample_cog_path, 'w') as f:
            f.write(sample_cog)
        logger.info(f"Created sample cog at {sample_cog_path}")

def copy_existing_cogs():
    """Copy existing cogs from files we know exist"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cogs_dir = os.path.join(current_dir, 'cogs')
    
    # Define cog content from the provided info
    user_commands_path = os.path.join(cogs_dir, 'user_commands.py')
    admin_commands_path = os.path.join(cogs_dir, 'admin_commands.py')
    
    if not os.path.exists(user_commands_path):
        logger.info("Copying user_commands.py from provided data")
        # Check if the user_commands.py is accessible from the additional_data
        with open(user_commands_path, 'w') as f:
            f.write("""import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime
import logging
import os
import random
import string

logger = logging.getLogger("shop_bot.user_commands")

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "shop_database.db"
        self.ltc_address = os.getenv('LTC_ADDRESS', 'DEFAULT_LTC_ADDRESS')
        if hasattr(bot, 'LTC_ADDRESS'):
            self.ltc_address = bot.LTC_ADDRESS
        self.colors = bot.COLORS if hasattr(bot, 'COLORS') else {
            "success": 0x43B581,
            "error": 0xF04747,
            "info": 0x7289DA,
            "warning": 0xFAA61A,
            "shop": 0x36393F,
            "primary": 0x5865F2
        }
        self.create_embed = bot.create_embed if hasattr(bot, 'create_embed') else self.default_embed

    def default_embed(self, title, description, color=0x5865F2, timestamp=True):
        """Fallback embed creation if bot.create_embed is not available"""
        embed = discord.Embed(title=title, description=description, color=color)
        if timestamp:
            embed.timestamp = datetime.now()
        return embed

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.command.cog_name == self.__class__.__name__:
            if await self.is_banned(ctx.author.id):
                await ctx.send(
                    embed=self.create_embed(
                        "🚫 Access Denied",
                        "You are banned from using this shop.",
                        self.colors["error"]
                    )
                )
                raise commands.CheckFailure("User is banned")

    async def is_banned(self, user_id):
        """Check if a user is banned from using the shop"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,)
            ) as cursor:
                return await cursor.fetchone() is not None

    @commands.command(name="shop")
    async def shop(self, ctx):
        """View all available items with prices, stock, and descriptions"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM items WHERE stock > 0") as cursor:
                items = await cursor.fetchall()
        
        if not items:
            await ctx.send(
                embed=self.create_embed(
                    "🛍️ Shop",
                    "The shop is currently empty. Check back later for new products!",
                    self.colors["shop"]
                )
            )
            return
        
        embed = self.create_embed(
            "🛍️ Shop Items",
            "Browse our collection of premium products:",
            self.colors["shop"]
        )
        
        # Add a thumbnail image
        embed.set_thumbnail(url="https://i.imgur.com/xBuZqM1.png")
        
        for item in items:
            embed.add_field(
                name=f"🔹 {item['name']} - ${item['price']:.2f}",
                value=f"**Stock:** {item['stock']} remaining\\n**Description:** {item['description']}",
                inline=False
            )
        
        embed.set_footer(text="To purchase an item, use s!buy <item name>")
        await ctx.send(embed=embed)

    @commands.command(name="userhelp")
    async def user_help(self, ctx):
        """Shop Bot help command"""
        embed = self.create_embed(
            "Shop Bot Help",
            "Here are all the commands you can use:",
            self.colors["info"]
        )
        
        # Add a nice thumbnail
        embed.set_thumbnail(url="https://i.imgur.com/q5nyBD4.png")
        
        # User commands
        embed.add_field(
            name="💰 Shop Commands",
            value=(
                "`s!shop` - Browse available items\\n"
                "`s!buy <item>` - Purchase an item\\n"
                "`s!confirm <key>` - Confirm your payment\\n"
                "`s!price <item>` - Check item price\\n"
                "`s!stock <item>` - Check item stock\\n"
                "`s!orders` - View your orders\\n"
                "`s!cancelorder <order_id>` - Cancel pending order\\n"
                "`s!refund <order_id>` - Request a refund"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
""")

    if not os.path.exists(admin_commands_path):
        logger.info("Creating a minimal admin_commands.py")
        with open(admin_commands_path, 'w') as f:
            f.write("""import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime
import logging
import os

logger = logging.getLogger("shop_bot.admin_commands")

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "shop_database.db"
        self.colors = bot.COLORS if hasattr(bot, 'COLORS') else {
            "success": 0x43B581,
            "error": 0xF04747,
            "info": 0x7289DA,
            "warning": 0xFAA61A,
            "shop": 0x36393F,
            "admin": 0xE91E63,
            "primary": 0x5865F2
        }
        self.create_embed = bot.create_embed if hasattr(bot, 'create_embed') else self.default_embed
        
    def default_embed(self, title, description, color=0x5865F2, timestamp=True):
        """Fallback embed creation if bot.create_embed is not available"""
        embed = discord.Embed(title=title, description=description, color=color)
        if timestamp:
            embed.timestamp = datetime.now()
        return embed
        
    def safe_get_field(self, row, field, default=None):
        """Safely get a field from a sqlite3.Row object"""
        try:
            if field in row.keys():
                return row[field]
            return default
        except:
            return default
        
    def cog_check(self, ctx):
        """Check if the user has admin privileges"""
        if not ctx.guild:
            return False
        admin_role_id = int(os.getenv('ADMIN_ROLE_ID', 0))
        admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id)
        if admin_role and admin_role in ctx.author.roles:
            return True
        return ctx.author.guild_permissions.administrator

    @commands.command(name="vieworders")
    async def view_orders(self, ctx, limit: int = 10):
        """View recent orders as an admin"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT o.id, o.user_id, i.name, o.quantity, o.total_price, o.status, o.created_at
                FROM orders o
                JOIN items i ON o.item_id = i.id
                ORDER BY o.created_at DESC
                LIMIT ?
                """,
                (limit,)
            ) as cursor:
                orders = await cursor.fetchall()
        
        if not orders:
            await ctx.send(
                embed=self.create_embed(
                    "📋 Orders",
                    "No orders found in the database.",
                    self.colors["info"]
                )
            )
            return
        
        embed = self.create_embed(
            "📋 Orders",
            f"Showing last {len(orders)} orders:",
            self.colors["admin"]
        )
        
        for order in orders:
            status_emoji = {
                "pending": "⏳",
                "paid": "💰",
                "delivered": "✅",
                "cancelled": "❌"
            }.get(order['status'].lower(), "❓")
            
            # Try to get user name
            user = self.bot.get_user(order['user_id'])
            user_display = user.mention if user else f"ID: {order['user_id']}"
            
            embed.add_field(
                name=f"Order #{order['id']} - {status_emoji} {order['status'].capitalize()}",
                value=f"**User:** {user_display}\\n"
                      f"**Item:** {order['name']}\\n"
                      f"**Amount:** ${order['total_price']:.2f}\\n"
                      f"**Date:** {order['created_at']}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
""")

def main():
    logger.info("Starting permissions and file check...")
    
    # Ensure cogs directory exists
    cogs_dir = ensure_cogs_directory()
    
    # Create __init__.py 
    ensure_python_files(cogs_dir)
    
    # Fix permissions
    fix_permissions(cogs_dir)
    
    # Copy existing cogs
    copy_existing_cogs()
    
    # Verify cog files
    verify_cog_files(cogs_dir)
    
    # Create a sample cog if none exist
    create_sample_cog(cogs_dir)
    
    logger.info("Permissions and file check completed")
    
    # Print next steps
    print("\nNext steps:")
    print("1. Restart your bot with 'python main.py'")
    print("2. Use the s!status command to verify cogs are loaded")
    print("3. Try s!shop or other commands to verify functionality")

if __name__ == "__main__":
    main() 