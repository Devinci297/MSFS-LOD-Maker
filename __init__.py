# __init__.py
import bpy
import logging

if "bpy" in locals():
    import importlib
    if "operators" in locals():
        importlib.reload(operators)
    if "ui" in locals():
        importlib.reload(ui)
    if "properties" in locals():
        importlib.reload(properties)


from . import operators
from . import ui
from . import properties

bl_info = {
    "name": "MSFS LOD Maker",
    "description": "Microsoft Flight Simulator LOD system for collections in Blender 3.6+, with intelligent LOD generation and automatic MSFS optimization",
    "author": "Devinci (inspired by DB3D's Lodify addon)",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),  # Updated to support Blender 3.6+ (including 4.x)
    "location": "Properties > Scene > Level of Detail Collections",
    "warning": "",
    "doc_url": "https://github.com/Devinci297/MSFS-LOD-Maker/blob/main/README.md",
    "tracker_url": "https://github.com/Devinci297/MSFS-LOD-Maker/issues",
    "category": "Scene"
}


def setup_logging():
    """Setup logging for the addon with improved error handling."""
    try:
        logging.basicConfig(
            filename='lodify_addon.log', 
            level=logging.DEBUG, 
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filemode='w'  # Overwrite log file each time
        )
        logging.info("MSFS LOD Maker addon logging initialized")
    except Exception as e:
        print(f"Warning: Could not setup logging: {str(e)}")


def register():
    """Register the addon with improved error handling."""
    setup_logging()
    try:
        properties.register()
        operators.register()
        ui.register()
        print("MSFS LOD Maker addon registered successfully")
    except Exception as e:
        print(f"Error during MSFS LOD Maker registration: {str(e)}")
        # Attempt cleanup on partial registration
        try:
            unregister()
        except:
            pass
        raise


def unregister():
    """Unregister the addon with improved error handling."""
    try:
        ui.unregister()
        operators.unregister()
        properties.unregister()
        print("MSFS LOD Maker addon unregistered successfully")
    except Exception as e:
        print(f"Error during MSFS LOD Maker unregistration: {str(e)}")


if __name__ == "__main__":
    register()