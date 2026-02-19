# properties.py

import bpy
from bpy.props import FloatProperty, IntProperty, BoolProperty, PointerProperty, CollectionProperty, StringProperty, EnumProperty

class LODIFY_props_list(bpy.types.PropertyGroup):
    """Property group for individual LOD collection items."""
    ui_idx: IntProperty(description='UI List Index')
    ui_lod: PointerProperty(type=bpy.types.Collection, description='Level of Detail collection')
    ui_dsp: BoolProperty(default=False, description="Set this collection as active LOD in the viewport only")
    ui_rdv: BoolProperty(default=False, description="Set this collection as active LOD in the rendered view only")
    ui_rdf: BoolProperty(default=False, description="Set this collection as active LOD in the final render only")

class LODIFY_props_scn(bpy.types.PropertyGroup):
    """Main property group for LOD system settings."""
    lod_list: CollectionProperty(type=LODIFY_props_list)
    lod_list_index: IntProperty()
    lod_enabled: BoolProperty(
        default=False, 
        description='Enable the LOD system for collections'
    )
    p_rdf_switch: BoolProperty(
        default=True, 
        description='Automatically change the LOD on final render'
    )
    p_rdv_switch: BoolProperty(
        default=True, 
        description='Automatically change the LOD on rendered view'
    )
    progress: FloatProperty(
        default=0.0, 
        min=0.0, 
        max=100.0, 
        subtype='PERCENTAGE'
    )
    
    # LOD Generation Settings
    small_object_threshold: FloatProperty(
        name="Small Object Threshold",
        description="Objects smaller than this size (in meters) will be removed from higher LODs. Set to 0 to keep all objects",
        default=0.1,
        min=0.0,
        max=10.0,
        precision=3,
        unit='LENGTH'
    )
    
    decimate_angle_increment: IntProperty(
        name="Decimate Angle Increments",
        description="By how much angle increment each subsequent LOD should be set to for the Planar Angle Limit of the Decimate Modifier",
        default=15,
        min=0,
        max=90,
        step=5
    )
    
    # MSFS LOD Optimization Settings
    use_automatic_lod_calculation: BoolProperty(
        name="Use Automatic LOD Calculation",
        description="Automatically calculate optimal LOD values based on object size and MSFS 2024 standards",
        default=True
    )
    
    manual_lod_values: StringProperty(
        name="Manual LOD Values",
        description="Comma-separated LOD values (e.g., '12,3,2,1') for manual override. Only used when automatic calculation is disabled",
        default="4,3,2,1"
    )

    msfs2024_cube_multiplier: FloatProperty(
        name="Invisible Cube Multiplier",
        description="Multiplier for the size of the invisible cube relative to the object bounding box (MSFS 2024 workaround)",
        default=20.0,
        min=1.0,
        max=1000.0,
        precision=1
    )
    
    lod_generation_method: EnumProperty(
        name="LOD Generation Method",
        description="Choose the method for generating LODs",
        items=[
            ('MIXED', "Mixed (All Decimate)", "Use decimate method for all LODs (recommended)"),
            ('DECIMATE_ONLY', "Decimate Only", "Use decimate method for all LODs"),
            ('SHRINKWRAP_ONLY', "Shrinkwrap Only", "Use shrinkwrap method for all LODs (experimental)")
        ],
        default='MIXED'
    )
    
    # Advanced Settings
    show_advanced_settings: BoolProperty(
        name="Show Advanced Settings",
        description="Show advanced LOD generation and optimization settings",
        default=False
    )
    
    vertex_color_mode: EnumProperty(
        name="Vertex Color Mode",
        description="How to handle vertex colors in LOD generation",
        items=[
            ('AUTO', "Automatic", "LOD00-01: white, LOD02: baked from albedo, LOD03: inherited from LOD02"),
            ('WHITE_ONLY', "White Only", "Apply white vertex colors to all LODs"),
            ('BAKE_ALL', "Bake All", "LOD00-01: white, LOD02: baked from albedo, LOD03: inherited from LOD02"),
            ('TRANSFER_ALL', "Transfer All", "LOD00-01: white colors, LOD02-03: gray colors")
        ],
        default='AUTO'
    )
    
    # LOD Selection Settings
    generate_lod01: BoolProperty(
        name="Generate LOD01",
        description="Generate LOD01 level",
        default=True
    )
    
    generate_lod02: BoolProperty(
        name="Generate LOD02", 
        description="Generate LOD02 level",
        default=True
    )
    
    generate_lod03: BoolProperty(
        name="Generate LOD03",
        description="Generate LOD03 level", 
        default=True
    )

classes = (
    LODIFY_props_list,
    LODIFY_props_scn,
)

def register():
    """Register property classes with improved error handling."""
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            print(f"Warning: Class {cls.__name__} registration issue: {e}")

    # Register the main scene property
    bpy.types.Scene.lod = PointerProperty(type=LODIFY_props_scn)

def unregister():
    """Unregister property classes with improved error handling."""
    # Remove scene property first
    if hasattr(bpy.types.Scene, "lod"):
        del bpy.types.Scene.lod
        
    # Unregister classes in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            print(f"Warning: Class {cls.__name__} unregistration issue: {e}")

if __name__ == "__main__":
    register()