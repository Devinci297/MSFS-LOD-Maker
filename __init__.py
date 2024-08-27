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
    "description": "MSFS LOD system for collections in Blender 3.6 & above, with LOD generation",
    "author": "Devinci (inspired by DB3D's Lodify addon)",
    "version": (0, 1),
    "blender": (3, 60, 0),
    "location": "''Properties'' > ''Scene'' > ''Level of Detail Collections''",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "a",
    "category": "Scene"
}


def setup_logging():
    logging.basicConfig(filename='lodify_addon.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                       



def register():
    setup_logging()
    try:
        properties.register()
        operators.register()
        ui.register()
    except Exception as e:
        print(f"Error during registration: {str(e)}")
        # Optionally, you can add a cleanup here if partial registration occurred

def unregister():
    try:
        ui.unregister()
        operators.unregister()
        properties.unregister()
    except Exception as e:
        print(f"Error during unregistration: {str(e)}")

if __name__ == "__main__":
    register()