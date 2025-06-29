# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Blender addon for Microsoft Flight Simulator (MSFS) LOD (Level of Detail) generation. The addon creates multiple LOD levels from a base collection using various optimization methods, with automatic LOD value calculation based on MSFS 2024 standards.

## Architecture

The addon follows standard Blender addon structure with 4 main components:

- **`__init__.py`** - Addon registration and metadata
- **`operators.py`** - Core LOD generation logic and operators
- **`properties.py`** - Property definitions and scene data
- **`ui.py`** - User interface panels and lists

### Key Components

**LOD Generation Pipeline:**
1. Find active LOD00 collections (collections ending with "_LOD00")
2. Calculate object size and optimal LOD values
3. Generate LOD01-03 collections using configurable methods
4. Apply vertex colors and modifiers
5. Integrate with MSFS Multi-Export addon

**Generation Methods:**
- **Mixed (default)**: Decimate modifier for all LODs (LOD01-03)
- **Decimate Only**: Decimate modifier for all LODs
- **Shrinkwrap Only**: Cube proxy with shrinkwrap for all LODs

**LOD Selection:** Users can select which specific LOD levels to generate (LOD01, LOD02, LOD03) using checkboxes in the Generation Settings panel. This allows for partial LOD generation and faster processing when only specific levels are needed.

## Development Commands

Since this is a Blender addon, there are no traditional build/test commands. Development workflow:

1. **Install addon in Blender:**
   - Copy addon folder to Blender's addons directory
   - Enable in Blender Preferences > Add-ons

2. **Test in Blender:**
   - Create collections ending with "_LOD00" 
   - Enable addon in Scene Properties panel
   - Use "Generate LODs" button to test functionality

3. **Debug:**
   - Check Blender Console (Window > Toggle System Console) for debug output
   - All operators include extensive print statements for debugging

## Key Functions

### LOD Generation (`operators.py`)

**`find_base_collection()`** - Finds first active LOD00 collection
**`find_all_active_base_collections()`** - Finds all active LOD00 collections
**`calculate_optimal_lod_values(object_size_meters)`** - Calculates MSFS LOD values based on object size
**`set_msfs_multi_exporter_lod_values(base_name, lod_values)`** - Sets LOD values in MSFS Multi-Export addon

### Collection Management

Collections must follow naming pattern: `[BaseName]_LOD00`, `[BaseName]_LOD01`, etc.
Only active (checked) LOD00 collections in Scene Collections panel are processed.

### Vertex Color Handling

Four modes available:
- **AUTO**: LOD00-01 white, LOD02 baked from albedo texture, LOD03 inherited from LOD02
- **WHITE_ONLY**: All LODs get white colors
- **BAKE_ALL**: LOD00-01 white, LOD02 baked from albedo texture, LOD03 inherited from LOD02
- **TRANSFER_ALL**: LOD00-01 white, LOD02-03 gray colors

**Optimized LOD03 Generation**: LOD03 is created by copying already-processed LOD02 objects (with baked vertex colors) and applying additional decimate reduction at the next angle increment. This ensures consistent vertex colors between LOD02 and LOD03 while providing further geometric simplification.

### MSFS Integration

The addon integrates with MSFS Multi-Export addon by:
- Setting LOD values based on object size calculations
- Enabling grouped collections export
- Configuring XML generation settings

## Error Handling

The addon includes comprehensive error handling:
- Try-catch blocks around critical operations
- Fallback behavior for missing dependencies
- Detailed console logging for debugging
- Graceful degradation when MSFS Multi-Export is unavailable

## Important Notes

- Addon requires Blender 3.6+ 
- Designed specifically for MSFS workflow
- Shrinkwrap modifiers are left unapplied for manual fine-tuning
- LOD values follow MSFS pattern (higher = more visible at distance)
- Supports both automatic and manual LOD value calculation