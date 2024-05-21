import os
import subprocess
import sys

# Get the name from the command-line arguments
if len(sys.argv) < 2:
    print("Please provide a name as a command-line argument.")
    sys.exit(1)
name = sys.argv[1]
optional_extra_names = sys.argv[2:]

# Directories to search
dirs = ["object_model\\object_classes", "object_model\\models", "object_model\\interface", "dbs_classes"]

# Find all Python files that include "measure" in their names
files = []
for dir in dirs:
    for root, _, filenames in os.walk(dir):
        for filename in filenames:
            if name in filename and filename.endswith('.py') or name in root or any(extra_name in filename for extra_name in optional_extra_names):
                files.append(os.path.join(root, filename))

# Add the generic files
files.append("object_model/object_classes/flood_adapt_object.py")
files.append("object_model/interface/flood_adapt_object.py")
files.append("dbs_classes/dbs_object.py")
files.append("dbs_classes/dbs_interface.py")

# Run pyreverse with the name included in the title
subprocess.run(["pyreverse", "-o", "dot", "-p", name] + files)

# Add the connection to the DOT file
dot_file_name = f"classes_{name}.dot"
with open(dot_file_name, "r") as dot_file:
    lines = dot_file.readlines()

# Modify the lines
for i, line in enumerate(lines):
    if 'flood_adapt.object_model.object_classes.flood_adapt_object.FAObject' in line:
        line = line.replace('attrs<br ALIGN="LEFT"/>attrs', 'attrs', 1)
    elif 'flood_adapt.object_model.interface.flood_adapt_object.IFAObject' in line:
        line = line.replace('attrs<br ALIGN="LEFT"/>', '<I>attrs</I><br ALIGN="LEFT"/>', 1)
    
    if "interface" in line and "->" not in line:
        line = line.replace('label=<{', 'label=<{&lt;&lt;I&gt;&gt;')
         
    if "interface" in line and "->" in line:	
        line = line.replace('];', ', style="dashed"];')

    if "Dbs" in line:
        line = line.replace('[color="black",', '[color="blue",')

    lines[i] = line


if name == "measure":    
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.measure_factory.MeasureFactory" -> "flood_adapt.dbs_classes.dbs_measure.DbsMeasure" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.measure_factory.HazardMeasureFactory" -> "flood_adapt.object_model.object_classes.measure.measure_factory.MeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.measure_factory.ImpactMeasureFactory" -> "flood_adapt.object_model.object_classes.measure.measure_factory.MeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.impact_measure.buyout.Buyout" -> "flood_adapt.object_model.object_classes.measure.measure_factory.ImpactMeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.impact_measure.elevate.Elevate" -> "flood_adapt.object_model.object_classes.measure.measure_factory.ImpactMeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.impact_measure.floodproof.FloodProof" -> "flood_adapt.object_model.object_classes.measure.measure_factory.ImpactMeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.hazard_measure.floodwall.FloodWall" -> "flood_adapt.object_model.object_classes.measure.measure_factory.HazardMeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.hazard_measure.green_infrastructure.GreenInfrastructure" -> "flood_adapt.object_model.object_classes.measure.measure_factory.HazardMeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')
    lines.insert(-1, '"flood_adapt.object_model.object_classes.measure.hazard_measure.pump.Pump" -> "flood_adapt.object_model.object_classes.measure.measure_factory.HazardMeasureFactory" [arrowhead="diamond", arrowtail="none", style="solid"];\n')

    forbidden_keywords = ["factory", "type", 'dbs']
    lvl_1_keywords = ['impact', 'hazard']
    lvl_2_keywords = ['buyout', 'elevate', 'floodwall', 'floodproof', 'greeninfrastructure', 'pump']
    for i, line in enumerate(lines):
        if "->" in line:
            left_side = line.split('->')[0].lower()
            if not any(forbidden_keyword in left_side for forbidden_keyword in (forbidden_keywords + lvl_1_keywords + lvl_2_keywords)):
                line = line.replace('[arrowhead', '[color="red", arrowhead')
            if any(word in left_side for word in lvl_1_keywords) and not any(forbidden_keyword in left_side for forbidden_keyword in (forbidden_keywords + lvl_2_keywords)):
                line = line.replace('[arrowhead', '[color="purple", arrowhead')
            if any(word in left_side for word in lvl_2_keywords) and not any(forbidden_keyword in left_side for forbidden_keyword in forbidden_keywords):
                line = line.replace('[arrowhead', '[color="cadetblue2", arrowhead')
        else:
            temp_line = line.split('" [color')[0].lower()
            if not any(forbidden_keyword in temp_line for forbidden_keyword in (forbidden_keywords + lvl_1_keywords + lvl_2_keywords)):
                line = line.replace('[color="black", ', '[color="red", ')
            if any(word in temp_line for word in lvl_1_keywords) and not any(forbidden_keyword in temp_line for forbidden_keyword in (forbidden_keywords + lvl_2_keywords)):
                line = line.replace('[color="black", ', '[color="purple", ')
            if any(word in temp_line for word in lvl_2_keywords) and not any(forbidden_keyword in temp_line for forbidden_keyword in forbidden_keywords):
                line = line.replace('[color="black", ', '[color="cadetblue2", ')

        lines[i] = line

# Write the lines back to the file
with open(dot_file_name, "w") as dot_file:
    dot_file.writelines(lines)

# Generate the PNG from the DOT file
subprocess.run(["dot", "-Tpng", dot_file_name, "-o", f"classes_{name}.png"])

# Remove the DOT file
os.remove(dot_file_name)
os.remove(dot_file_name.replace("classes", "packages"))