# Python Program Data Structure Visualizer (3D)

An interactive 3D visualization tool that analyzes Python source code and displays its data structures, classes, functions, variables, imports, and relationships as an interactive graph. Supports single files or entire project directories.

![3D Visualization Example](images/visualization_example.png)
*Interactive 3D graph showing program structure with color-coded nodes*

## ✨ Features

### Core Analysis
- **Multi-File Support**: Analyze entire project directories recursively
- **AST-based Analysis**: Parses Python files using the Abstract Syntax Tree (AST) to extract program structure
- **Import Tracking**: Visualizes module dependencies and import relationships
- **Class Inheritance**: Shows parent-child class relationships with special edges
- **Type Detection**: Automatically identifies and color-codes different data types
- **Metadata Extraction**: Captures docstrings, function parameters, and signatures

### Interactive Visualization
- **3D Interactive Graph**: Renders using Plotly with zoom, rotate, and pan controls
- **Interactive Filtering**: Show/hide specific node types (modules, classes, functions, variables, imports)
- **Search & Highlight**: Search for specific nodes and highlight them in the graph
- **Click for Details**: Click nodes to see docstrings, parameters, and metadata
- **Edge Customization**: RGB sliders to customize edge colors and opacity
- **Collapsible Controls**: Clean UI with collapsible control panel

### Relationship Mapping
- **Module containment**: Files contain classes, functions, variables
- **Class inheritance**: Parent-child relationships between classes
- **Method binding**: Classes contain their methods
- **Function calls**: Tracks function invocations
- **Import dependencies**: Shows which modules import what
- **Data structure hierarchy**: Lists, dicts, sets with their elements

## Screenshots

### Main Visualization
![Main Graph View](images/main_view.png)
*3D graph showing classes (red), functions (blue), and data structures*

### Interactive Controls
![Legend and Controls](images/controls.png)
*Legend showing element types and edge customization slider*

### Relationship Details
![Hover Information](images/hover_details.png)
*Hover over edges to see relationship types and connections*

## Installation

Install required dependencies using `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Or install manually:

```powershell
pip install plotly networkx
```

## Usage

### Basic Usage

```powershell
# Analyze a single file
python visualize_structures_3d.py <path_to_file> [output.html]

# Analyze entire directory (recursive)
python visualize_structures_3d.py <path_to_directory> [output.html]
```

### Examples

**Analyze a single Python file:**
```powershell
python visualize_structures_3d.py "script.py" "output.html"
```

**Analyze entire project directory:**
```powershell
python visualize_structures_3d.py "src/" "project_visualization.html"
```

**Analyze current directory:**
```powershell
python visualize_structures_3d.py "." "viz.html"
```

## Interactive Controls

### Control Panel (Left Side)

The collapsible control panel includes:

#### **Filter by Type**
Toggle visibility of node types:
- ☑️ Modules
- ☑️ Classes  
- ☑️ Functions
- ☑️ Variables
- ☑️ Imports

#### **Search**
- Type to search for specific nodes
- Matching nodes are highlighted (larger size)
- Case-insensitive search

#### **Edge Styling**
- **Red Slider**: Control red color component (0-255)
- **Green Slider**: Control green color component (0-255)
- **Blue Slider**: Control blue color component (0-255)
- **Opacity Slider**: Control edge transparency (0.0-1.0)

### Information Panel (Right Side)

Click any node to see:
- **Node name and type**
- **Docstring** (for classes/functions)
- **Parameters** (for functions/methods)
- **Module** (parent file)
- **Base classes** (for classes with inheritance)

### Graph Interactions

- **Rotate**: Click and drag
- **Zoom**: Scroll wheel or pinch
- **Pan**: Right-click and drag
- **Toggle Legend**: Click legend items to show/hide element types
- **Collapse Panel**: Click arrow (◀/▶) to hide/show control panel


## Color Coding

The visualization uses distinct colors for different element types:

| Element Type | Color |
|-------------|-------|
| **module** | Black (0,0,0) |
| **class** | Red (255,0,0) |
| **function** | Dark Blue (0,0,255) |
| **import** | Green (100,200,100) |
| **list** | Blue (0,150,255) |
| **dict** | Orange (255,140,0) |
| **set** | Green (50,200,50) |
| **tuple** | Magenta (200,0,200) |
| **int** | Gray (200,200,200) |
| **str** | Pink (255,105,180) |
| **float** | Light Blue (180,180,255) |
| **bool** | Gray (150,150,150) |
| **unknown** | Gray (120,120,120) |

## What Gets Visualized

### Nodes (Elements)
- **Modules**: Python files (.py)
- **Classes**: Class definitions with inheritance tracking
- **Functions/Methods**: Function definitions with parameters
- **Variables**: Variable assignments with type inference
- **Imports**: External modules and packages
- **Data Structures**: Lists, dictionaries, sets, tuples and their elements

### Edges (Relationships)
- **contains**: Module contains classes/functions/variables
- **imports**: Module imports external packages
- **inherits**: Class inherits from parent class
- **method**: Class contains methods
- **calls**: Function invocations
- **arg**: Arguments passed to functions
- **dict-item**: Dictionary key-value pairs
- **seq-item**: List/set/tuple elements

## Advanced Features

### Multi-File Analysis

When analyzing directories, the tool:
- Recursively scans for all `.py` files
- Creates module-qualified node names (e.g., `module.py::ClassName`)
- Links imports across files
- Tracks inheritance across modules
- Shows project-wide dependencies

### Metadata Extraction

For each code element, the tool captures:
- **Docstrings**: First 100 characters
- **Function parameters**: Argument names
- **Class base classes**: Inheritance chain
- **File paths**: Source module location

## Use Cases

✅ **Understanding unfamiliar codebases** - Visualize structure before diving into code  
✅ **Refactoring planning** - See dependencies before making changes  
✅ **Documentation** - Generate visual project overviews  
✅ **Code review** - Understand architectural decisions  
✅ **Teaching** - Show beginners how code is organized  
✅ **Debugging** - Trace relationships and dependencies

## Customization

### Modify Edge Appearance

Use the interactive sliders in the control panel, or edit default values in code.

### Add Custom Types

Add to the `TYPE_COLOR` dictionary at the top of the file:

```python
TYPE_COLOR = {
    "list": "rgb(0,150,255)",
    "your_custom_type": "rgb(R,G,B)",  # Add custom types here
    ...
}
```

## Limitations

- Only detects literal data structures (defined directly in code)
- Type inference is basic and may not capture all complex types
- Does not analyze runtime behavior, only static code structure
- Works best with well-structured Python code

## Technical Details

- **Parser**: Python's built-in `ast` module
- **Graph Library**: NetworkX for graph construction
- **Layout Algorithm**: Spring layout (force-directed) with 3D extension
- **Visualization**: Plotly for interactive 3D rendering
- **Output Format**: Self-contained HTML file with embedded JavaScript

## License

Free to use for educational and personal projects.

## Author

Created as a visualization tool for analyzing Python program structure in 3D space.
