# ui.py

import bpy

class LODIFY_UL_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        
        sub = row.row(align=True)
        sub.scale_x = 1.75
        sub.prop(item, "ui_lod", text='')

        sub = row.row(align=True)
        sub.scale_x = 1.1
        sub.enabled = bool(item.ui_lod)
        sub.prop(item, "ui_dsp", text='', icon='RESTRICT_VIEW_OFF' if item.ui_dsp else 'RESTRICT_VIEW_ON')

        if context.scene.lod.p_rdv_switch:
            sub.prop(item, 'ui_rdv', text='', icon='SHADING_RENDERED')
        if context.scene.lod.p_rdf_switch:
            sub.prop(item, "ui_rdf", text='', icon='RESTRICT_RENDER_OFF' if item.ui_rdf else 'RESTRICT_RENDER_ON')

class LODIFY_PT_collectionList(bpy.types.Panel):
    bl_label = "Level of Detail Collections"
    bl_idname = "LODIFY_PT_collectionList"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        scn = context.scene
        layout.prop(scn.lod, "lod_enabled", text="")

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        main = layout.column()
        main.enabled = scn.lod.lod_enabled

        row = main.row()
        col1 = row.column()
        col2 = row.column()

        template = col1.column()
        template.template_list("LODIFY_UL_items", "", scn.lod, "lod_list", scn.lod, "lod_list_index", rows=2)

        col2.separator(factor=1.0)
        add = col2.column(align=True)
        add.operator("lodify.list_action", icon='ADD', text="").action = 'ADD'
        rem = col2.column(align=True)
        rem.enabled = bool(len(scn.lod.lod_list))
        rem.operator("lodify.list_action", icon='REMOVE', text="").action = 'REMOVE'

        main.separator()
        main.prop(scn.lod, "small_object_threshold")
        
        main.separator()
        main.prop(scn.lod, "decimate_angle_increment")
        
        
        main.separator()
        main.operator("lodify.generate_lod_decimate", text="Generate LODs (Decimate)")
        
        main.separator()
        main.label(text="Material Conversion:")
        main.prop(scn.lod, "texture_path", text="Texture Path")
        row = main.row()
        row.operator("lodify.convert_msfs_to_blender", text="MSFS to Blender")
        row.operator("lodify.convert_blender_to_msfs", text="Convert All to MSFS")

        main.separator()
        main.label(text="Texture Baking:")
        main.operator("lodify.bake_to_vertex_colors", text="Bake Textures to Vertex Colors")

        # Add buttons to apply modifiers for each LOD
        main.separator()
        main.label(text="Apply Modifiers (All Collection Objects):")
        for i, item in enumerate(scn.lod.lod_list):
            row = main.row()
            row.operator("lodify.apply_lod_modifiers", text=f"Apply LOD{i:02d} Modifiers").lod_index = i
        
        # Progress bar
        if scn.lod.progress > 0:
            main.prop(scn.lod, "progress", text="Progress")

classes = (
    LODIFY_UL_items,
    LODIFY_PT_collectionList,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.lod.texture_path = bpy.props.StringProperty(
        name="Texture Path",
        description="Path to the folder containing textures",
        default="",
        subtype='DIR_PATH'
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.lod.texture_path

if __name__ == "__main__":
    register()