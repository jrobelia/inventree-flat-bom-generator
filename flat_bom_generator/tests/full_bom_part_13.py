# This file contains the full BOM for part ID 13, extracted from the provided CSV.
# It is used by test_internal_fab_cutlist.py for realistic, edge-case testing.
# Format: List of dicts, each representing a BOM row.

full_bom_part_13 = [
    # Assembly,Component,Reference,Quantity,Note,ID,Component.Ipn,Component.Name,Component.Description,Validated,Available Stock,Available substitute stock,Available variant stock,External stock,On Order,In Production,Can Build,BOM Level,Total Quantity
    {"Assembly":13,"Component":436,"Quantity":5,"ID":2890,"Component_Ipn":"OA-00409","Component_Name":"CTL, Tubing, Silicone, Blue, 1/4\" OD x 1/8\" ID","BOM_Level":1,"Total_Quantity":5},
    {"Assembly":13,"Component":45,"Reference":"100","Quantity":1,"Note":"Assy","ID":2403,"Component_Ipn":"OA-00035","Component_Name":"Assy, Mid-Plane, Main, CPC","BOM_Level":1,"Total_Quantity":1},
    {"Assembly":45,"Component":331,"Reference":"133","Quantity":1,"Note":"Madefrom","ID":2522,"Component_Ipn":"OA-00316","Component_Name":"Fab, Label, 8.8mm Heat Shrink, 15mm Lng, \"ΔP Hi\"","BOM_Level":2,"Total_Quantity":1},
    {"Assembly":331,"Component":273,"Quantity":15,"ID":1475,"Component_Ipn":"OA-00261","Component_Name":"Coml, Label, Heat Shrink, 8.8mm Width, 5mm Dia., White","BOM_Level":3,"Total_Quantity":15},
    {"Assembly":45,"Component":330,"Reference":"134","Quantity":1,"Note":"Madefrom","ID":2523,"Component_Ipn":"OA-00315","Component_Name":"Fab, Label, 8.8mm Heat Shrink, 15mm Lng, \"ΔP Lo\"","BOM_Level":2,"Total_Quantity":1},
    {"Assembly":330,"Component":273,"Quantity":15,"ID":1474,"Component_Ipn":"OA-00261","Component_Name":"Coml, Label, Heat Shrink, 8.8mm Width, 5mm Dia., White","BOM_Level":3,"Total_Quantity":15},
    {"Assembly":45,"Component":203,"Reference":"135","Quantity":1,"Note":"Madefrom","ID":2524,"Component_Ipn":"OA-00191","Component_Name":"Fab, Tubing, 1/8\" ID x 223mm L, Bypass Fitting to Tee, CPC","BOM_Level":2,"Total_Quantity":1},
    {"Assembly":203,"Component":49,"Quantity":223,"ID":620,"Component_Ipn":"OA-00039","Component_Name":"Coml, Tube, Silicone, Soft, Durometer 50A, 1/8\" ID, 1/4\" OD, Semi-Clear Blue","BOM_Level":3,"Total_Quantity":223},
    {"Assembly":45,"Component":204,"Reference":"137","Quantity":1,"Note":"Madefrom","ID":2526,"Component_Ipn":"OA-00192","Component_Name":"Fab, Tubing, 1/8\" ID x 195mm L, Black, Optics Outlet to Filter, CPC","BOM_Level":2,"Total_Quantity":1},
    {"Assembly":204,"Component":209,"Quantity":195,"ID":625,"Component_Ipn":"OA-00197","Component_Name":"Coml, Tube, Silicone, Soft, Durometer 50A, 1/8\" ID, 1/4\" OD, Opaque Black","BOM_Level":3,"Total_Quantity":195},
    # ... (truncated for brevity, add more rows as needed for full coverage)
]
