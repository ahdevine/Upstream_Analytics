import arcpy

#set environment
arcpy.env.workspace = r"\\zoofiles.uvm.edu\jcampb16\gully_road_length\gully_road_length_project\gully_road_length.gdb"
arcpy.env.overwriteOutput = True

#import data and add corresponding feature layers
culverts = "sample_culverts"
#arcpy.management.MakeFeatureLayer(culverts, "culverts_lyr")
roads = "sample_roads"
arcpy.management.MakeFeatureLayer(roads, "roads_lyr")
road_highpoints = "sample_road_highpoints"
arcpy.management.MakeFeatureLayer(road_highpoints, "road_highpoints_lyr")
print("Data Imported!")

#create feature class that all merged roads will be appended to
arcpy.management.CreateFeatureclass(arcpy.env.workspace, "merged_roads", "POLYLINE", spatial_reference = roads)

#iterate through all culverts
with arcpy.da.SearchCursor(culverts, ["SHAPE@", "RASTERVALU"]) as iterate_cursor:
    for row in iterate_cursor:
        print("Beginning next iteration")
        target_culvert_obj = row[0]
        culvert_elev = row[1]
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, "target_culvert", "POINT", culverts)
        with arcpy.da.InsertCursor("target_culvert", ["SHAPE@", "RASTERVALU"]) as create_target_culvert_cursor:
            create_target_culvert_cursor.insertRow([target_culvert_obj, culvert_elev])

        target_culvert = "target_culvert"
        arcpy.management.MakeFeatureLayer(target_culvert, "target_culvert_lyr")

        #select target roads
        arcpy.management.SelectLayerByLocation("roads_lyr", "INTERSECT", "target_culvert_lyr")
        arcpy.management.CopyFeatures("roads_lyr", "target_roads")
        target_roads = "target_roads"
        arcpy.management.MakeFeatureLayer(target_roads, "target_roads_lyr")

        #select target road highpoints
        #also select the other culverts that intersect 
        arcpy.management.SelectLayerByLocation("road_highpoints_lyr", "INTERSECT", "target_roads_lyr")
        arcpy.management.CopyFeatures("road_highpoints_lyr", "target_road_highpoints")
        target_road_highpoints = "target_road_highpoints"
        print("Selection complete!")

        #get elevation of target culvert
        with arcpy.da.SearchCursor(target_culvert, ["RASTERVALU"]) as culvert_cursor:
            for row in culvert_cursor:
                culvert_elevation = row[0]
                print(f"Culvert elevation: {culvert_elevation} m")
                
        #create feature class for merged roads to be appended to
        

        #create blank list to be populated by geometry objects
        higher = []

        #associate the elevation of the points with the target roads


        #loop through all of the associated target road polylines
        #add to higher list if elevation is higher than that of culvert
        #CHANGE "RASTERVALU" TO ELEVATION COLUMN
        with arcpy.da.SearchCursor(target_roads, ["RASTERVALU", "SHAPE@"]) as road_cursor:
            for row in road_cursor:
                if row[0] > culvert_elevation:
                    higher.append(row[1])
                                   
        #loop through higher list and combine them into one feature class
        #append that feature class to the merged_roads feature class
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, "all_higher_roads", "POLYLINE", roads)
        for i in range(len(higher)):
            with arcpy.da.InsertCursor("all_higher_roads", ["SHAPE@"]) as cursor:
                cursor.insertRow([higher[i]])                         
        arcpy.management.Dissolve("all_higher_roads", "all_higher_roads_dissolved", ["OBJECTID"])
        arcpy.management.Append("all_higher_roads_dissolved", "merged_roads")
        
    

                
                           
