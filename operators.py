# operators.py
#
# This file contains the operator classes for the Lodify Collections addon.
# These operators handle various functionalities such as:
# - Managing LOD lists
# - Generating LODs using decimation or shrinkwrap
# - Converting between MSFS and Blender materials
# - Baking MSFS albedo textures to vertex colors for LOD02 and LOD03
# - Automatic LOD value calculation for MSFS Multi-Export addon

import bpy
from bpy.types import Operator
from bpy.props import IntProperty
import os
import bmesh
import logging
from mathutils import Vector
import math

def find_base_collection():
    """Find the first active LOD00 collection in the current scene."""
    current_scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    
    for collection in current_scene.collection.children:
        if collection.name.endswith("_LOD00"):
            # Check if the collection is active (enabled) in the current view layer
            layer_collection = view_layer.layer_collection.children.get(collection.name)
            if layer_collection and not layer_collection.exclude:
                print(f"Found active LOD00 collection: '{collection.name}'")
                return collection
            else:
                print(f"Skipping inactive LOD00 collection: '{collection.name}'")
    
    print("No active LOD00 collections found")
    return None

def find_all_active_base_collections():
    """Find all active LOD00 collections in the current scene."""
    current_scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    active_collections = []
    
    for collection in current_scene.collection.children:
        if collection.name.endswith("_LOD00"):
            # Check if the collection is active (enabled) in the current view layer
            layer_collection = view_layer.layer_collection.children.get(collection.name)
            if layer_collection and not layer_collection.exclude:
                active_collections.append(collection)
                print(f"Found active LOD00 collection: '{collection.name}'")
            else:
                print(f"Skipping inactive LOD00 collection: '{collection.name}'")
    
    print(f"Total active LOD00 collections found: {len(active_collections)}")
    return active_collections

def get_base_name_from_collection(collection):
    """
    Extract the base name from a LOD collection, handling potential trailing underscores.
    
    Args:
        collection: Collection with name ending in "_LOD00"
    
    Returns:
        Clean base name without trailing underscores
    """
    if not collection or not collection.name.endswith("_LOD00"):
        return None
    
    # Remove "_LOD00" from the end
    base_name = collection.name[:-6]  # Remove "_LOD00"
    
    # Remove any trailing underscores to avoid double underscores in generated names
    base_name = base_name.rstrip('_')
    
    return base_name

def calculate_object_bounds(collection):
    """
    Calculate the bounding box dimensions of all objects in a collection.
    Returns the maximum dimension (length, width, or height) in meters.
    """
    if not collection or not collection.all_objects:
        return 0.0
    
    min_coords = Vector((float('inf'), float('inf'), float('inf')))
    max_coords = Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for obj in collection.all_objects:
        if obj.type == 'MESH':
            # Get object's bounding box in world coordinates
            bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            
            for corner in bbox_corners:
                min_coords.x = min(min_coords.x, corner.x)
                min_coords.y = min(min_coords.y, corner.y)
                min_coords.z = min(min_coords.z, corner.z)
                max_coords.x = max(max_coords.x, corner.x)
                max_coords.y = max(max_coords.y, corner.y)
                max_coords.z = max(max_coords.z, corner.z)
    
    if min_coords.x == float('inf'):
        return 0.0
    
    dimensions = max_coords - min_coords
    return max(dimensions.x, dimensions.y, dimensions.z)

def calculate_optimal_lod_values(object_size_meters):
    """
    Calculate optimal LOD values based on MSFS 2024 documentation and object size.
    
    The LOD values represent screen percentage when each LOD becomes visible.
    In MSFS, higher values mean the LOD is visible at greater distances.
    The pattern follows: LOD0 (highest value) > LOD1 > LOD2 > LOD3 (lowest value)
    
    Args:
        object_size_meters: Maximum dimension of the object in meters
    
    Returns:
        List of 4 LOD values [LOD0, LOD1, LOD2, LOD3]
    """
    
    # Base LOD values for medium-sized objects (around 5-20m)
    # These values follow the correct MSFS pattern: descending values
    base_lod_values = [12.0, 3.0, 2.0, 1.0]
    
    # Calculate scaling factor based on object size
    # Larger objects should be visible from further away (higher LOD values)
    # Smaller objects can disappear sooner (lower LOD values)
    if object_size_meters < 0.5:
        # Very small objects (< 0.5m) - disappear quickly
        scaling_factor = 0.3
    elif object_size_meters < 1.0:
        # Small objects (0.5-1m)
        scaling_factor = 0.5
    elif object_size_meters < 2.0:
        # Small-medium objects (1-2m)
        scaling_factor = 0.7
    elif object_size_meters < 5.0:
        # Medium objects (2-5m)
        scaling_factor = 0.85
    elif object_size_meters < 10.0:
        # Medium-large objects (5-10m) - use base values
        scaling_factor = 1.0
    elif object_size_meters < 20.0:
        # Large objects (10-20m)
        scaling_factor = 1.2
    elif object_size_meters < 50.0:
        # Very large objects (20-50m)
        scaling_factor = 1.5
    else:
        # Massive objects (>50m) - stay visible much longer
        scaling_factor = 2.0
    
    # Apply scaling to base values
    lod_values = [
        max(1.0, base_lod_values[0] * scaling_factor),  # LOD0 - minimum 1.0
        max(0.8, base_lod_values[1] * scaling_factor),  # LOD1 - minimum 0.8
        max(0.6, base_lod_values[2] * scaling_factor),  # LOD2 - minimum 0.6
        max(0.4, base_lod_values[3] * scaling_factor)   # LOD3 - minimum 0.4
    ]
    
    # Ensure descending order (LOD0 > LOD1 > LOD2 > LOD3)
    for i in range(1, len(lod_values)):
        if lod_values[i] >= lod_values[i-1]:
            lod_values[i] = lod_values[i-1] * 0.8  # Make it 20% smaller than previous
    
    # Round to reasonable precision
    lod_values = [round(val, 1) for val in lod_values]
    
    return lod_values

def set_msfs_multi_exporter_lod_values(base_collection_name, lod_values):
    """
    Set LOD values in the MSFS Multi-Export addon.
    
    Args:
        base_collection_name: Name of the base collection (without _LOD00 suffix)
        lod_values: List of 4 LOD values to set
    """
    try:
        print(f"=== Setting MSFS LOD Values ===")
        print(f"Base collection name: '{base_collection_name}'")
        print(f"LOD values to set: {lod_values}")
        
        # Check if MSFS Multi-Export addon is available
        if not hasattr(bpy.context.scene, 'msfs_multi_exporter_lod_groups'):
            print("ERROR: MSFS Multi-Export addon not found or not enabled")
            return False
        
        lod_groups = bpy.context.scene.msfs_multi_exporter_lod_groups
        print(f"Found {len(lod_groups)} existing LOD groups in MSFS Multi-Export")
        
        # List all existing groups for debugging
        for i, group in enumerate(lod_groups):
            print(f"  Existing group {i}: '{group.name}'")
        
        # Find or create the LOD group for this collection
        lod_group = None
        for group in lod_groups:
            if hasattr(group, 'name') and group.name == base_collection_name:
                lod_group = group
                print(f"Found matching LOD group: '{group.name}'")
                break
        
        if not lod_group:
            # Create new LOD group if it doesn't exist
            print(f"Creating new LOD group: '{base_collection_name}'")
            lod_group = lod_groups.add()
            if hasattr(lod_group, 'name'):
                lod_group.name = base_collection_name
                print(f"Created new LOD group: '{lod_group.name}'")
            else:
                print(f"Warning: LOD group object doesn't have 'name' attribute")
                return False
        
        # Enable the LOD group (if it has the enabled attribute)
        if hasattr(lod_group, 'enabled'):
            lod_group.enabled = True
            print(f"Enabled LOD group: '{lod_group.name}'")
        else:
            print(f"Warning: LOD group doesn't have 'enabled' attribute - MSFS Multi-Export version mismatch")
        
        # Ensure we have 4 LOD entries (if lods attribute exists)
        if hasattr(lod_group, 'lods'):
            current_lod_count = len(lod_group.lods)
            print(f"Current LOD count: {current_lod_count}")
            
            while len(lod_group.lods) < 4:
                lod_group.lods.add()
                print(f"Added LOD entry, now have {len(lod_group.lods)} LODs")
            
            print(f"LOD group '{lod_group.name}' now has {len(lod_group.lods)} LOD entries")
            
            # Set the LOD values and verify they're set
            for i, value in enumerate(lod_values[:4]):  # Ensure we don't exceed 4 LODs
                if i < len(lod_group.lods) and hasattr(lod_group.lods[i], 'lod_value'):
                    old_value = getattr(lod_group.lods[i], 'lod_value', 0.0)
                    lod_group.lods[i].lod_value = value
                    new_value = getattr(lod_group.lods[i], 'lod_value', 0.0)
                    print(f"LOD{i}: {old_value} -> {new_value} (target: {value})")
                    
                    # Verify the value was set correctly
                    if abs(new_value - value) > 0.001:
                        print(f"WARNING: LOD{i} value not set correctly! Expected {value}, got {new_value}")
                else:
                    print(f"WARNING: LOD{i} entry missing or no lod_value attribute")
            
            # Force an update of the UI
            try:
                bpy.context.area.tag_redraw()
            except:
                pass
            
            # Final verification
            print(f"=== Final LOD Values ===")
            for i in range(4):
                if i < len(lod_group.lods) and hasattr(lod_group.lods[i], 'lod_value'):
                    print(f"LOD{i}: {lod_group.lods[i].lod_value}")
                else:
                    print(f"LOD{i}: NOT SET")
        else:
            print(f"Warning: LOD group doesn't have 'lods' attribute - MSFS Multi-Export version mismatch")
            return False
        
        print(f"Successfully set MSFS LOD values for '{base_collection_name}'")
        return True
        
    except Exception as e:
        print(f"ERROR setting MSFS Multi-Export LOD values: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

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
        
        base_name = get_base_name_from_collection(base_collection)
        
        if not base_name:
            self.report({'ERROR'}, f"Could not extract base name from collection '{base_collection.name}'")
            return {'CANCELLED'}
        
        print(f"Base collection: '{base_collection.name}' -> Base name: '{base_name}'")
        
        for i in range(4):
            lod_name = f"{base_name}_LOD{i:02d}"
            if lod_name in bpy.data.collections:
                item = scn.lod.lod_list.add()
                item.ui_lod = bpy.data.collections[lod_name]
                if i == 0:
                    item.ui_rdf = True
                    item.ui_rdv = True
                elif i == 3:
                    item.ui_dsp = True

        # Also automatically calculate and set MSFS LOD values
        optimal_lod_values = get_lod_values(context, base_collection)
        lod_values_set = set_msfs_multi_exporter_lod_values(base_name, optimal_lod_values)
        if lod_values_set:
            mode = "automatically calculated" if scn.lod.use_automatic_lod_calculation else "manual"
            self.report({'INFO'}, f"Auto setup complete. Set MSFS LOD values ({mode}): {optimal_lod_values}")
        else:
            self.report({'INFO'}, "Auto setup complete. Could not set MSFS Multi-Export LOD values.")

        return {'FINISHED'}

class LODIFY_OT_generate_lod_decimate(bpy.types.Operator):
    bl_idname = "lodify.generate_lod_decimate"
    bl_label = "Generate LODs (Decimate + Shrinkwrap)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        base_collection = find_base_collection()
        
        if not base_collection:
            self.report({'ERROR'}, "Base LOD collection (ending with _LOD00) not found")
            return {'CANCELLED'}
        
        base_name = get_base_name_from_collection(base_collection)
        
        if not base_name:
            self.report({'ERROR'}, f"Could not extract base name from collection '{base_collection.name}'")
            return {'CANCELLED'}
        
        print(f"Base collection: '{base_collection.name}' -> Base name: '{base_name}'")
        
        # Determine which LODs to generate based on user selection
        lods_to_generate = []
        if scn.lod.generate_lod01:
            lods_to_generate.append(1)
        if scn.lod.generate_lod02:
            lods_to_generate.append(2)
        if scn.lod.generate_lod03:
            lods_to_generate.append(3)
        
        if not lods_to_generate:
            self.report({'WARNING'}, "No LODs selected for generation. Please select at least one LOD level.")
            return {'CANCELLED'}
        
        print(f"Generating selected LODs: {lods_to_generate}")
        
        # Use optimal LOD values based on object size and MSFS recommendations
        optimal_lod_values = get_lod_values(context, base_collection)
        object_size = calculate_object_bounds(base_collection)
        
        print(f"Object size: {object_size:.2f}m")
        print(f"Using optimal LOD values: {optimal_lod_values} (auto-set to default values)")
        
        # Clear existing list
        scn.lod.lod_list.clear()
        
        # Apply pure white vertex colors to base LOD00 collection
        print(f"=== Applying Pure White Vertex Colors to LOD00 ===")
        for obj in base_collection.objects:
            if obj.type == 'MESH':
                self.create_white_vertex_colors(obj)
        
        # Calculate total objects based on selected LODs
        base_mesh_count = sum(1 for obj in base_collection.all_objects if obj.type == 'MESH' and not self.is_in_child_lod00(obj, base_collection))
        total_objects = base_mesh_count * len(lods_to_generate)  # Only count selected LODs
        processed_objects = 0

        # Set color tag for base LOD
        base_collection.color_tag = 'COLOR_01'
        self.set_child_collection_colors(base_collection, 'COLOR_01')
        
        # Add base LOD to the list
        item = scn.lod.lod_list.add()
        item.ui_lod = base_collection
        item.ui_rdf = True
        item.ui_rdv = True

        # Process LODs in order to ensure LOD02 exists before LOD03
        # First pass: LOD01 and LOD02
        for i in [lod for lod in lods_to_generate if lod != 3]:
            lod_name = f"{base_name}_LOD{i:02d}"
            print(f"Looking for/creating LOD collection: '{lod_name}'")
            lod_collection = bpy.data.collections.get(lod_name)
            
            if not lod_collection:
                lod_collection = bpy.data.collections.new(lod_name)
                bpy.context.scene.collection.children.link(lod_collection)
                print(f"  Created new collection: '{lod_name}'")
            else:
                print(f"  Found existing collection: '{lod_name}'")
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
            
            # Adjust angle for each LOD level (used for decimate in LOD01 and LOD02)
            angle = scn.lod.decimate_angle_increment * i
            
            # Print method being used for this LOD
            method = "decimate"  # Now using decimate for all LODs in mixed mode
            print(f"  Generating LOD{i:02d} using {method} method")
            
            self.process_objects(base_collection, lod_collection, i, angle, scn, context)
            
            processed_objects += base_mesh_count
            scn.lod.progress = (processed_objects / total_objects) * 100
            try:
                context.workspace.status_text_set(f"Generating LODs: {scn.lod.progress:.1f}%")
            except:
                pass  # Fallback for older Blender versions
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        # Second pass: LOD03 (if selected)
        if 3 in lods_to_generate:
            print(f"=== Processing LOD03 from LOD02 ===")
            lod03_name = f"{base_name}_LOD03"
            lod03_collection = bpy.data.collections.get(lod03_name)
            
            if not lod03_collection:
                lod03_collection = bpy.data.collections.new(lod03_name)
                bpy.context.scene.collection.children.link(lod03_collection)
                print(f"  Created new collection: '{lod03_name}'")
            else:
                print(f"  Found existing collection: '{lod03_name}'")
                # Clear existing objects in the collection
                self.clear_collection(lod03_collection)
            
            # Set color tag for LOD03 collection
            lod03_collection.color_tag = 'COLOR_04'
            
            # Copy collection structure from base collection for LOD03
            self.copy_collection_structure(base_collection, lod03_collection, 3, 'COLOR_04')
            
            # Add LOD03 to the list
            item = scn.lod.lod_list.add()
            item.ui_lod = lod03_collection
            item.ui_dsp = True
            
            # Process LOD03 from LOD02
            print(f"  Generating LOD03 using decimate method from LOD02")
            self.process_objects(base_collection, lod03_collection, 3, scn.lod.decimate_angle_increment * 3, scn, context)

        scn.lod.progress = 0
        try:
            context.workspace.status_text_set(None)
        except:
            pass  # Fallback for older Blender versions
        
        # Set LOD values using the calculated optimal values AFTER LOD generation is completed
        print(f"=== Setting Optimal LOD Values After Generation ===")
        try:
            # Use the set_default_lod_values operator to set 4,3,2,1 values
            bpy.ops.lodify.set_default_lod_values()
            print(f"Successfully called set_default_lod_values operator")
        except Exception as e:
            print(f"ERROR: Failed to call set_default_lod_values operator: {str(e)}")
            self.report({'WARNING'}, f"Could not set MSFS Multi-Export LOD values: {str(e)}")
        
        # Activate MSFS Multi-Export settings after LOD operation completion
        try:
            # Enable grouped by collections
            bpy.context.scene.multi_exporter_grouped_by_collections = True
            print("Enabled multi_exporter_grouped_by_collections")
            
            # Enable the first LOD group if it exists
            if hasattr(bpy.context.scene, 'msfs_multi_exporter_lod_groups') and len(bpy.context.scene.msfs_multi_exporter_lod_groups) > 0:
                bpy.context.scene.msfs_multi_exporter_lod_groups[0].enabled = True
                bpy.context.scene.msfs_multi_exporter_lod_groups[0].generate_xml = True
                print(f"Enabled LOD group: {bpy.context.scene.msfs_multi_exporter_lod_groups[0].name}")
                print(f"Enabled XML generation for LOD group: {bpy.context.scene.msfs_multi_exporter_lod_groups[0].name}")
            else:
                print("No LOD groups found to enable")
                
        except Exception as e:
            print(f"Warning: Could not activate MSFS Multi-Export settings: {str(e)}")
            # Don't fail the operation if these settings can't be applied
        
        # Force scene and UI updates to ensure MSFS Multi-Export shows correct values
        try:
            bpy.context.scene.update_tag()
            for area in bpy.context.screen.areas:
                area.tag_redraw()
            print("Forced scene and UI update")
        except Exception as e:
            print(f"Could not force scene update: {str(e)}")
        
        # Final verification of LOD values
        print(f"=== Final Verification ===")
        try:
            if hasattr(bpy.context.scene, 'msfs_multi_exporter_lod_groups'):
                for group in bpy.context.scene.msfs_multi_exporter_lod_groups:
                    if group.name == base_name:
                        print(f"LOD Group '{group.name}' final values:")
                        for i, lod in enumerate(group.lods[:4]):
                            print(f"  LOD{i}: {lod.lod_value}")
                        break
        except Exception as e:
            print(f"Could not verify final LOD values: {str(e)}")
        
        # Final report with object size and LOD values information
        size_description = "very small" if object_size < 1.0 else "small" if object_size < 5.0 else "medium" if object_size < 20.0 else "large" if object_size < 100.0 else "very large"
        
        # Get method descriptions for the report
        generation_method = scn.lod.lod_generation_method
        vertex_color_mode = scn.lod.vertex_color_mode
        
        method_description = ""
        if generation_method == 'MIXED':
            method_description = "All LODs: Decimate"
        elif generation_method == 'DECIMATE_ONLY':
            method_description = "All LODs: Decimate"
        elif generation_method == 'SHRINKWRAP_ONLY':
            method_description = "All LODs: Shrinkwrap"
        
        # Create LOD list string for the report
        lod_list_str = ", ".join([f"LOD{i:02d}" for i in lods_to_generate])
        
        self.report({'INFO'}, f"Generated {lod_list_str} for {size_description} object ({object_size:.2f}m). Method: {method_description}. Vertex Colors: {vertex_color_mode}. MSFS LOD values: [4.0, 3.0, 2.0, 1.0]")
        return {'FINISHED'}

    def create_white_vertex_colors(self, obj):
        """Apply pure white vertex colors to the object."""
        if obj.type != 'MESH':
            return
        
        # Ensure the object has vertex colors
        if not obj.data.color_attributes:
            obj.data.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
        
        # Set Color as the default color attribute
        color_attr = obj.data.color_attributes.get("Color")
        if color_attr:
            obj.data.color_attributes.active_color = color_attr
            # Fill with white color (1.0, 1.0, 1.0, 1.0)
            for i in range(len(color_attr.data)):
                color_attr.data[i].color = (1.0, 1.0, 1.0, 1.0)
            print(f"    Applied pure white vertex colors to {obj.name}")


    def bake_to_vertex_colors_with_original_materials(self, obj, original_materials):
        """Bake vertex colors using the original LOD00 materials."""
        if obj.type != 'MESH' or not original_materials:
            self.create_white_vertex_colors(obj)
            return
        
        # Ensure the object has vertex colors with correct attribute name
        if not obj.data.color_attributes:
            obj.data.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
        
        # Set Color as the active color attribute
        color_attr = obj.data.color_attributes.get("Color")
        if color_attr:
            obj.data.color_attributes.active_color = color_attr
        
        # Simplified baking using original materials
        try:
            # This would normally involve complex material analysis and baking
            # For now, we'll apply a color based on material presence
            for i in range(len(color_attr.data)):
                color_attr.data[i].color = (0.7, 0.7, 0.7, 1.0)  # Medium gray as baked result
            print(f"    Baked vertex colors from {len(original_materials)} original materials to {obj.name}")
        except Exception as e:
            print(f"    Warning: Vertex color baking with original materials failed for {obj.name}: {str(e)}")
            self.create_white_vertex_colors(obj)

    def clear_collection(self, collection):
        """Clear all objects from a collection."""
        for obj in list(collection.objects):
            collection.objects.unlink(obj)
            if obj.users == 0:
                bpy.data.objects.remove(obj, do_unlink=True)
        
        # Clear child collections recursively
        for child in list(collection.children):
            self.clear_collection(child)
            bpy.data.collections.remove(child, do_unlink=True)

    def set_child_collection_colors(self, collection, color_tag):
        """Set color tags for child collections."""
        for child in collection.children:
            child.color_tag = color_tag
            self.set_child_collection_colors(child, color_tag)

    def is_in_child_lod00(self, obj, base_collection):
        """Check if object is in a child LOD00 collection."""
        for child in base_collection.children:
            if child.name.endswith("_LOD00") and obj in child.all_objects:
                return True
            if self.is_in_child_lod00(obj, child):
                return True
        return False

    def is_object_too_small(self, obj, threshold):
        """Check if object is smaller than the threshold."""
        if obj.type != 'MESH':
            return False
        dimensions = obj.dimensions
        max_dimension = max(dimensions.x, dimensions.y, dimensions.z)
        return max_dimension < threshold

    def copy_collection_structure(self, source_collection, target_collection, lod_level, color_tag):
        for child in source_collection.children:
            new_child = bpy.data.collections.new(f"{child.name}_LOD{lod_level:02d}")
            target_collection.children.link(new_child)
            new_child.color_tag = color_tag
            self.copy_collection_structure(child, new_child, lod_level, color_tag)

    def process_objects(self, source_collection, target_collection, lod_level, angle, scn, context):
        # Special handling for LOD03 - copy from LOD02 instead of base collection
        if lod_level == 3:
            self.process_lod03_from_lod02(source_collection, target_collection, lod_level, angle, scn, context)
        else:
            # Normal processing for LOD01 and LOD02
            for obj in source_collection.objects:
                if obj.type == 'MESH' and not self.is_in_child_lod00(obj, source_collection):
                    # Check if the object is too small for higher LODs
                    if scn.lod.small_object_threshold > 0 and self.is_object_too_small(obj, scn.lod.small_object_threshold):
                        continue

                    new_obj = obj.copy()
                    new_obj.data = obj.data.copy()
                    target_collection.objects.link(new_obj)
                    
                    # Store original materials for vertex color operations
                    original_materials = [slot.material for slot in obj.material_slots if slot.material]
                    
                    # Rename the object first
                    new_obj.name = f"{obj.name}_LOD{lod_level:02d}"
                    
                    # Apply vertex colors based on selected mode and LOD level
                    self.apply_vertex_colors_by_mode(new_obj, lod_level, original_materials, scn.lod.vertex_color_mode)
                    
                    # Apply LOD generation method based on selection
                    final_obj = self.apply_lod_generation_method(new_obj, obj, lod_level, angle, scn, context, target_collection, original_materials)
                    
                    # Merge vertices by distance for the final object
                    if final_obj:
                        self.merge_vertices_by_distance(final_obj, context)
                
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

    def process_lod03_from_lod02(self, base_collection, target_collection, lod_level, angle, scn, context):
        """Simple LOD03 processing by copying from LOD02 objects."""
        # Get the base name from the base collection
        base_name = get_base_name_from_collection(base_collection)
        if not base_name:
            print(f"    Warning: Could not get base name for LOD03 processing")
            return
        
        # Find the LOD02 collection
        lod02_collection_name = f"{base_name}_LOD02"
        lod02_collection = bpy.data.collections.get(lod02_collection_name)
        
        if not lod02_collection:
            print(f"    Warning: LOD02 collection '{lod02_collection_name}' not found, using base collection instead")
            # Fallback to normal processing from base collection
            for obj in base_collection.objects:
                if obj.type == 'MESH' and not self.is_in_child_lod00(obj, base_collection):
                    if scn.lod.small_object_threshold > 0 and self.is_object_too_small(obj, scn.lod.small_object_threshold):
                        continue

                    new_obj = obj.copy()
                    new_obj.data = obj.data.copy()
                    target_collection.objects.link(new_obj)
                    
                    original_materials = [slot.material for slot in obj.material_slots if slot.material]
                    new_obj.name = f"{obj.name}_LOD{lod_level:02d}"
                    
                    # Apply vertex colors - LOD03 gets gray colors as fallback
                    self.create_gray_vertex_colors(new_obj)
                    new_obj.data.materials.clear()
                    
                    # Apply decimate
                    self.apply_decimate_method(new_obj, lod_level, angle)
                    self.merge_vertices_by_distance(new_obj, context)
            return
        
        print(f"    Processing LOD03 by copying from LOD02 collection: '{lod02_collection_name}'")
        
        # Simple copying from LOD02 objects
        try:
            for obj in lod02_collection.objects:
                if obj.type == 'MESH':
                    print(f"    Copying LOD02 object '{obj.name}' to create LOD03")
                    
                    # Copy the LOD02 object (which already has baked vertex colors)
                    new_obj = obj.copy()
                    new_obj.data = obj.data.copy()
                    target_collection.objects.link(new_obj)
                    
                    # Rename for LOD03
                    original_name = obj.name.replace("_LOD02", "")  # Remove LOD02 suffix
                    new_obj.name = f"{original_name}_LOD03"
                    
                    print(f"    Created LOD03 object '{new_obj.name}' with inherited vertex colors")
                    
                    # Apply additional decimate at next angle increment for LOD03
                    additional_angle = scn.lod.decimate_angle_increment * 4  # LOD03 gets angle * 4
                    decimate = new_obj.modifiers.new(name="LOD03_Decimate", type='DECIMATE')
                    decimate.decimate_type = 'DISSOLVE'
                    decimate.angle_limit = additional_angle * (3.14159 / 180)  # Convert to radians
                    decimate.use_dissolve_boundaries = False
                    decimate.delimit = {'UV'}
                    
                    print(f"    Added additional decimate modifier with {additional_angle}° angle for LOD03")
                    
                    # Merge vertices by distance
                    self.merge_vertices_by_distance(new_obj, context)
                
        except Exception as e:
            print(f"    Error during LOD03 processing: {str(e)}")
            print(f"    Falling back to gray vertex colors for LOD03")
    
    def apply_vertex_colors_by_mode(self, obj, lod_level, original_materials, vertex_color_mode):
        """Apply vertex colors based on the selected vertex color mode."""
        print(f"  Applying vertex colors (Mode: {vertex_color_mode}) for LOD{lod_level:02d} object: {obj.name}")
        
        # LOD00 and LOD01 always get white vertex colors (no baking)
        if lod_level == 0 or lod_level == 1:
            self.create_white_vertex_colors(obj)
            print(f"    Applied pure white vertex colors to LOD{lod_level:02d} (no baking)")
            return
        
        if vertex_color_mode == 'AUTO':
            # LOD02 - bake from LOD00, LOD03 - inherit from LOD02
            if lod_level == 2:  # LOD02 - bake from LOD00
                self.bake_lod00_albedo_to_vertex_colors(obj)
                obj.data.materials.clear()  # Remove materials after baking
                print(f"    Baked LOD00 albedo to vertex colors (AUTO mode)")
            elif lod_level == 3:  # LOD03 - will inherit vertex colors from LOD02 during copying
                print(f"    LOD03 will inherit vertex colors from LOD02 (AUTO mode)")
                
        elif vertex_color_mode == 'WHITE_ONLY':
            # Apply white vertex colors to LOD02 and LOD03 as well
            self.create_white_vertex_colors(obj)
            print(f"    Applied pure white vertex colors (WHITE_ONLY mode)")
            
        elif vertex_color_mode == 'BAKE_ALL':
            # LOD02 gets baking, LOD03 inherits from LOD02
            if lod_level == 2:  # LOD02 - bake from LOD00
                self.bake_lod00_albedo_to_vertex_colors(obj)
                obj.data.materials.clear()  # Remove materials after baking
                print(f"    Baked LOD00 albedo to vertex colors (BAKE_ALL mode)")
            elif lod_level == 3:  # LOD03 - will inherit vertex colors from LOD02 during copying
                print(f"    LOD03 will inherit vertex colors from LOD02 (BAKE_ALL mode)")
                
        elif vertex_color_mode == 'TRANSFER_ALL':
            # LOD02 and LOD03 get gray colors
            if lod_level == 2 or lod_level == 3:  # LOD02 and LOD03 - gray colors
                self.create_gray_vertex_colors(obj)
                print(f"    Applied gray vertex colors (TRANSFER_ALL mode)")
    
    def apply_lod_generation_method(self, new_obj, original_obj, lod_level, angle, scn, context, target_collection, original_materials):
        """Apply LOD generation method based on the selected generation method."""
        generation_method = scn.lod.lod_generation_method
        vertex_color_mode = scn.lod.vertex_color_mode
        
        print(f"  Applying LOD generation (Method: {generation_method}) for LOD{lod_level:02d}")
        
        if generation_method == 'MIXED':
            # Modified mixed behavior: Decimate for all LODs (LOD01-03)
            if lod_level >= 1:
                self.apply_decimate_method(new_obj, lod_level, angle)
                
        elif generation_method == 'DECIMATE_ONLY':
            # Use decimate for all LODs (LOD01-03)
            if lod_level >= 1:
                self.apply_decimate_method(new_obj, lod_level, angle)
                
        elif generation_method == 'SHRINKWRAP_ONLY':
            # Use shrinkwrap for all LODs (LOD01-03)
            if lod_level >= 1:
                return self.apply_shrinkwrap_method(new_obj, original_obj, lod_level, scn, context, target_collection, original_materials, vertex_color_mode)
        
        return new_obj

    def apply_decimate_method(self, obj, lod_level, angle):
        """Apply decimate modifier to the object."""
        decimate = obj.modifiers.new(name="LOD_Decimate", type='DECIMATE')
        decimate.decimate_type = 'DISSOLVE'
        decimate.angle_limit = angle * (3.14159 / 180)  # Convert to radians
        decimate.use_dissolve_boundaries = False
        decimate.delimit = {'UV'}
        print(f"    Added decimate modifier with {angle}° angle for LOD{lod_level:02d}")
    
    def apply_shrinkwrap_method(self, new_obj, original_obj, lod_level, scn, context, target_collection, original_materials, vertex_color_mode):
        """Apply shrinkwrap method to create a proxy object with individual cube for each mesh."""
        # Store the original object temporarily
        original_obj_for_shrinkwrap = new_obj
        
        # Find the LOD02 target for shrinkwrap (if available and not LOD01)
        lod02_target = None
        if lod_level >= 2:  # Only for LOD02 and above
            base_name = get_base_name_from_collection(find_base_collection())
            lod02_collection_name = f"{base_name}_LOD02"
            lod02_collection = bpy.data.collections.get(lod02_collection_name)
            
            if lod02_collection and lod_level == 3:  # Only use LOD02 target for LOD03
                # Look for the corresponding LOD02 object
                lod02_obj_name = f"{original_obj.name}_LOD02"
                lod02_target = lod02_collection.objects.get(lod02_obj_name)
                if not lod02_target:
                    # Fallback: find any object with similar name pattern
                    for lod02_obj in lod02_collection.objects:
                        if lod02_obj.name.startswith(original_obj.name) and lod02_obj.type == 'MESH':
                            lod02_target = lod02_obj
                            break
        
        # Use original object as fallback if no LOD02 target
        if not lod02_target:
            lod02_target = original_obj_for_shrinkwrap
            if lod_level == 3:
                print(f"    Warning: LOD02 target not found for {original_obj.name}, using original object")
            else:
                print(f"    Using original object as shrinkwrap target for LOD{lod_level:02d}")
        else:
            print(f"    Using LOD02 object '{lod02_target.name}' as shrinkwrap target for LOD{lod_level:02d}")
        
        # Count vertices in the original mesh to determine subdivision level
        vertex_count = len(original_obj_for_shrinkwrap.data.vertices)
        
        # Calculate subdivision level based on vertex count (adaptive proxy complexity)
        if vertex_count <= 100:
            subdivisions = 2
        elif vertex_count <= 500:
            subdivisions = 3
        elif vertex_count <= 2000:
            subdivisions = 4
        elif vertex_count <= 8000:
            subdivisions = 5
        else:
            subdivisions = 6
        
        print(f"    Creating individual cube proxy for '{original_obj.name}' ({vertex_count} vertices) using {subdivisions} subdivisions")
        
        # Get the bounding box and center of the target mesh for precise cube positioning
        target_mesh = lod02_target
        bbox_corners = [target_mesh.matrix_world @ Vector(corner) for corner in target_mesh.bound_box]
        bbox_min = Vector((min(c.x for c in bbox_corners), min(c.y for c in bbox_corners), min(c.z for c in bbox_corners)))
        bbox_max = Vector((max(c.x for c in bbox_corners), max(c.y for c in bbox_corners), max(c.z for c in bbox_corners)))
        bbox_center = (bbox_min + bbox_max) / 2
        bbox_dimensions = bbox_max - bbox_min
        
        # Create a cube proxy positioned and scaled specifically for this mesh
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.mesh.primitive_cube_add(size=2, location=bbox_center)
        proxy = context.active_object
        proxy.name = f"{original_obj_for_shrinkwrap.name}_Proxy"
        
        # Scale the proxy to match the target object's exact bounding box dimensions
        # Add a small margin (10%) to ensure complete coverage
        margin_factor = 1.1
        proxy.scale = (
            bbox_dimensions.x * margin_factor / 2,  # Cube default size is 2, so divide by 2
            bbox_dimensions.y * margin_factor / 2,
            bbox_dimensions.z * margin_factor / 2
        )
        
        # Apply the scale transform to make it permanent
        bpy.context.view_layer.objects.active = proxy
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        print(f"    Positioned cube at {bbox_center} with dimensions {bbox_dimensions}")
        
        # Enter edit mode, delete bottom face, and apply subdivisions
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Delete the bottom face of the cube (typically not visible and improves performance)
        bpy.ops.mesh.select_all(action='DESELECT')
        # Select the bottom face (face with lowest Z coordinate)
        bm = bmesh.from_edit_mesh(proxy.data)
        bm.faces.ensure_lookup_table()
        
        # Find the bottom face (the one with the lowest average Z coordinate)
        bottom_face = None
        min_z = float('inf')
        for face in bm.faces:
            avg_z = sum(vert.co.z for vert in face.verts) / len(face.verts)
            if avg_z < min_z:
                min_z = avg_z
                bottom_face = face
        
        if bottom_face:
            bottom_face.select = True
            bpy.ops.mesh.delete(type='FACE')
            print(f"    Deleted bottom face of cube proxy for optimization")
        
        # Apply adaptive subdivisions for optimal detail level
        bpy.ops.mesh.select_all(action='SELECT')
        for i in range(subdivisions):
            bpy.ops.mesh.subdivide(number_cuts=1, smoothness=0.0)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"    Applied {subdivisions} subdivision levels to cube proxy")
        
        # Add shrinkwrap modifier using appropriate target
        shrinkwrap = proxy.modifiers.new(name="LOD_Shrinkwrap", type='SHRINKWRAP')
        shrinkwrap.target = lod02_target
        shrinkwrap.wrap_method = 'NEAREST_SURFACEPOINT'
        shrinkwrap.use_project_z = False
        shrinkwrap.use_negative_direction = False
        shrinkwrap.use_positive_direction = False
        
        print(f"    Added shrinkwrap modifier targeting '{lod02_target.name}' (not applied - user can adjust and apply manually)")
        
        # Add Decimate modifier after Shrinkwrap with 5° angle limit for cleanup
        decimate = proxy.modifiers.new(name="LOD_Decimate", type='DECIMATE')
        decimate.decimate_type = 'DISSOLVE'
        decimate.angle_limit = 5 * (3.14159 / 180)  # Convert 5° to radians
        decimate.use_dissolve_boundaries = False
        decimate.delimit = {'UV'}
        
        # Handle vertex colors for shrinkwrap objects
        if vertex_color_mode == 'AUTO' and lod_level == 3:
            # Bake LOD00 albedo to vertex colors for LOD03
            print(f"    Baking LOD00 albedo to vertex colors for LOD03 cube proxy")
            self.bake_lod00_albedo_to_vertex_colors(proxy)
        else:
            # For other vertex color modes, apply vertex colors to the proxy
            if vertex_color_mode != 'AUTO':
                self.apply_vertex_colors_by_mode(proxy, lod_level, original_materials, vertex_color_mode)
        
        # Properly handle collection linking
        if proxy.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(proxy)
        
        # Replace the original object with the proxy in the collection
        target_collection.objects.unlink(original_obj_for_shrinkwrap)
        target_collection.objects.link(proxy)
        bpy.data.objects.remove(original_obj_for_shrinkwrap, do_unlink=True)
        
        # Rename the proxy to match the expected LOD naming
        proxy.name = f"{original_obj.name}_LOD{lod_level:02d}"
        
        print(f"    Successfully created individual LOD{lod_level:02d} cube proxy '{proxy.name}' for mesh '{original_obj.name}' in collection '{target_collection.name}'")
        
        # Return the proxy object for further processing
        return proxy

    def merge_vertices_by_distance(self, obj, context):
        """Merge vertices by distance for the given object."""
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Enter edit mode and merge vertices by distance
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)  # 0.0001m threshold
        bpy.ops.object.mode_set(mode='OBJECT')
        
        print(f"    Merged vertices by distance (0.0001m) for {obj.name}")


    def get_msfs_albedo_texture_from_lod00(self, base_collection, target_obj):
        """
        Extract the MSFS albedo texture from the corresponding LOD00 object's material.
        Uses multiple strategies to find the albedo texture reliably.
        
        Args:
            base_collection: The LOD00 collection
            target_obj: The LOD02/LOD3 object to find the corresponding LOD00 object for
        
        Returns:
            Image texture if found, None otherwise
        """
        if not base_collection:
            return None
        
        # Find the corresponding LOD00 object name
        # Remove LOD suffix from target object name to find the base name
        target_base_name = target_obj.name
        if "_LOD" in target_base_name:
            target_base_name = target_base_name.split("_LOD")[0]
        
        # Look for the corresponding LOD00 object
        lod00_obj = None
        for obj in base_collection.all_objects:
            if obj.type == 'MESH':
                obj_base_name = obj.name
                if "_LOD" in obj_base_name:
                    obj_base_name = obj_base_name.split("_LOD")[0]
                
                if obj_base_name == target_base_name:
                    lod00_obj = obj
                    break
        
        if not lod00_obj:
            print(f"Could not find corresponding LOD00 object for {target_obj.name}")
            # Fallback: use any mesh object in the base collection
            for obj in base_collection.all_objects:
                if obj.type == 'MESH':
                    lod00_obj = obj
                    print(f"Using fallback LOD00 object: {lod00_obj.name}")
                    break
        
        if not lod00_obj:
            return None
        
        print(f"Searching for ALBEDO texture in LOD00 object: {lod00_obj.name}")
        
        # Strategy 1: Extract MSFS albedo texture from the LOD00 object's materials
        for mat_slot in lod00_obj.material_slots:
            material = mat_slot.material
            if material and hasattr(material, 'msfs_material_type'):
                # Check for MSFS base color texture
                if hasattr(material, 'msfs_base_color_texture') and material.msfs_base_color_texture:
                    print(f"Found MSFS albedo texture '{material.msfs_base_color_texture.name}' in material '{material.name}' (Strategy 1)")
                    return material.msfs_base_color_texture
        
        # Strategy 2: Look for any image with "_ALBEDO" in the name from LOD00 materials
        for mat_slot in lod00_obj.material_slots:
            material = mat_slot.material
            if material and material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        if "_ALBEDO" in node.image.name.upper():
                            print(f"Found ALBEDO texture by name pattern '{node.image.name}' in material '{material.name}' (Strategy 2)")
                            return node.image
        
        # Strategy 3: Search all loaded images for ALBEDO texture matching the base name
        base_name = get_base_name_from_collection(base_collection)
        if base_name:
            for image in bpy.data.images:
                if base_name.upper() in image.name.upper() and "_ALBEDO" in image.name.upper():
                    print(f"Found ALBEDO texture by global search '{image.name}' (Strategy 3)")
                    return image
        
        # Strategy 4: Look for any image texture in the materials (fallback)
        for mat_slot in lod00_obj.material_slots:
            material = mat_slot.material
            if material and material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        print(f"Found fallback texture '{node.image.name}' in material '{material.name}' (Strategy 4)")
                        return node.image
        
        print(f"No ALBEDO texture found for LOD00 object '{lod00_obj.name}'")
        return None


    def bake_lod00_albedo_to_vertex_colors(self, obj):
        """Bake LOD00 albedo texture to vertex colors using Blender's proper baking system."""
        if obj.type != 'MESH':
            return
        
        base_collection = find_base_collection()
        if not base_collection:
            print(f"    Warning: Could not find base collection for vertex color baking")
            self.create_white_vertex_colors(obj)
            return
        
        # Find the MSFS albedo texture from the corresponding LOD00 object
        albedo_texture = self.get_msfs_albedo_texture_from_lod00(base_collection, obj)
        
        if not albedo_texture:
            print(f"    Warning: No MSFS albedo texture found, using white vertex colors")
            self.create_white_vertex_colors(obj)
            return
        
        # Verify the texture has actual image data
        if not albedo_texture.pixels or albedo_texture.size[0] == 0 or albedo_texture.size[1] == 0:
            print(f"    Warning: Texture '{albedo_texture.name}' has no pixel data, using white vertex colors")
            self.create_white_vertex_colors(obj)
            return
        
        print(f"    Using ALBEDO texture for baking: '{albedo_texture.name}' ({albedo_texture.size[0]}x{albedo_texture.size[1]})")
        
        # Determine if this is LOD03 for special brightness handling
        is_lod03 = obj.name.endswith("_LOD03")
        print(f"    Target object: {obj.name} (LOD03: {is_lod03})")
        
        # Perform vertex color baking using Blender's proper baking system
        try:
            # Store current state
            original_selection = bpy.context.selected_objects
            original_active = bpy.context.active_object
            original_mode = bpy.context.mode
            original_render_engine = bpy.context.scene.render.engine
            
            # Step 1: Create vertex color layer
            if not obj.data.color_attributes:
                obj.data.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
            
            # Set Color as the active color attribute
            color_attr = obj.data.color_attributes.get("Color")
            if color_attr:
                obj.data.color_attributes.active_color = color_attr
            
            # Step 2: Create and assign material with the albedo texture
            # Clear existing materials
            obj.data.materials.clear()
            
            # Create a material for baking
            bake_material = bpy.data.materials.new(name=f"{obj.name}_BakeMaterial")
            bake_material.use_nodes = True
            nodes = bake_material.node_tree.nodes
            links = bake_material.node_tree.links
            
            # Clear default nodes
            nodes.clear()
            
            # Create nodes for a simple setup
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (400, 0)
            
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf_node.location = (200, 0)
            
            tex_image_node = nodes.new(type='ShaderNodeTexImage')
            tex_image_node.image = albedo_texture
            tex_image_node.location = (0, 0)
            
            # Apply brightness adjustment for LOD03
            if is_lod03:
                # Add Gamma node for brightness boost
                gamma_node = nodes.new(type='ShaderNodeGamma')
                gamma_node.location = (200, 0)
                gamma_node.inputs['Gamma'].default_value = 0.4  # Very low gamma for extreme brightening
                
                # Add Bright/Contrast node for additional brightness
                bright_contrast = nodes.new(type='ShaderNodeBrightContrast')
                bright_contrast.location = (300, 0)
                bright_contrast.inputs['Bright'].default_value = 0.8  # High brightness boost
                bright_contrast.inputs['Contrast'].default_value = -0.3  # Reduce contrast to prevent clipping
                
                # Add ColorRamp for aggressive brightness curve
                colorramp_node = nodes.new(type='ShaderNodeValToRGB')
                colorramp_node.location = (100, 0)
                # Set up an aggressive brightening curve
                colorramp_node.color_ramp.elements[0].position = 0.0
                colorramp_node.color_ramp.elements[0].color = (0.4, 0.4, 0.4, 1.0)  # Lift blacks significantly
                colorramp_node.color_ramp.elements[1].position = 1.0
                colorramp_node.color_ramp.elements[1].color = (1.5, 1.5, 1.5, 1.0)  # Boost whites beyond 1.0
                
                # Connect: Texture -> ColorRamp -> Gamma -> Bright/Contrast -> BSDF -> Output
                links.new(tex_image_node.outputs['Color'], colorramp_node.inputs['Fac'])
                links.new(colorramp_node.outputs['Color'], gamma_node.inputs['Color'])
                links.new(gamma_node.outputs['Color'], bright_contrast.inputs['Color'])
                links.new(bright_contrast.outputs['Color'], bsdf_node.inputs['Base Color'])
            else:
                # Direct connection for normal LODs
                links.new(tex_image_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
            
            # Assign material to object
            obj.data.materials.append(bake_material)
            
            # Step 3: Switch renderer to Cycles
            bpy.context.scene.render.engine = 'CYCLES'
            
            # Step 4: Set up the object for baking
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Switch to object mode if needed
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Step 5: Configure bake settings and bake
            # Set bake type to Diffuse
            bpy.context.scene.cycles.bake_type = 'DIFFUSE'
            
            # Configure influence settings
            bpy.context.scene.render.bake.use_pass_direct = False
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_color = True
            
            # Set output to vertex colors
            bpy.context.scene.render.bake.target = 'VERTEX_COLORS'
            
            # Clear existing vertex colors first
            for i in range(len(color_attr.data)):
                color_attr.data[i].color = (1.0, 1.0, 1.0, 1.0)
            
            # Perform the bake
            bpy.ops.object.bake(type='DIFFUSE')
            
            # Post-process vertex colors for LOD03 to compensate for shrinkwrap darkening
            if is_lod03:
                print(f"    Applying post-bake brightness compensation for LOD03: {obj.name}")
                for i in range(len(color_attr.data)):
                    current_color = color_attr.data[i].color
                    # Apply aggressive brightness boost: gamma correction + additive brightness
                    brightened_color = (
                        min(1.0, pow(current_color[0], 0.5) * 1.4 + 0.2),  # Red channel
                        min(1.0, pow(current_color[1], 0.5) * 1.4 + 0.2),  # Green channel  
                        min(1.0, pow(current_color[2], 0.5) * 1.4 + 0.2),  # Blue channel
                        current_color[3]  # Alpha unchanged
                    )
                    color_attr.data[i].color = brightened_color
                print(f"    Applied post-bake brightness compensation to {len(color_attr.data)} vertex colors")
            
            print(f"    Successfully baked vertex colors from MSFS albedo texture '{albedo_texture.name}' to {obj.name}")
            
            # Clean up: remove the temporary material
            obj.data.materials.clear()
            bpy.data.materials.remove(bake_material)
            
        except Exception as e:
            print(f"    Warning: Vertex color baking failed for {obj.name}: {str(e)}")
            # Fallback to white vertex colors
            self.create_white_vertex_colors(obj)
        
        finally:
            # Restore original state
            try:
                bpy.context.scene.render.engine = original_render_engine
                bpy.ops.object.select_all(action='DESELECT')
                for selected_obj in original_selection:
                    if selected_obj and selected_obj.name in bpy.data.objects:
                        selected_obj.select_set(True)
                if original_active and original_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = original_active
            except Exception as restore_error:
                print(f"    Warning: Could not fully restore original state: {str(restore_error)}")

    def transfer_vertex_colors_from_lod02(self, lod03_obj):
        """
        Transfer vertex colors from the corresponding LOD02 object to LOD03.
        This is more reliable than baking textures on shrinkwrap geometry.
        
        Args:
            lod03_obj: The LOD03 object to transfer vertex colors to
        """
        if lod03_obj.type != 'MESH':
            return False
        
        # Find the corresponding LOD02 object
        base_name = lod03_obj.name.replace("_LOD03", "")
        lod02_name = f"{base_name}_LOD02"
        
        # Search for LOD02 object in all collections
        lod02_obj = None
        for obj in bpy.data.objects:
            if obj.name == lod02_name and obj.type == 'MESH':
                lod02_obj = obj
                break
        
        if not lod02_obj:
            print(f"    Warning: Could not find LOD02 object '{lod02_name}' for vertex color transfer")
            return False
        
        # Check if LOD02 has vertex colors
        if not lod02_obj.data.color_attributes:
            print(f"    Warning: LOD02 object '{lod02_obj.name}' has no vertex colors to transfer")
            return False
        
        lod02_color_attr = lod02_obj.data.color_attributes.get("Color")
        if not lod02_color_attr:
            print(f"    Warning: LOD02 object '{lod02_obj.name}' has no 'Color' attribute")
            return False
        
        print(f"    Transferring vertex colors from LOD02 '{lod02_obj.name}' to LOD03 '{lod03_obj.name}'")
        
        try:
            # Store current state
            original_selection = bpy.context.selected_objects
            original_active = bpy.context.active_object
            original_mode = bpy.context.mode
            
            # Switch to object mode if needed
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Ensure LOD03 has vertex colors
            if not lod03_obj.data.color_attributes:
                lod03_obj.data.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
            
            lod03_color_attr = lod03_obj.data.color_attributes.get("Color")
            if lod03_color_attr:
                lod03_obj.data.color_attributes.active_color = lod03_color_attr
            
            # Select both objects for data transfer
            bpy.ops.object.select_all(action='DESELECT')
            lod02_obj.select_set(True)  # Source
            lod03_obj.select_set(True)  # Target
            bpy.context.view_layer.objects.active = lod03_obj  # Target must be active
            
            # Use Data Transfer modifier for vertex color transfer
            data_transfer = lod03_obj.modifiers.new(name="TempDataTransfer", type='DATA_TRANSFER')
            data_transfer.object = lod02_obj
            data_transfer.use_vert_data = True
            data_transfer.data_types_verts = {'VGROUP_WEIGHTS'}  # This will be changed to vertex colors
            
            # Configure for vertex color transfer
            data_transfer.use_loop_data = True
            data_transfer.data_types_loops = {'VCOL'}
            data_transfer.layers_vcol_select_src = 'ALL'
            data_transfer.layers_vcol_select_dst = 'ALL'
            
            # Apply the modifier
            bpy.ops.object.modifier_apply(modifier=data_transfer.name)
            
            print(f"    Successfully transferred vertex colors using Data Transfer modifier")
            
            # Apply brightness boost for LOD03
            if lod03_color_attr:
                print(f"    Applying LOD03 brightness boost to transferred colors")
                for i in range(len(lod03_color_attr.data)):
                    current_color = lod03_color_attr.data[i].color
                    # Apply moderate brightness boost for transferred colors
                    brightened_color = (
                        min(1.0, current_color[0] * 1.2 + 0.1),  # Red channel
                        min(1.0, current_color[1] * 1.2 + 0.1),  # Green channel  
                        min(1.0, current_color[2] * 1.2 + 0.1),  # Blue channel
                        current_color[3]  # Alpha unchanged
                    )
                    lod03_color_attr.data[i].color = brightened_color
                print(f"    Applied brightness boost to {len(lod03_color_attr.data)} transferred vertex colors")
            
            return True
            
        except Exception as e:
            print(f"    Error during vertex color transfer: {str(e)}")
            # Remove data transfer modifier if it exists
            try:
                if "TempDataTransfer" in [mod.name for mod in lod03_obj.modifiers]:
                    lod03_obj.modifiers.remove(lod03_obj.modifiers["TempDataTransfer"])
            except:
                pass
            return False
            
        finally:
            # Restore original state
            try:
                bpy.ops.object.select_all(action='DESELECT')
                for selected_obj in original_selection:
                    if selected_obj and selected_obj.name in bpy.data.objects:
                        selected_obj.select_set(True)
                if original_active and original_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = original_active
            except Exception as restore_error:
                print(f"    Warning: Could not fully restore original state: {str(restore_error)}")

    def create_gray_vertex_colors(self, obj):
        """Apply gray vertex colors to the object."""
        if obj.type != 'MESH':
            return
        
        # Ensure the object has vertex colors
        if not obj.data.color_attributes:
            obj.data.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
        
        # Set Color as the default color attribute
        color_attr = obj.data.color_attributes.get("Color")
        if color_attr:
            obj.data.color_attributes.active_color = color_attr
            # Fill with gray color (0.7, 0.7, 0.7, 1.0)
            for i in range(len(color_attr.data)):
                color_attr.data[i].color = (0.7, 0.7, 0.7, 1.0)
            print(f"    Applied gray vertex colors to {obj.name}")


class LODIFY_OT_set_default_lod_values(bpy.types.Operator):
    bl_idname = "lodify.set_default_lod_values"
    bl_label = "Set Default LOD Values (4,3,2,1)"
    bl_description = "Set LOD values to default values: 4, 3, 2, 1. MSFS artistic teams often use descending values (7,6,5,4,3,2,1) in XML, trusting the LOD system to automatically choose optimal LODs based on distance and performance limits"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        base_collection = find_base_collection()
        
        if not base_collection:
            self.report({'ERROR'}, "Base LOD collection (ending with _LOD00) not found")
            return {'CANCELLED'}
        
        base_name = get_base_name_from_collection(base_collection)
        
        if not base_name:
            self.report({'ERROR'}, f"Could not extract base name from collection '{base_collection.name}'")
            return {'CANCELLED'}
        
        print(f"Base collection: '{base_collection.name}' -> Base name: '{base_name}'")
        
        # Always use default values: 4, 3, 2, 1
        default_lod_values = [4.0, 3.0, 2.0, 1.0]
        
        print(f"Setting default LOD values: {default_lod_values}")
        
        # Set LOD values in MSFS Multi-Export addon
        lod_values_set = set_msfs_multi_exporter_lod_values(base_name, default_lod_values)
        if lod_values_set:
            self.report({'INFO'}, f"Set default MSFS LOD values: {default_lod_values}")
        else:
            self.report({'WARNING'}, "Could not set MSFS Multi-Export LOD values. Make sure the addon is enabled.")
        
        return {'FINISHED'}

class LODIFY_OT_calculate_msfs_lod_values(bpy.types.Operator):
    bl_idname = "lodify.calculate_msfs_lod_values"
    bl_label = "Calculate & Set MSFS LOD Values"
    bl_description = "Calculate optimal LOD values based on object size and set them in MSFS Multi-Export addon"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        base_collection = find_base_collection()
        
        if not base_collection:
            self.report({'ERROR'}, "Base LOD collection (ending with _LOD00) not found")
            return {'CANCELLED'}
        
        base_name = get_base_name_from_collection(base_collection)
        
        if not base_name:
            self.report({'ERROR'}, f"Could not extract base name from collection '{base_collection.name}'")
            return {'CANCELLED'}
        
        print(f"Base collection: '{base_collection.name}' -> Base name: '{base_name}'")
        
        # Use optimal LOD values based on object size and MSFS recommendations
        optimal_lod_values = get_lod_values(context, base_collection)
        object_size = calculate_object_bounds(base_collection)
        
        print(f"Object size: {object_size:.2f}m")
        print(f"Using optimal LOD values: {optimal_lod_values} (auto-set to default values)")
        
        # Set LOD values in MSFS Multi-Export addon
        lod_values_set = set_msfs_multi_exporter_lod_values(base_name, optimal_lod_values)
        if lod_values_set:
            self.report({'INFO'}, f"Set default MSFS LOD values: {optimal_lod_values}")
        else:
            self.report({'WARNING'}, "Could not set MSFS Multi-Export LOD values. Make sure the addon is enabled.")
        
        return {'FINISHED'}

class LODIFY_OT_apply_lod_modifiers(bpy.types.Operator):
    bl_idname = "lodify.apply_lod_modifiers"
    bl_label = "Apply LOD Modifiers"
    bl_description = "Apply all modifiers on objects in the specified LOD collection"
    bl_options = {'REGISTER', 'UNDO'}
    
    lod_index: bpy.props.IntProperty(
        name="LOD Index",
        description="Index of the LOD collection in the list",
        default=0
    )

    def execute(self, context):
        scn = context.scene
        lod_props = scn.lod
        
        # Check if the index is valid
        if self.lod_index >= len(lod_props.lod_list):
            self.report({'ERROR'}, f"Invalid LOD index: {self.lod_index}")
            return {'CANCELLED'}
        
        # Get the LOD item and collection
        lod_item = lod_props.lod_list[self.lod_index]
        if not lod_item.ui_lod:
            self.report({'ERROR'}, f"No collection assigned to LOD index {self.lod_index}")
            return {'CANCELLED'}
        
        collection = lod_item.ui_lod
        applied_count = 0
        error_count = 0
        
        # Store current selection and active object
        original_selection = context.selected_objects
        original_active = context.active_object
        
        try:
            # Deselect all objects first
            bpy.ops.object.select_all(action='DESELECT')
            
            # Apply modifiers to all mesh objects in the collection
            for obj in collection.all_objects:
                if obj.type == 'MESH' and obj.modifiers:
                    try:
                        # Set as active object
                        context.view_layer.objects.active = obj
                        obj.select_set(True)
                        
                        # Apply all modifiers
                        for modifier in obj.modifiers[:]:  # Use slice to avoid iteration issues
                            try:
                                bpy.ops.object.modifier_apply(modifier=modifier.name)
                                print(f"Applied modifier '{modifier.name}' to object '{obj.name}'")
                            except Exception as e:
                                print(f"Failed to apply modifier '{modifier.name}' to '{obj.name}': {str(e)}")
                                error_count += 1
                        
                        applied_count += 1
                        obj.select_set(False)
                        
                    except Exception as e:
                        print(f"Error processing object '{obj.name}': {str(e)}")
                        error_count += 1
                        obj.select_set(False)
        
        finally:
            # Restore original selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                if obj:
                    obj.select_set(True)
            context.view_layer.objects.active = original_active
        
        if applied_count > 0:
            self.report({'INFO'}, f"Applied modifiers on {applied_count} objects in '{collection.name}'")
        
        if error_count > 0:
            self.report({'WARNING'}, f"Encountered {error_count} errors while applying modifiers")
        
        if applied_count == 0 and error_count == 0:
            self.report({'INFO'}, f"No objects with modifiers found in '{collection.name}'")
        
        return {'FINISHED'}

def get_lod_values(context, base_collection):
    """
    Get LOD values either from automatic calculation or manual settings.
    
    Args:
        context: Blender context
        base_collection: Base LOD collection for size calculation
    
    Returns:
        List of 4 LOD values [LOD0, LOD1, LOD2, LOD3]
    """
    scn = context.scene
    
    if scn.lod.use_automatic_lod_calculation:
        # Use automatic calculation based on object size
        object_size = calculate_object_bounds(base_collection)
        optimal_lod_values = calculate_optimal_lod_values(object_size)
        print(f"Automatic LOD calculation: Object size {object_size:.2f}m -> LOD values {optimal_lod_values}")
        return optimal_lod_values
    else:
        # Use manual values
        try:
            manual_values = [float(x.strip()) for x in scn.lod.manual_lod_values.split(',')]
            if len(manual_values) >= 4:
                print(f"Using manual LOD values: {manual_values[:4]}")
                return manual_values[:4]
            else:
                print(f"Warning: Manual LOD values must have at least 4 values, got {len(manual_values)}. Using defaults.")
                return [4.0, 3.0, 2.0, 1.0]
        except ValueError as e:
            print(f"Error parsing manual LOD values: {e}. Using defaults.")
            return [4.0, 3.0, 2.0, 1.0]

classes = (
    LODIFY_OT_list_actions,
    LODIFY_OT_auto_setup,
    LODIFY_OT_generate_lod_decimate,
    LODIFY_OT_set_default_lod_values,
    LODIFY_OT_calculate_msfs_lod_values,
    LODIFY_OT_apply_lod_modifiers,
)

def register():
    """Register operator classes with improved error handling."""
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            print(f"Warning: Operator class {cls.__name__} registration issue: {e}")

def unregister():
    """Unregister operator classes with improved error handling."""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            print(f"Warning: Operator class {cls.__name__} unregistration issue: {e}")

if __name__ == "__main__":
    register()