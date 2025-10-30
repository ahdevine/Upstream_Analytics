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
arcpy.management.SplitLineAtPoint(roads_fc, f"{town_name}_culverts_with_elevation", "split_roads_no_elev", "50 Meters")


##generate road high point points
#generate maxium raster
road_max_raster = arcpy.sa.ZonalStatistics("split_roads_no_elev", "OBJECTID", dem, "MAXIMUM")
road_max_raster.save("road_max_raster")
#generate maximum points raster
road_max_points_raster = arcpy.sa.Con(arcpy.Raster(dem) == arcpy.Raster(road_max_raster), arcpy.Raster(dem))
road_max_points_raster.save("road_max_points_raster")
#convert maximum points raster to points feature class and snap to split roads
arcpy.conversion.RasterToPoint("road_max_points_raster", "all_road_high_points")
arcpy.edit.Snap("all_road_high_points", "'split_roads_no_elev' EDGE '50 Meters'")

#make new layer of highpoints that are 4m away from culverts
selection = arcpy.management.SelectLayerByLocation("all_road_high_points", "WITHIN_A_DISTANCE", "monkton_culverts_with_elevation", "4 Meters", "NEW_SELECTION", "INVERT")
arcpy.management.CopyFeatures(selection, f"{town_name}_high_points")


##join road highpoint data to split roads
#configure field mapping
hp_fms = arcpy.FieldMappings()
hp_fm_elev = arcpy.FieldMap()
hp_fm_elev.addInputField(f"{town_name}_high_points", "grid_code")
hp_fm_elev.mergeRule = "Max"
hp_fms.addFieldMap(hp_fm_elev)

#do the join
arcpy.analysis.SpatialJoin(
    target_features = "split_roads_no_elev",
    join_features = f"{town_name}_high_points",
    out_feature_class = "split_roads_elev_hp",
    join_operation = "JOIN_ONE_TO_ONE",
    join_type = "KEEP_ALL",
    field_mapping = hp_fms,
    match_option = "INTERSECT",
    search_radius = "50 Meters")

#rename the joined field
arcpy.management.AlterField("split_roads_elev_hp", "grid_code", "hp_elev", "hp_elev")
arcpy.management.DeleteField("split_roads_elev_hp", ["Join_Count", "TARGET_FID"])


##join culvert maxel data to split roads
#configure field mapping
cul_max_fms = arcpy.FieldMappings()
cul_max_elev = arcpy.FieldMap()
cul_max_elev.addInputField(f"{town_name}_culverts_with_elevation", "RASTERVALU")
cul_max_elev.mergeRule = "Max"
cul_max_fms.addFieldMap(cul_max_elev)

#do the join
arcpy.analysis.SpatialJoin(
    target_features = "split_roads_no_elev",
    join_features = f"{town_name}_culverts_with_elevation",
    out_feature_class = "split_roads_elev_culv",
    join_operation = "JOIN_ONE_TO_ONE",
    join_type = "KEEP_ALL",
    field_mapping = cul_max_fms,
    match_option = "INTERSECT",
    search_radius = "50 Meters")

#rename the joined field
arcpy.management.AlterField("split_roads_elev_culv", "RASTERVALU", "max_culv_el", "max_culv_el")
arcpy.management.DeleteField("split_roads_elev_culv", ["Join_Count", "TARGET_FID"])

##merge the hp and culv road datasets to get them all into one fc
#do join
split_roads_elev_no_intersection = arcpy.management.AddJoin("split_roads_elev_culv", "OBJECTID", "split_roads_elev_hp", "OBJECTID")
arcpy.management.CopyFeatures(split_roads_elev_no_intersection, "split_roads_elev_no_intersection")

#create intersection points
arcpy.analysis.Intersect("split_roads_elev_no_intersection", "all_intersections", "ONLY_FID", output_type = "POINT")
selection = arcpy.management.SelectLayerByLocation("all_intersections", "WITHIN", "monkton_culverts_with_elevation", None, "NEW_SELECTION", "INVERT")
arcpy.management.CopyFeatures(selection, "target_intersections")

#split new road fc by road hp
arcpy.management.SplitLineAtPoint("split_roads_elev_no_intersection", f"{town_name}_high_points", "roads_split_by_hp", "50 Meters")

#extract intersection elevation to intersection points
arcpy.management.MultipartToSinglepart("target_intersections", "target_intersections_sp")
arcpy.sa.ExtractValuesToPoints("target_intersections_sp", dem, f"{town_name}_intersections", "NONE", "VALUE_ONLY")

#intersection point join with split road fc
town_split_roads_elev = arcpy.management.AddJoin("roads_split_by_hp", "split_roads_elev_hp_OBJECTID",
                         f"{town_name}_intersections", "FID_split_roads_elev_no_intersection")
arcpy.management.CopyFeatures(town_split_roads_elev, f"{town_name}_split_roads_elev")

#clean up field names in final roads fc
arcpy.management.AlterField(f"{town_name}_split_roads_elev", "monkton_intersections_RASTERVALU", "inter_elev", "inter_elev")
arcpy.management.AlterField(f"{town_name}_split_roads_elev", "roads_split_by_hp_split_roads_elev_hp_hp_elev", "hp_elev", "hp_elev")
arcpy.management.AlterField(f"{town_name}_split_roads_elev", "roads_split_by_hp_split_roads_elev_culv_max_culv_el", "culv_elev", "culv_elev")
arcpy.management.DeleteField(f"{town_name}_split_roads_elev", ["roads_split_by_hp_split_roads_elev_hp_OBJECTID",
                                                               "monkton_intersections_OBJECTID",
                                                               "monkton_intersections_FID_split_roads_elev_no_intersection",
                                                               "monkton_intersections_ORIG_FID"]
                             )

#fix non-intersection points having intersection values
selection = arcpy.management.SelectLayerByLocation(f"{town_name}_split_roads_elev", "INTERSECT", f"{town_name}_intersections", "50 Meters", "NEW_SELECTION", "INVERT")
arcpy.management.CalculateField(selection, "inter_elev", -999)

#fix non-highpoint points having highpoint values
selection = arcpy.management.SelectLayerByLocation(f"{town_name}_split_roads_elev", "INTERSECT", f"{town_name}_high_points", "1 Meters", "NEW_SELECTION", "INVERT")
arcpy.management.CalculateField(selection, "hp_elev", -999)

#delete intermediate data
arcpy.management.Delete(["road_max_raster", "road_max_points_raster", "all_road_high_points", "split_roads_elev_hp", "split_roads_elev_culv",
                         "split_roads_no_elevation", "target_intersections_sp", "target_intersections", "split_roads_no_elev",
                         "split_roads_elev_no_intersection", "roads_split_by_hp", "all_intersections", f"{town_name}_intersection"])
    

                
                           
