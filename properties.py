# properties.py

import bpy
from bpy.props import FloatProperty, IntProperty, BoolProperty, PointerProperty, CollectionProperty, StringProperty

class LODIFY_props_list(bpy.types.PropertyGroup):
    ui_idx : IntProperty(description='UI List Index')
    ui_lod : PointerProperty(type=bpy.types.Collection, description='Level of Detail collection')
    ui_dsp : BoolProperty(default=False, description="Set this collection as active LOD in the viewport only")
    ui_rdv : BoolProperty(default=False, description="Set this collection as active LOD in the rendered view only")
    ui_rdf : BoolProperty(default=False, description="Set this collection as active LOD in the final render only")

class LODIFY_props_scn(bpy.types.PropertyGroup):
    lod_list : CollectionProperty(type=LODIFY_props_list)
    lod_list_index : IntProperty()
    lod_enabled : BoolProperty(default=False, description='Enable the LOD system for collections.')
    p_rdf_switch : BoolProperty(default=True, description='Automatically change the LOD on final render')
    p_rdv_switch : BoolProperty(default=True, description='Automatically change the LOD on rendered view')
    progress : FloatProperty(default=0.0, min=0.0, max=100.0, subtype='PERCENTAGE')
    small_object_threshold : FloatProperty(
        name="Small Object Threshold (m)",
        description="Objects smaller than this size (in meters) will be removed from higher LODs. Set to 0 to keep all objects.",
        default=0.1,
        min=0.0,
        max=10.0,
        precision=3,
        unit='LENGTH'
    )
    # decimate_angle_increment : FloatProperty(
    #     name="Decimate Angle Increments (°)",
    #     description="Objects smaller than this size (in meters) will be removed from higher LODs. Set to 0 to keep all objects.",
    #     default=0.1,
    #     min=0.0,
    #     max=10.0,
    #     precision=3,
    #     unit='LENGTH'
    # )
    decimate_angle_increment : IntProperty(
        name="Decimate Angle Increments (°)",
        description="By how much angle increment each subsequent LOD should be set to for the Planar Angle Limit of the Decimate Modifier.",
        default=15,
        min=0,
        max=90,
        step=5,
        # unit='ROTATION'
    )
    texture_path: StringProperty(
        name="Texture Path",
        description="Path to the folder containing textures",
        default="",
        subtype='DIR_PATH'
    )

classes = (
    LODIFY_props_list,
    LODIFY_props_scn,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            print(f"Class {cls.__name__} is already registered")

    bpy.types.Scene.lod = PointerProperty(type=LODIFY_props_scn)

def unregister():
    if hasattr(bpy.types.Scene, "lod"):
        del bpy.types.Scene.lod
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            print(f"Class {cls.__name__} is not registered")

if __name__ == "__main__":
    register()