import arcpy

#set parameters
workspace = r"C:\gully_road_length\gully_road_length_data\data_for_prep.gdb"
culvert_fc = r"C:\gully_road_length\gully_road_length_data\data_for_prep.gdb\culverts"
roads_fc = r"C:\gully_road_length\gully_road_length_data\data_for_prep.gdb\dissolved_roads"
dem = r"C:\gully_road_length\gully_road_length_data\data_for_prep.gdb\monkton_dem" #needs to be a gdb raster for some reason
town_name = "monkton"

#set environment
arcpy.env.workspace = workspace
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

#snap the culverts to the road
arcpy.edit.Snap(culvert_fc, f"{roads_fc} EDGE '50 Meters'")
#extract the elevation of the culvert points from the DEM
arcpy.sa.ExtractValuesToPoints(culvert_fc, dem, f"{town_name}_culverts_with_elevation", "NONE", "VALUE_ONLY")
#split roads at culverts and intersections
arcpy.management.SplitLineAtPoint(roads_fc, f"{town_name}_culverts_with_elevation", f"{town_name}_roads_split_by_culvert", "50 Meters")

##generate road high point points
#generate maxium raster
road_max_raster = arcpy.sa.ZonalStatistics(f"{town_name}_roads_split_by_culvert", "OBJECTID", dem, "MAXIMUM")
road_max_raster.save("road_max_raster")
#generate maximum points raster
road_max_points_raster = arcpy.sa.Con(arcpy.Raster(dem) == arcpy.Raster(road_max_raster), arcpy.Raster(dem))
road_max_points_raster.save("road_max_points_raster")
#convert maximum points raster to points feature class and snap to split roads
arcpy.conversion.RasterToPoint("road_max_points_raster", "all_road_high_points")
arcpy.edit.Snap("all_road_high_points", f"{roads_fc} EDGE '50 Meters'")

#make new layer of highpoints that are 4m away from culverts
selection = arcpy.management.SelectLayerByLocation("all_road_high_points", "WITHIN_A_DISTANCE", "monkton_culverts_with_elevation", "4 Meters", "NEW_SELECTION", "INVERT")
arcpy.management.CopyFeatures(selection, f"{town_name}_high_points")

#create intersection points
arcpy.analysis.Intersect(f"{town_name}_roads_split_by_culvert", "all_intersections", "ONLY_FID", output_type = "POINT")
selection = arcpy.management.SelectLayerByLocation("all_intersections", "WITHIN", f"{town_name}_culverts_with_elevation", None, "NEW_SELECTION", "INVERT")
arcpy.management.CopyFeatures(selection, "target_intersections")

#extract intersection elevation to intersection points
arcpy.management.MultipartToSinglepart("target_intersections", "target_intersections_sp")
arcpy.sa.ExtractValuesToPoints("target_intersections_sp", dem, f"{town_name}_intersections", "NONE", "VALUE_ONLY")

#rename elevation fields
arcpy.management.AlterField(f"{town_name}_culverts_with_elevation", "RASTERVALU", "culv_el", "culv_el")
arcpy.management.AlterField(f"{town_name}_intersections", "RASTERVALU", "inter_el", "inter_el")
arcpy.management.AlterField(f"{town_name}_high_points", "grid_code", "hp_el", "hp_el")



#delete intermediate datasets
arcpy.management.Delete(["target_intersections", "target_intersections_sp", "road_max_raster", "split_roads_no_elevation",
                          "road_max_points_raster", "all_intersections", "all_road_high_points"])


    

                
                           
