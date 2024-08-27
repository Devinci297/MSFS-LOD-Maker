# MSFS LOD Maker Addon

## Overview
MSFS LOD system for collections in Blender 3.6 & above, with LOD generation. It allows for easy management and generation of LODs, with features for decimation, material conversion, and texture baking.

## Installation
1. Download the addon ZIP file.
2. In Blender, go to Edit > Preferences > Add-ons.
3. Click "Install" and select the downloaded ZIP file.
4. Enable the addon by checking the box next to "Scene: Lodify Collections".

## Features
- Automatic LOD setup for collections
- LOD generation using decimation
- Conversion between MSFS and Blender materials
- Texture baking to vertex colors
- Small object culling for higher LODs

## Usage
1. In the Scene Properties panel, find the "Level of Detail Collections" section.
2. Enable the LOD system by clicking the checkbox.
3. Use the "+" button to add LOD levels, or use "Auto Setup" to detect existing LOD collections.
4. Adjust the "Small Object Threshold" and "Decimate Angle Increments" as needed.
5. Click "Generate LODs (Decimate)" to create LOD versions of your models.
6. Use the material conversion tools if working with MSFS materials.
7. Bake textures to vertex colors for the lowest LOD level if desired.

## Tips
- Ensure your base model is in a collection named with the suffix "_LOD00".
- Use descriptive names for your LOD collections (e.g., "MyModel_LOD00", "MyModel_LOD01", etc.).
- Adjust the decimate angle increment to control the level of simplification between LODs.
- The small object threshold helps remove tiny details in higher LODs for better performance.

## Author
Devinci

## License
[Your chosen license]

## Support
For issues and feature requests, please [open an issue on GitHub](https://github.com/yourusername/your-repo-name/issues).
