# operators.py
#
# This file contains the operator classes for the Lodify Collections addon.
# These operators handle various functionalities such as:
# - Managing LOD lists
# - Generating LODs using decimation or shrinkwrap
# - Converting between MSFS and Blender materials
# - Baking textures to vertex colors

import bpy
from bpy.types import Operator
from bpy.props import IntProperty
import os
import bmesh
import logging
from mathutils import Vector

def find_base_collection():
    for scene in bpy.data.scenes:
        for collection in scene.collection.children:
            if collection.name.endswith("_LOD00"):
                return collection
    return None


class LODIFY_OT_list_actions(bpy.types.Operator):
    bl_idname = "lodify.list_action"
    bl_label = "List Actions"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=(
            ('ADD', "Add", ""),
            ('REMOVE', "Remove", ""),
        )
    )

    def execute(self, context):
        scn = context.scene
        idx = scn.lod.lod_list_index

        if self.action == 'ADD':
            item = scn.lod.lod_list.add()
            item.name = f"LOD{len(scn.lod.lod_list) - 1:02d}"
            scn.lod.lod_list_index = len(scn.lod.lod_list) - 1
        elif self.action == 'REMOVE':
            scn.lod.lod_list.remove(idx)
            scn.lod.lod_list_index = min(max(0, idx - 1), len(scn.lod.lod_list) - 1)

        return {'FINISHED'}

class LODIFY_OT_auto_setup(bpy.types.Operator):
    bl_idname = "lodify.auto_setup"
    bl_label = "Auto Setup LOD Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        base_collection = find_base_collection()
        
        if not base_collection:
            self.report({'ERROR'}, "Base LOD collection (ending with _LOD00) not found")
            return {'CANCELLED'}
        
        # Clear existing list
        scn.lod.lod_list.clear()
        
        base_name = base_collection.name[:-5]  # Remove "_LOD00" from the end
        
        for i in range(4):
            lod_name = f"{base_name}LOD{i:02d}"
            if lod_name in bpy.data.collections:
                item = scn.lod.lod_list.add()
                item.ui_lod = bpy.data.collections[lod_name]
                if i == 0:
                    item.ui_rdf = True
                    item.ui_rdv = True
                elif i == 3:
                    item.ui_dsp = True

        return {'FINISHED'}

class LODIFY_OT_generate_lod_decimate(bpy.types.Operator):
    bl_idname = "lodify.generate_lod_decimate"
    bl_label = "Generate LODs using Decimate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        base_collection = find_base_collection()
        
        if not base_collection:
            self.report({'ERROR'}, "Base LOD collection (ending with _LOD00) not found")
            return {'CANCELLED'}
        
        base_name = base_collection.name[:-5]  # Remove "_LOD00" from the end
        
        # Clear existing list
        scn.lod.lod_list.clear()
        
        total_objects = sum(1 for obj in base_collection.all_objects if obj.type == 'MESH' and not self.is_in_child_lod00(obj, base_collection)) * 3  # 3 LOD levels
        processed_objects = 0

        # Set color tag for base LOD
        base_collection.color_tag = 'COLOR_01'
        self.set_child_collection_colors(base_collection, 'COLOR_01')
        
        # Add base LOD to the list
        item = scn.lod.lod_list.add()
        item.ui_lod = base_collection
        item.ui_rdf = True
        item.ui_rdv = True

        for i in range(1, 4):  # Generate LOD01, LOD02, LOD03
            lod_name = f"{base_name}LOD{i:02d}"
            lod_collection = bpy.data.collections.get(lod_name)
            
            if not lod_collection:
                lod_collection = bpy.data.collections.new(lod_name)
                scn.collection.children.link(lod_collection)
            else:
                # Clear existing objects in the collection
                self.clear_collection(lod_collection)
            
            # Set color tag for LOD collection
            color_tag = f'COLOR_0{i+1}'
            lod_collection.color_tag = color_tag
            
            # Copy collection structure from base collection
            self.copy_collection_structure(base_collection, lod_collection, i, color_tag)
            
            # Add LOD to the list
            item = scn.lod.lod_list.add()
            item.ui_lod = lod_collection
            if i == 3:
                item.ui_dsp = True
            
            # Adjust angle for each LOD level
            angle = scn.lod.decimate_angle_increment * i
            
            self.process_objects(base_collection, lod_collection, i, angle, scn, context)
            
            processed_objects += total_objects // 3
            scn.lod.progress = (processed_objects / total_objects) * 100
            context.workspace.status_text_set(f"Generating LODs: {scn.lod.progress:.1f}%")
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        scn.lod.progress = 0
        context.workspace.status_text_set(None)
        self.report({'INFO'}, "LODs generated using Decimate modifier (Planar Dissolve)")
        return {'FINISHED'}

    def copy_collection_structure(self, source_collection, target_collection, lod_level, color_tag):
        for child in source_collection.children:
            new_child = bpy.data.collections.new(f"{child.name}_LOD{lod_level:02d}")
            target_collection.children.link(new_child)
            new_child.color_tag = color_tag
            self.copy_collection_structure(child, new_child, lod_level, color_tag)

    def process_objects(self, source_collection, target_collection, lod_level, angle, scn, context):
        for obj in source_collection.objects:
            if obj.type == 'MESH' and not self.is_in_child_lod00(obj, source_collection):
                # Check if the object is too small for higher LODs
                if scn.lod.small_object_threshold > 0 and self.is_object_too_small(obj, scn.lod.small_object_threshold):
                    continue

                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                target_collection.objects.link(new_obj)
                
                if lod_level in [2, 3]:  # For LOD02 and LOD03
                    # Convert MSFS materials to Blender materials
                    self.convert_materials(new_obj)

                    # Bake to vertex colors
                    self.bake_to_vertex_colors(new_obj)
                    # Remove all materials from the object after baking
                    new_obj.data.materials.clear()
                
                # Rename the object
                new_obj.name = f"{obj.name}_LOD{lod_level:02d}"
                
                # Add decimate modifier
                decimate = new_obj.modifiers.new(name="LOD_Decimate", type='DECIMATE')
                decimate.decimate_type = 'DISSOLVE'
                decimate.angle_limit = angle * (3.14159 / 180)  # Convert to radians
                decimate.use_dissolve_boundaries = False
                decimate.delimit = {'UV'}
                
            else:
                # For non-mesh objects (e.g., lights), just duplicate them
                new_obj = obj.copy()
                if obj.data:
                    new_obj.data = obj.data.copy()
                target_collection.objects.link(new_obj)
                new_obj.name = f"{obj.name}_LOD{lod_level:02d}"

        # Process child collections
        for child in source_collection.children:
            child_target = next((c for c in target_collection.children if c.name.startswith(child.name)), None)
            if child_target:
                self.process_objects(child, child_target, lod_level, angle, scn, context)
                
    def clear_collection(self, collection):
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(collection.children):
            self.clear_collection(child)
            bpy.data.collections.remove(child)

    def set_child_collection_colors(self, collection, color_tag):
        for child in collection.children:
            child.color_tag = color_tag
            self.set_child_collection_colors(child, color_tag)

    def is_in_child_lod00(self, obj, base_collection):
        for child in base_collection.children:
            if child.name.endswith("_LOD00") and obj.name in child.objects:
                return True
        return False

    def is_object_too_small(self, obj, threshold):
        largest_dimension = max(obj.dimensions)
        return largest_dimension < threshold

    def convert_materials(self, obj):
        for slot in obj.material_slots:
            if slot.material and hasattr(slot.material, 'msfs_material_type'):
                # Create a copy of the original material
                new_material = slot.material.copy()
                slot.material = new_material

                # Call the conversion operator
                bpy.ops.lodify.convert_msfs_to_blender(material_name=new_material.name)

        # Note: We're not removing materials here anymore

    def bake_to_vertex_colors(self, obj):
        # Ensure the object is selected and active
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Create a unique color attribute name
        base_name = f"{obj.name}_Color"
        color_attribute_name = base_name
        counter = 1
        while color_attribute_name in obj.data.color_attributes:
            color_attribute_name = f"{base_name}_{counter}"
            counter += 1

        # Create a color attribute if it doesn't exist
        if color_attribute_name not in obj.data.color_attributes:
            color_attribute = obj.data.color_attributes.new(
                name=color_attribute_name,
                type='FLOAT_COLOR',
                domain='POINT'
            )
            
            # Initialize the color attribute with white
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            color_layer = bm.loops.layers.color.get(color_attribute_name)
            
            if color_layer:
                for face in bm.faces:
                    for loop in face.loops:
                        loop[color_layer] = (1, 1, 1, 1)
                
                bm.to_mesh(mesh)
                mesh.update()
            
            bm.free()

        # Set the color attribute as active
        if color_attribute_name in obj.data.color_attributes:
            obj.data.color_attributes.active_color = obj.data.color_attributes[color_attribute_name]
        else:
            self.report({'WARNING'}, f"Failed to create color attribute for {obj.name}")
            return

        # Set up render settings
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True
        bpy.context.scene.render.bake.target = 'VERTEX_COLORS'

        # Ensure all texture images are loaded
        for mat_slot in obj.material_slots:
            material = mat_slot.material
            if material and material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        node.image.reload()

        # Bake vertex colors
        bpy.ops.object.bake(type='DIFFUSE')

        # Set the active color attribute for viewport display
        if hasattr(obj.data.attributes, 'active_color'):
            obj.data.attributes.active_color = obj.data.attributes[color_attribute_name]
            
class LODIFY_OT_generate_lod_shrinkwrap(bpy.types.Operator):
    bl_idname = "lodify.generate_lod_shrinkwrap"
    bl_label = "Generate LODs using Shrinkwrap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        base_collection = find_base_collection()
        
        if not base_collection:
            self.report({'ERROR'}, "Base LOD collection (ending with _LOD00) not found")
            return {'CANCELLED'}
        
        base_name = base_collection.name[:-5]  # Remove "_LOD00" from the end
        
        for i in range(1, 4):  # Generate LOD01, LOD02, LOD03
            lod_name = f"{base_name.rstrip('_')}_LOOOOD{i:02d}"
            lod_collection = bpy.data.collections.get(lod_name)
            
            if not lod_collection:
                lod_collection = bpy.data.collections.new(lod_name)
                scn.collection.children.link(lod_collection)
            
            for obj in base_collection.objects:
                new_obj = obj.copy()
                if obj.data:
                    new_obj.data = obj.data.copy()
                lod_collection.objects.link(new_obj)
                
                if new_obj.type == 'MESH':
                    # Create a low-poly proxy
                    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=new_obj.location)
                    proxy = context.active_object
                    proxy.name = f"{new_obj.name}_Proxy"
                    proxy.scale = new_obj.dimensions
                    
                    # Add shrinkwrap modifier
                    shrinkwrap = proxy.modifiers.new(name="Shrinkwrap", type='SHRINKWRAP')
                    shrinkwrap.target = new_obj
                    shrinkwrap.wrap_method = 'PROJECT'
                    shrinkwrap.use_project_z = True
                    
                    # Apply modifier
                    context.view_layer.objects.active = proxy
                    bpy.ops.object.modifier_apply(modifier="Shrinkwrap")
                    
                    # Replace the duplicated object with the proxy
                    lod_collection.objects.unlink(new_obj)
                    lod_collection.objects.link(proxy)
                    bpy.data.objects.remove(new_obj)
                    
                    # Rename the proxy to match the original object name
                    proxy.name = obj.name
        
        self.report({'INFO'}, "LODs generated using Shrinkwrap method")
        return {'FINISHED'}

class LODIFY_OT_apply_lod_modifiers(bpy.types.Operator):
    bl_idname = "lodify.apply_lod_modifiers"
    bl_label = "Apply LOD Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    lod_index: bpy.props.IntProperty()

    def execute(self, context):
        scn = context.scene
        if self.lod_index < 0 or self.lod_index >= len(scn.lod.lod_list):
            self.report({'ERROR'}, "Invalid LOD index")
            return {'CANCELLED'}

        lod_collection = scn.lod.lod_list[self.lod_index].ui_lod
        if not lod_collection:
            self.report({'ERROR'}, "LOD collection not found")
            return {'CANCELLED'}

        self.apply_modifiers_recursive(context, lod_collection)

        self.report({'INFO'}, f"Applied all modifiers for LOD {self.lod_index}")
        return {'FINISHED'}

    def apply_modifiers_recursive(self, context, collection):
        for obj in collection.objects:
            if obj.type == 'MESH':
                context.view_layer.objects.active = obj
                for modifier in obj.modifiers:
                    try:
                        bpy.ops.object.modifier_apply({"object": obj, "selected_objects": [obj]}, modifier=modifier.name)
                    except RuntimeError:
                        self.report({'WARNING'}, f"Could not apply modifier {modifier.name} to object {obj.name}")

        for child_collection in collection.children:
            self.apply_modifiers_recursive(context, child_collection)
            
class LODIFY_OT_convert_msfs_to_blender(bpy.types.Operator):
    bl_idname = "lodify.convert_msfs_to_blender"
    bl_label = "Convert MSFS to Blender Material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.material_name:
            material = bpy.data.materials.get(self.material_name)
            if material:
                self.convert_material(material)
                self.report({'INFO'}, f"Converted material: {self.material_name}")
            else:
                self.report({'WARNING'}, f"Material not found: {self.material_name}")
        else:
            obj = context.active_object
            if obj and obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material:
                        self.convert_material(slot.material)
                self.report({'INFO'}, "Converted MSFS materials to Blender materials")
            else:
                self.report({'WARNING'}, "No active mesh object selected")
        return {'FINISHED'}

    def convert_material(self, material):
        if not hasattr(material, 'msfs_material_type'):
            return  # Not an MSFS material

        # Create a new Principled BSDF material
        material.use_nodes = True
        material.node_tree.nodes.clear()

        principled = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
        output = material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
        material.node_tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])

        # Transfer properties
        principled.inputs['Base Color'].default_value = material.msfs_base_color_factor
        principled.inputs['Metallic'].default_value = material.msfs_metallic_factor
        principled.inputs['Roughness'].default_value = material.msfs_roughness_factor
        
        # Create a Normal Map node for the normal scale
        normal_map = material.node_tree.nodes.new('ShaderNodeNormalMap')
        normal_map.inputs['Strength'].default_value = material.msfs_normal_scale
        material.node_tree.links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])

        # Transfer textures
        self.transfer_texture(material, 'msfs_base_color_texture', 'Base Color', principled)
        self.transfer_texture(material, 'msfs_occlusion_metallic_roughness_texture', 'Metallic', principled)
        self.transfer_texture(material, 'msfs_normal_texture', 'Normal', normal_map)
        self.transfer_texture(material, 'msfs_emissive_texture', 'Emission', principled)

    def transfer_texture(self, material, msfs_prop, principled_input, target_node):
        if hasattr(material, msfs_prop):
            texture = getattr(material, msfs_prop)
            if texture:
                tex_node = material.node_tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = texture
                if principled_input == 'Normal':
                    material.node_tree.links.new(
                        tex_node.outputs['Color'],
                        target_node.inputs['Color']
                    )
                else:
                    material.node_tree.links.new(
                        tex_node.outputs['Color'],
                        target_node.inputs[principled_input]
                    )

class LODIFY_OT_convert_blender_to_msfs(bpy.types.Operator):
    bl_idname = "lodify.convert_blender_to_msfs"
    bl_label = "Convert All Blender to MSFS Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            converted_count = 0
            skipped_count = 0

            for material in bpy.data.materials:
                if material.use_nodes:
                    # Check if the material is already an MSFS material
                    if hasattr(material, 'msfs_material_type') and material.msfs_material_type != 'NONE':
                        skipped_count += 1
                        continue

                    # Convert the material
                    self.convert_material(material, context)
                    converted_count += 1
                else:
                    skipped_count += 1

            self.report({'INFO'}, f"Converted {converted_count} materials. Skipped {skipped_count} materials.")
        except Exception as e:
            logging.exception("Error in convert_blender_to_msfs")
            self.report({'ERROR'}, f"An error occurred: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}

    def convert_material(self, material, context):
        # Ensure MSFS properties exist on the material
        if not hasattr(material, 'msfs_material_type'):
            material.msfs_material_type = 'NONE'

        # Your existing convert_material function here
        # Make sure to remove any references to obj and use material directly
        def ensure_4_elements(color):
            if len(color) == 3:
                return list(color) + [1.0]
            return list(color)

        principled = next((node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            self.report({'WARNING'}, f"No Principled BSDF node found in material '{material.name}'. Skipping.")
            return

        # Log original values
        original_color = ensure_4_elements(self.safe_get_input(principled, 'Base Color', (0.8, 0.8, 0.8, 1.0)))
        original_metallic = self.safe_get_input(principled, 'Metallic', 0.0)
        original_roughness = self.safe_get_input(principled, 'Roughness', 0.5)
        original_emission = ensure_4_elements(self.safe_get_input(principled, 'Emission', (0.0, 0.0, 0.0, 1.0)))
        original_alpha = self.safe_get_input(principled, 'Alpha', 1.0)

        # Set the material type to standard
        material.msfs_material_type = 'msfs_standard'

        # Transfer parameters
        material.msfs_base_color_factor = original_color
        material.msfs_metallic_factor = original_metallic
        material.msfs_roughness_factor = original_roughness
        material.msfs_emissive_factor = original_emission[:3]  # Only use RGB
        material.msfs_alpha_cutoff = original_alpha

        # Additional MSFS-specific parameters
        material.msfs_normal_scale = 1.0
        material.msfs_detail_uv_scale = 1.0
        material.msfs_detail_uv_offset_u = 0.0
        material.msfs_detail_uv_offset_v = 0.0

        # Handle textures
        material.msfs_base_color_texture = self.get_linked_texture(principled, 'Base Color')
        material.msfs_occlusion_metallic_roughness_texture = self.get_linked_texture(principled, 'Metallic')

        # Handle normal map
        if 'Normal' in principled.inputs and principled.inputs['Normal'].is_linked:
            from_node = principled.inputs['Normal'].links[0].from_node
            if from_node.type == 'NORMAL_MAP':
                if from_node.inputs[0].is_linked:
                    tex_node = from_node.inputs[0].links[0].from_node
                    if tex_node.type == 'TEX_IMAGE':
                        material.msfs_normal_texture = tex_node.image

        # Force an update
        material.update_tag()

    def safe_get_input(self, node, input_name, default_value):
        if input_name in node.inputs:
            return node.inputs[input_name].default_value
        logging.warning(f"Input '{input_name}' not found in node. Using default value.")
        return default_value

    def get_linked_texture(self, principled, input_name):
        if input_name in principled.inputs and principled.inputs[input_name].is_linked:
            from_node = principled.inputs[input_name].links[0].from_node
            if from_node.type == 'TEX_IMAGE':
                return from_node.image
        return None

class LODIFY_OT_bake_to_vertex_colors(bpy.types.Operator):
    bl_idname = "lodify.bake_to_vertex_colors"
    bl_label = "Bake Textures to Vertex Colors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        # Convert MSFS materials to Blender materials
        bpy.ops.lodify.convert_msfs_to_blender()

        for obj in selected_objects:
            if obj.type == 'MESH':
                self.bake_to_vertex_colors(obj)

        # Switch viewport shading to flat
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        space.shading.color_type = 'VERTEX'
                        space.shading.light = 'FLAT'
                        break
                break

        self.report({'INFO'}, f"Baked textures to vertex colors for {len(selected_objects)} object(s)")
        return {'FINISHED'}

    def bake_to_vertex_colors(self, obj):
        # Ensure the object is selected and active
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Create a color attribute if it doesn't exist
        color_attribute_name = f"{obj.name}_Color"
        if color_attribute_name not in obj.data.color_attributes:
            color_attribute = obj.data.color_attributes.new(
                name=color_attribute_name,
                type='FLOAT_COLOR',
                domain='POINT'
            )
            
            # Initialize the color attribute with white
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            color_layer = bm.loops.layers.color.get(color_attribute_name)
            
            if color_layer:
                for face in bm.faces:
                    for loop in face.loops:
                        loop[color_layer] = (1, 1, 1, 1)
                
                bm.to_mesh(mesh)
                mesh.update()
            
            bm.free()

        # Set the color attribute as active
        obj.data.color_attributes.active_color = obj.data.color_attributes[color_attribute_name]

        # Set up render settings
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True
        bpy.context.scene.render.bake.target = 'VERTEX_COLORS'

        # Ensure all texture images are loaded
        for mat_slot in obj.material_slots:
            material = mat_slot.material
            if material and material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        node.image.reload()

        # Bake vertex colors
        bpy.ops.object.bake(type='DIFFUSE')

        # Set the active color attribute for viewport display
        if hasattr(obj.data.attributes, 'active_color'):
            obj.data.attributes.active_color = obj.data.attributes[color_attribute_name]

classes = (
    LODIFY_OT_list_actions,
    LODIFY_OT_auto_setup,
    LODIFY_OT_generate_lod_decimate,
    LODIFY_OT_generate_lod_shrinkwrap,
    LODIFY_OT_apply_lod_modifiers,
    LODIFY_OT_convert_msfs_to_blender,
    LODIFY_OT_convert_blender_to_msfs,
    LODIFY_OT_bake_to_vertex_colors,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()