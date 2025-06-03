# MSFS LOD Maker Addon

## Overview
MSFS LOD system for collections in Blender 3.6 & above, with LOD generation and automatic MSFS LOD value calculation. It allows for easy management and generation of LODs, with features for decimation, material conversion, texture baking, and automatic optimization of LOD values for the MSFS Multi-Export addon.

## Installation
1. Download the addon ZIP file.
2. In Blender, go to Edit > Preferences > Add-ons.
3. Click "Install" and select the downloaded ZIP file.
4. Enable the addon by checking the box next to "Scene: Lodify Collections".

## Features
- Automatic LOD setup for collections
- **Mixed LOD generation**: Decimate for LOD01-02, Shrinkwrap for LOD03 (final LOD)
- **Flexible LOD generation methods**: Choose between Mixed (recommended), Decimate Only, or Shrinkwrap Only
- **Customizable vertex color handling**: Auto, White Only, Bake All, or Transfer All modes
- **Automatic MSFS LOD value calculation** based on object size and MSFS 2024 documentation
- **Quick default LOD values**: One-click button to set standard values (4, 3, 2, 1)
- **Integration with MSFS Multi-Export addon** - automatically sets optimal LOD values and enables proper settings
- Conversion between MSFS and Blender materials
- **Enhanced vertex color baking**: 
  - **LOD00**: Uses pure white vertex colors (no texture baking)
  - **LOD02**: Uses converted Blender materials for baking
  - **LOD03**: Bakes vertex colors directly from LOD00 materials for high-quality results
  - Automatically sets "Color" as default attribute for LOD00-03
- Small object culling for higher LODs
- Manual LOD value override option
- **User-adjustable modifiers**: Shrinkwrap modifiers are left unapplied for manual fine-tuning

## LOD Generation Methods
The addon offers three generation methods via dropdown selection:

### Mixed Method (Recommended)
- **LOD01-02**: Uses Decimate method for gradual mesh simplification
- **LOD03**: Uses Shrinkwrap method for maximum performance optimization
- Best balance between quality and performance

### Decimate Only
- **All LODs**: Uses Decimate method for consistent mesh reduction
- Good for objects where shape preservation is critical
- Maintains original topology structure

### Shrinkwrap Only 
- **All LODs**: Uses Shrinkwrap method for aggressive optimization
- Creates cube-based proxy geometry for all LODs
- Maximum performance focus for distant objects

## Vertex Color Modes
Choose how vertex colors are handled across LODs:

### Automatic (Default)
- **LOD00**: Pure white vertex colors
- **LOD01**: Pure white vertex colors  
- **LOD02**: Baked from MSFS albedo textures
- **LOD03**: Baked from original LOD00 materials

### White Only
- **All LODs**: Pure white vertex colors
- Fastest generation, no texture baking

### Bake All
- **All LODs**: Bake textures to vertex colors
- Consistent appearance across all LODs
- Higher generation time

### Transfer All
- **LOD00**: Pure white vertex colors
- **LOD01-03**: Transfer vertex colors from LOD00
- Maintains consistent coloring (placeholder implementation)

## Usage
1. In the Scene Properties panel, find the "Level of Detail Collections" section.
2. Enable the LOD system by clicking the checkbox.
3. Use the "+" button to add LOD levels manually.
4. Adjust the "Small Object Threshold" and "Decimate Angle Increments" as needed.
5. **MSFS LOD Optimization**: 
   - Enable "Use Automatic LOD Calculation" (default) for smart LOD values based on object size
   - Or disable it and provide manual values in "Manual LOD Base Values" (comma-separated, e.g., "12,3,2,1")
   - Use "Set Default (4,3,2,1)" for quick standard LOD values
6. Click "Generate LODs (Decimate + Shrinkwrap)" to create LOD versions using:
   - **Decimate method** for LOD01 and LOD02 (mesh simplification)
   - **Shrinkwrap method** for LOD03 (creates low-poly proxy wrapped to original shape)
   - **Shrinkwrap modifiers are left unapplied** for manual adjustment and fine-tuning
   - Automatically sets MSFS LOD values based on object size
   - **Activates MSFS Multi-Export settings**: Enables "Grouped by Collections" and the first LOD group
   - **Sets "Color" as default vertex color attribute** for LOD00-03
   - **LOD00 gets pure white vertex colors** (no texture baking)
   - **LOD03 bakes vertex colors from LOD00 materials** for high-quality appearance matching the original
7. **Manual modifier adjustment**: After LOD generation, you can adjust the shrinkwrap modifier settings on LOD03 objects and apply them when satisfied
8. Alternatively, use "Calculate & Set LOD Values" to only calculate and set values without generating LODs.
9. Use the material conversion tools if working with MSFS materials.
10. Bake textures to vertex colors for the lowest LOD level if desired.

## MSFS LOD Value Calculation
The addon automatically calculates optimal LOD values based on:
- **Object size** (bounding box dimensions in meters)
- **MSFS 2024 documentation and real-world testing**:
  - Very small objects (< 0.5m): Quick disappearance (scaling factor 0.3)
  - Small objects (0.5-1m): Early culling (scaling factor 0.5)
  - Small-medium objects (1-2m): Moderate culling (scaling factor 0.7)
  - Medium objects (2-5m): Balanced approach (scaling factor 0.85)
  - Medium-large objects (5-10m): Base values (scaling factor 1.0)
  - Large objects (10-20m): Conservative culling (scaling factor 1.2)
  - Very large objects (20-50m): Extended visibility (scaling factor 1.5)
  - Massive objects (>50m): Maximum visibility (scaling factor 2.0)

The calculated values follow the correct MSFS pattern:
- **LOD0**: Highest value (most visible from distance)
- **LOD1-3**: Progressively decreasing values
- **Pattern**: LOD0 > LOD1 > LOD2 > LOD3 (e.g., 12.0, 3.0, 2.0, 1.0)
- **Important**: Higher values mean objects are visible from greater distances
- Values are based on screen percentage when LOD switches occur

## Mixed LOD Generation Approach
This addon uses an intelligent mixed approach for LOD generation:
- **LOD01-02**: Uses **Decimate** method for gradual mesh simplification while preserving detail
- **LOD03**: Uses **Shrinkwrap** method for maximum performance optimization

### Benefits of Shrinkwrap for Final LOD
- **Extreme optimization**: Creates very low-polygon proxy geometry using adaptive cube subdivision
- **Intelligent proxy creation**: Cube subdivision levels adapt to original mesh complexity (100-8000+ vertices)
- **Consistent shape**: Maintains the general silhouette of the original object
- **Performance focus**: Ideal for distant viewing where detail isn't critical
- **Automatic simplification**: No need to fine-tune decimation parameters for extreme reductions
- **Smart targeting**: Uses LOD02 as shrinkwrap target for better detail preservation
- **Optimized geometry**: Removes unnecessary bottom face from cube proxy for cleaner results
- **User-adjustable**: Shrinkwrap modifiers are left unapplied, allowing manual fine-tuning before application

### Cube-Based Shrinkwrap Details
The shrinkwrap method creates a subdivided cube proxy with optimizations:
- **Individual cube per mesh**: Each mesh gets its own perfectly positioned and scaled cube proxy
- **Precise positioning**: Cubes are positioned at the exact bounding box center of the target mesh
- **Optimal scaling**: Cubes are scaled to match the target mesh's bounding box dimensions (with 10% margin for complete coverage)
- **Target**: Uses LOD02 mesh instead of original LOD00 for more appropriate detail level
- **Bottom face removal**: Automatically deletes the bottom face of each cube (not typically visible)
- **Modifier preservation**: Shrinkwrap modifiers are left unapplied for user adjustment
- **Adaptive subdivision levels**:
  - **0-100 vertices**: Basic cube (8 vertices)
  - **101-500 vertices**: 1 subdivision level (26 vertices)  
  - **501-2000 vertices**: 2 subdivision levels (98 vertices)
  - **2001-8000 vertices**: 3 subdivision levels (386 vertices)
  - **8000+ vertices**: 4 subdivision levels (1538 vertices)

This adaptive approach ensures optimal balance between performance and shape approximation while using the already-simplified LOD02 as the shrinkwrap target. Each mesh receives its own custom-fitted cube proxy for the best possible LOD03 representation. Users can manually adjust shrinkwrap settings and apply the modifier when satisfied with the results.

## Tips
- Ensure your base model is in a collection named with the suffix "_LOD00".
- Use descriptive names for your LOD collections (e.g., "MyModel_LOD00", "MyModel_LOD01", etc.).
- **Important**: LOD collections must follow the exact naming pattern: `[BaseName]_LOD00`, `[BaseName]_LOD01`, `[BaseName]_LOD02`, `[BaseName]_LOD03`
- If you have a collection ending with an underscore (e.g., "Antenna_"), the addon will automatically handle it correctly
- Adjust the decimate angle increment to control the level of simplification between LODs.
- The small object threshold helps remove tiny details in higher LODs for better performance.
- **Make sure the MSFS Multi-Export addon is enabled** for automatic LOD value setting to work.
- Check the Blender Console (Window > Toggle System Console) for detailed debugging information during LOD generation.
- **LOD03 vertex color baking**: Bakes vertex colors directly from LOD00 materials for high-quality appearance matching the original.
- **Modifier adjustment**: After LOD generation, review and adjust the shrinkwrap modifier settings on LOD03 objects before applying them manually.

## Troubleshooting

### LOD Collections Not Showing in MSFS Multi-Export
If your LOD collections are not appearing correctly in the MSFS Multi-Export addon:

1. **Check Collection Naming**: Ensure collections follow the exact pattern: `[BaseName]_LOD00`, `[BaseName]_LOD01`, etc.
2. **Enable Console Logging**: Open Blender Console (Window > Toggle System Console) to see detailed debug information
3. **Verify Base Collection**: Make sure you have a collection ending with `_LOD00` as your base
4. **Check MSFS Multi-Export**: Verify the MSFS Multi-Export addon is enabled in Blender preferences
5. **Manual Setup**: Use the "+" button to manually add LOD collections to the list

### Collections with Trailing Underscores
If your original collection name ends with an underscore (e.g., "Antenna_LOD00"), the addon will automatically clean this up to avoid double underscores in generated names.

### Debug Information
The addon provides detailed console output showing:
- Base collection name and extracted base name
- LOD collection names being created/found
- Material usage for vertex color baking (LOD02: converted materials, LOD03: transferred from LOD02)
- MSFS Multi-Export integration status
- LOD values being set

## Author
Devinci

## License
MIT License

Copyright (c) 2024 Devinci

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Support
For issues and feature requests, please [open an issue on GitHub](https://github.com/yourusername/your-repo-name/issues).