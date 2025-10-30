import arcpy

#define parameters here
project_gdb = r"C:\gully_road_length\gully_road_length_project\gully_road_length.gdb"
output_fc_name = "test"
culverts_fc = r"C:\gully_road_length\gully_road_length_data\monkton_data.gdb\Monkton_Culvpt"
roads_fc = r"C:\gully_road_length\gully_road_length_data\roads_with_elev.gdb\Monkton_Rds_Seg_Elevation"

culvert_elevation_field = "elevation"
road_hp_elevation_field = "MaxEl"
road_culvert_elevation_field = "Culv_El_Max"
road_intersection_elevation_field = "Inter_El"


#set environment
arcpy.env.workspace = project_gdb
arcpy.env.overwriteOutput = True

#import data and add corresponding feature layers
culverts = culverts_fc
arcpy.management.MakeFeatureLayer(culverts, "culverts_lyr")
roads = roads_fc
arcpy.management.MakeFeatureLayer(roads, "roads_lyr")
print("Data Imported!")

#create feature class that all merged roads will be appended to
arcpy.management.CreateFeatureclass(arcpy.env.workspace, output_fc_name, "POLYLINE", spatial_reference = roads)

#create counter to track progress of script
counter = 1

#iterate through all culverts
with arcpy.da.SearchCursor(culverts, ["SHAPE@", culvert_elevation_field]) as iterate_cursor:
    for row in iterate_cursor:
        print(f"Beginning iteration {counter}")
        target_culvert_obj = row[0]
        culvert_elev = row[1]
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, "target_culvert", "POINT", culverts)
        with arcpy.da.InsertCursor("target_culvert", ["SHAPE@", culvert_elevation_field]) as create_target_culvert_cursor:
            create_target_culvert_cursor.insertRow([target_culvert_obj, culvert_elev])

        target_culvert = "target_culvert"
        arcpy.management.MakeFeatureLayer(target_culvert, "target_culvert_lyr")

        #select target roads
        arcpy.management.SelectLayerByLocation("roads_lyr", "INTERSECT", "target_culvert_lyr")
        arcpy.management.CopyFeatures("roads_lyr", "target_roads")
        target_roads = "target_roads"
        arcpy.management.MakeFeatureLayer(target_roads, "target_roads_lyr")


        #get elevation of target culvert
        with arcpy.da.SearchCursor(target_culvert, ["elevation"]) as culvert_cursor:
            for row in culvert_cursor:
                culvert_elevation = row[0]
                
        #create blank list to be populated by geometry objects
        higher = []

        #loop through all of the associated target road polylines
        #add to higher list if elevation is higher than that of culvert
        with arcpy.da.SearchCursor(target_roads, [road_hp_elevation_field, road_culvert_elevation_field, road_intersection_elevation_field, "SHAPE@"]) as road_cursor:
            for row in road_cursor:
                feature_elevation = 0
                if row[0] == None and row[2] == None: #culvert and culvert
                    feature_elevation = row[1]
                    print("Culvert")
                    print(f"Culvert Elevation: {culvert_elevation} Feature Elevation: {feature_elevation}")
                elif row[0] == None and row[2] != None: #culvert and intersection
                    feature_elevation = row[2]
                    print("Intersection")
                    print(f"Culvert Elevation: {culvert_elevation} Feature Elevation: {feature_elevation}")
                else:
                    feature_elevation = row[0] #culvert and road high point
                    print("Road High Point")
                    print(f"Culvert Elevation: {culvert_elevation} Feature Elevation: {feature_elevation}")
                if round(feature_elevation, 2) > round(culvert_elevation, 2):
                    higher.append(row[3])
                                   
        #loop through higher list and combine them into one feature class
        #append that feature class to the merged_roads feature class
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, "all_higher_roads", "POLYLINE", roads)
        for i in range(len(higher)):
            with arcpy.da.InsertCursor("all_higher_roads", ["SHAPE@"]) as cursor:
                cursor.insertRow([higher[i]])                         
        arcpy.management.Dissolve("all_higher_roads", "all_higher_roads_dissolved", ["OBJECTID"])
        arcpy.management.Append("all_higher_roads_dissolved", "merged_roads")

        #add to counter
        counter += 1
        
    

                
                           
