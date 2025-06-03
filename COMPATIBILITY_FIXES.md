# MSFS LOD Maker - Compatibility Fixes & Updates

## Recent Fixes & Improvements

### Version 1.2.0 - Enhanced LOD Generation
- **Mixed LOD Generation**: Implemented intelligent LOD generation strategy
  - LOD01-02: Uses Decimate method for gradual mesh simplification
  - LOD03: Uses Shrinkwrap method for maximum performance optimization
- **Automatic MSFS LOD Value Calculation**: Smart calculation based on object size and MSFS 2024 documentation
- **Quick Default Values**: One-click button to set standard LOD values (4, 3, 2, 1)
- **MSFS Multi-Export Integration**: Automatically enables proper settings and LOD groups

### Vertex Color Baking Enhancements
- **LOD00**: Now uses pure white vertex colors (no texture baking needed)
- **LOD02**: Uses converted Blender materials for proper texture baking
- **LOD03**: Directly transfers vertex colors from LOD02 to ensure identical appearance
- **Automatic Color Attribute**: Sets "Color" as default attribute for LOD00-03

### Shrinkwrap Method Implementation
- **Adaptive Cube Subdivision**: Subdivision levels adapt to mesh complexity
- **Smart Targeting**: Uses LOD02 as shrinkwrap target instead of LOD00
- **Optimized Geometry**: Removes unnecessary bottom face from cube proxy
- **Performance Focused**: Creates very low-polygon proxy geometry

### MSFS Multi-Export Integration
- **Automatic Settings**: Enables "Grouped by Collections" and first LOD group
- **LOD Value Setting**: Automatically sets calculated LOD values in MSFS Multi-Export properties
- **Collection Detection**: Improved detection and handling of LOD collections

### Bug Fixes
- Fixed collection naming issues with trailing underscores
- Improved LOD collection detection algorithm
- Better error handling for missing MSFS Multi-Export addon
- Enhanced console logging for debugging

### Compatibility
- **Blender**: 3.6+ (tested up to 4.0)
- **MSFS Multi-Export**: Compatible with latest versions
- **MSFS 2024**: Optimized LOD calculations for new simulator version

### Known Issues
- Some complex materials may need manual adjustment after conversion
- Very large scenes may experience longer processing times during LOD generation
- Shrinkwrap method works best with closed meshes (objects without holes)

### Future Improvements
- Support for custom LOD generation algorithms
- Enhanced material conversion for complex shader setups
- Integration with additional MSFS development tools
- Performance optimizations for large scenes 