import asyncio
import os
import sys
import importlib.util
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cogs_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cogs_check")

async def check_cogs():
    """Check if cogs can be imported and loaded"""
    logger.info("Starting cogs check...")
    
    # Add the current directory to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Check if cogs directory exists
    cogs_dir = os.path.join(current_dir, 'cogs')
    if not os.path.exists(cogs_dir):
        logger.error(f"Cogs directory not found: {cogs_dir}")
        return
    
    logger.info(f"Cogs directory found: {cogs_dir}")
    
    # List cogs
    cog_files = [f for f in os.listdir(cogs_dir) if f.endswith('.py')]
    logger.info(f"Found {len(cog_files)} cog files: {cog_files}")
    
    # Try to load each cog manually
    for cog_file in cog_files:
        cog_name = cog_file[:-3]  # Remove .py extension
        cog_path = os.path.join(cogs_dir, cog_file)
        
        logger.info(f"Checking cog: {cog_name} at {cog_path}")
        
        # Try to import the module
        try:
            # Try importing using importlib
            spec = importlib.util.spec_from_file_location(f"cogs.{cog_name}", cog_path)
            if not spec:
                logger.error(f"Could not create spec for {cog_path}")
                continue
                
            module = importlib.util.module_from_spec(spec)
            if not module:
                logger.error(f"Could not create module from spec for {cog_path}")
                continue
                
            spec.loader.exec_module(module)
            logger.info(f"✅ Successfully imported {cog_name}")
            
            # Check for setup function
            if not hasattr(module, 'setup'):
                logger.error(f"❌ Missing setup function in {cog_name}")
            else:
                logger.info(f"✅ Found setup function in {cog_name}")
                
            # Check for Cog class
            has_cog_class = False
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name not in ['Cog', 'commands']:
                    logger.info(f"Potential cog class found: {attr_name}")
                    has_cog_class = True
            
            if not has_cog_class:
                logger.warning(f"⚠️ No potential Cog class found in {cog_name}")
                
        except Exception as e:
            logger.error(f"❌ Error importing {cog_name}: {e}")
            logger.error(traceback.format_exc())
    
    logger.info("Cogs check completed")

if __name__ == "__main__":
    asyncio.run(check_cogs()) 