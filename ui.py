# ui.py

import bpy
from bpy.types import Panel, UIList

class LODIFY_UL_items(bpy.types.UIList):
    """UI List for LOD collections with improved visual design."""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # LOD collection selector with larger scale
            sub = row.row(align=True)
            sub.scale_x = 2.0
            sub.prop(item, "ui_lod", text='', emboss=True)

            # Viewport display toggle
            sub = row.row(align=True)
            sub.scale_x = 0.8
            sub.enabled = bool(item.ui_lod)
            icon = 'HIDE_OFF' if item.ui_dsp else 'HIDE_ON'
            sub.prop(item, "ui_dsp", text='', icon=icon, emboss=False)

            # Rendered view toggle (if enabled)
            if context.scene.lod.p_rdv_switch:
                sub.prop(item, 'ui_rdv', text='', icon='SHADING_RENDERED', emboss=False)
                
            # Render toggle (if enabled)
            if context.scene.lod.p_rdf_switch:
                icon = 'RESTRICT_RENDER_OFF' if item.ui_rdf else 'RESTRICT_RENDER_ON'
                sub.prop(item, "ui_rdf", text='', icon=icon, emboss=False)
                
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=f"LOD{index:02d}", icon='OUTLINER_COLLECTION')


class LODIFY_PT_main_panel(bpy.types.Panel):
    """Main LOD system panel with modern design."""
    bl_label = "MSFS LOD Maker"
    bl_idname = "LODIFY_PT_main_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        scn = context.scene
        layout.prop(scn.lod, "lod_enabled", text="")

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        lod_props = scn.lod

        # Main column with proper enabled state
        main = layout.column()
        main.enabled = lod_props.lod_enabled

        if not lod_props.lod_enabled:
            box = main.box()
            box.label(text="Enable LOD system to access all features", icon='INFO')
            return

        # Info message when LOD system is enabled
        box = main.box()
        col = box.column()
        col.label(text="LOD system is enabled and ready", icon='CHECKMARK')


class LODIFY_PT_generation_settings(bpy.types.Panel):
    """LOD generation settings panel."""
    bl_label = "Generation Settings"
    bl_idname = "LODIFY_PT_generation_settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "LODIFY_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        lod_props = scn.lod

        layout.enabled = lod_props.lod_enabled

        # Generation Method
        box = layout.box()
        col = box.column()
        col.label(text="LOD Generation Method", icon='MODIFIER')
        col.prop(lod_props, "lod_generation_method", text="")
        
        # Basic Settings
        col.separator()
        col.label(text="Basic Settings", icon='SETTINGS')
        
        row = col.row(align=True)
        row.prop(lod_props, "small_object_threshold", text="Small Object Threshold")
        
        row = col.row(align=True)
        row.prop(lod_props, "decimate_angle_increment", text="Decimate Angle")

        # Advanced Settings Toggle
        col.separator()
        col.prop(lod_props, "show_advanced_settings", icon='TRIA_DOWN' if lod_props.show_advanced_settings else 'TRIA_RIGHT')
        
        if lod_props.show_advanced_settings:
            box_adv = col.box()
            adv_col = box_adv.column()
            adv_col.label(text="Advanced Settings", icon='PREFERENCES')
            adv_col.prop(lod_props, "vertex_color_mode", text="Vertex Colors")


class LODIFY_PT_msfs_optimization(bpy.types.Panel):
    """MSFS optimization settings panel."""
    bl_label = "MSFS Optimization"
    bl_idname = "LODIFY_PT_msfs_optimization"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "LODIFY_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        lod_props = scn.lod

        layout.enabled = lod_props.lod_enabled

        # LOD Value Calculation
        box = layout.box()
        col = box.column()
        col.label(text="LOD Value Calculation", icon='DRIVER_DISTANCE')
        
        col.prop(lod_props, "use_automatic_lod_calculation", text="Automatic Calculation")
        
        if not lod_props.use_automatic_lod_calculation:
            col.prop(lod_props, "manual_lod_values", text="Manual Values")
        
        # Action Buttons
        col.separator()
        row = col.row(align=True)
        row.scale_y = 1.2
        
        # Set Default button with enhanced styling
        default_op = row.operator("lodify.set_default_lod_values", text="Set Default (4,3,2,1)", icon='PRESET')
        
        # Calculate button
        calc_op = row.operator("lodify.calculate_msfs_lod_values", text="Calculate & Apply", icon='AUTO')


class LODIFY_PT_generation_actions(bpy.types.Panel):
    """LOD generation action buttons panel."""
    bl_label = "Generate LODs"
    bl_idname = "LODIFY_PT_generation_actions"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "LODIFY_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        lod_props = scn.lod

        layout.enabled = lod_props.lod_enabled

        # Main Generation Button
        box = layout.box()
        col = box.column()
        
        # Primary action button
        row = col.row()
        row.scale_y = 1.5
        
        # Set button text based on generation method
        if lod_props.lod_generation_method == 'MIXED':
            button_text = "Generate LODs (Mixed Method)"
        elif lod_props.lod_generation_method == 'DECIMATE_ONLY':
            button_text = "Generate LODs (Decimate Only)"
        else:
            button_text = "Generate LODs (Shrinkwrap Only)"
            
        row.operator("lodify.generate_lod_decimate", text=button_text, icon='MOD_DECIM')

        # Progress bar
        if lod_props.progress > 0:
            col.separator(factor=0.5)
            col.prop(lod_props, "progress", text="Progress", slider=True)


class LODIFY_PT_modifier_tools(bpy.types.Panel):
    """Modifier application tools panel."""
    bl_label = "Modifier Tools"
    bl_idname = "LODIFY_PT_modifier_tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "LODIFY_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        lod_props = scn.lod

        layout.enabled = lod_props.lod_enabled

        # Modifier Application Section
        box = layout.box()
        col = box.column()
        col.label(text="Apply Modifiers (All Collection Objects)", icon='MODIFIER')
        
        # Create buttons for each LOD
        for i, item in enumerate(lod_props.lod_list):
            if item.ui_lod:  # Only show if collection is assigned
                row = col.row()
                apply_op = row.operator("lodify.apply_lod_modifiers", text=f"Apply {item.ui_lod.name} Modifiers")
                apply_op.lod_index = i


# Class registration
classes = (
    LODIFY_UL_items,
    LODIFY_PT_main_panel,
    LODIFY_PT_generation_settings,
    LODIFY_PT_msfs_optimization,
    LODIFY_PT_generation_actions,
    LODIFY_PT_modifier_tools,
)

def register():
    """Register UI classes with error handling."""
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            print(f"Warning: UI class {cls.__name__} registration issue: {e}")

def unregister():
    """Unregister UI classes with error handling."""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            print(f"Warning: UI class {cls.__name__} unregistration issue: {e}")

if __name__ == "__main__":
    register()