﻿# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Name:        Valley Confinement Tool                                        #
# Purpose:     Calculate Valley Confinement Along a Stream Network            #
#                                                                             #
# Author:      Kelly Whitehead (kelly@southforkresearch.org)                  #
#              South Fork Research, Inc                                       #
#              Seattle, Washington                                            #
#                                                                             #
# Created:     2014-Nov-01                                                    #
# Version:     1.3                                                            #
# Modified:    2016-Feb-10                                                    #
#                                                                             #
# Copyright:   (c) Kelly Whitehead 2016                                       #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#!/usr/bin/env python

# # Import Modules # #
import sys
import arcpy
import gis_tools
import DividePolygonBySegment

## Updates
# Shapefile support
# Remove old calculation methods
# use stat table calculation method
# Added Constriction Field
# Added Final Intersect to rejoin Original Attributes.


# # Main Function # #
def main(fcInputStreamLineNetwork,
         fcInputValleyBottomPolygon,
         fcInputChannelPolygon,
         fcOutputRawConfiningState,
         fcOutputConfiningMargins,
         scratchWorkspace,
         boolIntegratedWidthAttributes=False):

    ##Prepare processing environments
    arcpy.AddMessage("Starting Confining Margins Tool")

    # Create Confined Channel Polygon
    fcConfinedChannel = gis_tools.newGISDataset(scratchWorkspace,"ChannelConfined")
    arcpy.Clip_analysis(fcInputChannelPolygon,fcInputValleyBottomPolygon,fcConfinedChannel)

    # Convert Confined Channel polygon to Edges polyline
    fcChannelMargins = gis_tools.newGISDataset(scratchWorkspace,"ChannelMargins")
    arcpy.PolygonToLine_management(fcConfinedChannel,fcChannelMargins)

    # Create Confinement Edges
    if fcOutputConfiningMargins:
        gis_tools.resetData(fcOutputConfiningMargins)
        fcConfiningMargins = fcOutputConfiningMargins
    else:
        fcConfiningMargins = gis_tools.newGISDataset(scratchWorkspace, "ConfiningMargins")

    fcConfiningMarginsMultipart = gis_tools.newGISDataset(scratchWorkspace, "ConfiningMargins_Multipart")
    arcpy.Intersect_analysis([fcConfinedChannel, fcInputValleyBottomPolygon], fcConfiningMarginsMultipart, output_type="LINE")
    arcpy.MultipartToSinglepart_management(fcConfiningMarginsMultipart,fcConfiningMargins)

    # Merge segments in Polyline Center to create Route Layer
    arcpy.env.outputZFlag = "Disabled" # 'empty' z values can cause problem with dissolve
    fcStreamNetworkDissolved = gis_tools.newGISDataset(scratchWorkspace, "StreamNetworkDissolved") # one feature per 'section between trib or branch junctions'
    arcpy.Dissolve_management(fcInputStreamLineNetwork, fcStreamNetworkDissolved, multi_part="SINGLE_PART", unsplit_lines="UNSPLIT_LINES")

    fcNetworkSegmentPoints = gis_tools.newGISDataset(scratchWorkspace, "StreamNetworkSegmentPoints")
    arcpy.FeatureVerticesToPoints_management(fcInputStreamLineNetwork, fcNetworkSegmentPoints, "END")
    fcStreamNetworkDangles = gis_tools.newGISDataset(scratchWorkspace, "StreamNetworkDangles")
    arcpy.FeatureVerticesToPoints_management(fcInputStreamLineNetwork, fcStreamNetworkDangles, "DANGLE")

    #SegmentPolgyons
    arcpy.AddMessage("Preparing Segmented Polygons...")
    
    fcChannelSegmentPolygons = gis_tools.newGISDataset(scratchWorkspace, "SegmentPolygons")
    fcChannelSegmentPolygonLines = gis_tools.newGISDataset(scratchWorkspace,"SegmentPolygonLines")

    #DividePolygonBySegment.main(fcInputStreamLineNetwork, fcConfinedChannel, fcChannelSegmentPolygons, scratchWorkspace)
    arcpy.CopyFeatures_management(fcConfinedChannel,fcChannelSegmentPolygons)
    arcpy.PolygonToLine_management(fcChannelSegmentPolygons, fcChannelSegmentPolygonLines)

    lyrStreamNetworkDangles = gis_tools.newGISDataset("LAYER", "lyrStreamNetworkDangles")
    arcpy.MakeFeatureLayer_management(fcStreamNetworkDangles, lyrStreamNetworkDangles)
    arcpy.SelectLayerByLocation_management(lyrStreamNetworkDangles, "INTERSECT", fcConfinedChannel)
    arcpy.Near_analysis(lyrStreamNetworkDangles, fcChannelSegmentPolygonLines, location="LOCATION")
    
    arcpy.AddXY_management(lyrStreamNetworkDangles)

    fcChannelBankNearLines = gis_tools.newGISDataset(scratchWorkspace, "Bank_NearLines")
    arcpy.XYToLine_management(lyrStreamNetworkDangles,
                                fcChannelBankNearLines,
                                "POINT_X",
                                "POINT_Y",
                                "NEAR_X",
                                "NEAR_Y")

    fcChannelBankLines = gis_tools.newGISDataset(scratchWorkspace, "Bank_Lines")
    arcpy.Merge_management([fcInputStreamLineNetwork,fcChannelBankNearLines, fcChannelSegmentPolygonLines], fcChannelBankLines)
    fcChannelBankPolygons = gis_tools.newGISDataset(scratchWorkspace, "Bank_Polygons")
    arcpy.FeatureToPolygon_management(fcChannelBankLines, fcChannelBankPolygons)
        
    # # Intersect and Split Channel polygon Channel Edges and Polyline Confinement using cross section lines
    arcpy.AddMessage("Intersect and Split Channel Polygons...")
    fcIntersectPoints_ChannelMargins = gis_tools.newGISDataset(scratchWorkspace, "IntersectPoints_ChannelMargins")
    fcIntersectPoints_ConfinementMargins = gis_tools.newGISDataset(scratchWorkspace, "IntersectPoints_ConfinementMargins")
    arcpy.Intersect_analysis([fcConfiningMargins,fcChannelSegmentPolygonLines], fcIntersectPoints_ConfinementMargins, output_type="POINT")
    arcpy.Intersect_analysis([fcChannelMargins,fcChannelSegmentPolygonLines], fcIntersectPoints_ChannelMargins, output_type="POINT")
    fcConfinementMargin_Segments = gis_tools.newGISDataset(scratchWorkspace, "ConfinementMargin_Segments")
    fcChannelMargin_Segments = gis_tools.newGISDataset(scratchWorkspace, "ChannelMargin_Segements")
    arcpy.SplitLineAtPoint_management(fcConfiningMargins, fcIntersectPoints_ConfinementMargins, fcConfinementMargin_Segments, search_radius="10 Meters")
    arcpy.SplitLineAtPoint_management(fcChannelMargins, fcIntersectPoints_ChannelMargins, fcChannelMargin_Segments, search_radius="10 Meters")

    # Create River Side buffer to select right or left banks
    arcpy.AddMessage("Determining Relative Sides of Bank...")
    determine_banks(fcInputStreamLineNetwork, fcChannelBankPolygons, scratchWorkspace)

    # Prepare Layers for Segment Selection
    lyrSegmentPolygons = gis_tools.newGISDataset("Layer","lyrSegmentPolygons")
    lyrConfinementEdgeSegments = gis_tools.newGISDataset("Layer", "lyrConfinementEdgeSegments")
    lyrChannelEdgeSegments = gis_tools.newGISDataset("Layer", "lyrChannelEdgeSegments")
    arcpy.MakeFeatureLayer_management(fcChannelSegmentPolygons, lyrSegmentPolygons)
    arcpy.MakeFeatureLayer_management(fcConfinementMargin_Segments, lyrConfinementEdgeSegments)
    arcpy.MakeFeatureLayer_management(fcChannelMargin_Segments, lyrChannelEdgeSegments)

    ## Prepare Filtered Margins
    fcFilterSplitPoints = gis_tools.newGISDataset(scratchWorkspace, "FilterSplitPoints")
    arcpy.FeatureVerticesToPoints_management(fcConfinementMargin_Segments, fcFilterSplitPoints, "BOTH_ENDS")

    # Transfer Confining Margins to Stream Network ##
    arcpy.AddMessage("Transferring Confining Margins to Stream Network...")
    fcConfinementMarginSegmentsBankSide = gis_tools.newGISDataset(scratchWorkspace, "ConfinementMarginSegmentsBank")
    lyrConfinementMarginSegmentsBankside = gis_tools.newGISDataset("Layer", "lyrConfinementMarginSegmentsBankside")

    field_map = """BankSide "BankSide" true true false 255 Text 0 0 ,First,#,""" + fcChannelBankPolygons + """,BankSide,-1,-1"""
    arcpy.SpatialJoin_analysis(fcConfinementMargin_Segments,
                               fcChannelBankPolygons,
                               fcConfinementMarginSegmentsBankSide,
                               "JOIN_ONE_TO_ONE",
                               "KEEP_ALL",
                               field_map)

    arcpy.MakeFeatureLayer_management(fcConfinementMarginSegmentsBankSide, lyrConfinementMarginSegmentsBankside)
    arcpy.SelectLayerByAttribute_management(lyrConfinementMarginSegmentsBankside, "NEW_SELECTION", """ "BankSide" = 'LEFT'""")
    
    fcStreamNetworkConfinementLeft = transfer_line(lyrConfinementMarginSegmentsBankside, fcStreamNetworkDissolved, "LEFT")
    arcpy.SelectLayerByAttribute_management(lyrConfinementMarginSegmentsBankside, "NEW_SELECTION", """ "BankSide" = 'RIGHT'""")
    fcStreamNetworkConfinementRight = transfer_line(lyrConfinementMarginSegmentsBankside, fcStreamNetworkDissolved, "RIGHT")

    fcConfinementStreamNetworkIntersected = gis_tools.newGISDataset(scratchWorkspace,"ConfinementStreamNetworkIntersected")
    arcpy.Intersect_analysis([fcStreamNetworkConfinementLeft,fcStreamNetworkConfinementRight],
                             fcConfinementStreamNetworkIntersected, "NO_FID") # TODO no fid?

    #Re-split centerline by segments
    arcpy.AddMessage("Determining Confinement State on Stream Network...")
    fcRawConfiningNetworkSplit = gis_tools.newGISDataset(scratchWorkspace,"RawConfiningNetworkSplit")
    arcpy.SplitLineAtPoint_management(fcConfinementStreamNetworkIntersected,
                                      fcNetworkSegmentPoints,
                                      fcRawConfiningNetworkSplit,
                                      "0.01 Meters")

    #Table and Attributes
    arcpy.AddField_management(fcRawConfiningNetworkSplit, "Con_Type", "TEXT", field_length="6")
    arcpy.AddField_management(fcRawConfiningNetworkSplit, "IsConfined", "SHORT")
    gis_tools.resetField(fcRawConfiningNetworkSplit, "IsConstric", "SHORT")

    lyrRawConfiningNetwork = gis_tools.newGISDataset("Layer", "lyrStreamNetworkCenterline1")
    arcpy.MakeFeatureLayer_management(fcRawConfiningNetworkSplit,lyrRawConfiningNetwork)

    arcpy.SelectLayerByAttribute_management(lyrRawConfiningNetwork,"NEW_SELECTION", """ "Con_LEFT" = 1""")
    arcpy.CalculateField_management(lyrRawConfiningNetwork,"Con_Type", "'LEFT'", "PYTHON")
    arcpy.SelectLayerByAttribute_management(lyrRawConfiningNetwork, "NEW_SELECTION", """ "Con_RIGHT" = 1""")
    arcpy.CalculateField_management(lyrRawConfiningNetwork,"Con_Type", "'RIGHT'", "PYTHON")
    arcpy.SelectLayerByAttribute_management(lyrRawConfiningNetwork, "NEW_SELECTION", """ "Con_LEFT" = 1 AND "Con_RIGHT" = 1""")
    arcpy.CalculateField_management(lyrRawConfiningNetwork,"Con_Type", "'BOTH'", "PYTHON")
    arcpy.CalculateField_management(lyrRawConfiningNetwork,"IsConstric", "1", "PYTHON")
    arcpy.SelectLayerByAttribute_management(lyrRawConfiningNetwork, "SWITCH_SELECTION")
    arcpy.CalculateField_management(lyrRawConfiningNetwork, "IsConstric", "0", "PYTHON")
    arcpy.SelectLayerByAttribute_management(lyrRawConfiningNetwork, "NEW_SELECTION", """ "Con_LEFT" = 1 OR "Con_RIGHT" = 1""")
    arcpy.CalculateField_management(lyrRawConfiningNetwork, "IsConfined", "1", "PYTHON")
    arcpy.SelectLayerByAttribute_management(lyrRawConfiningNetwork, "SWITCH_SELECTION")
    arcpy.CalculateField_management(lyrRawConfiningNetwork, "IsConfined", "0", "PYTHON")
    arcpy.CalculateField_management(lyrRawConfiningNetwork, "Con_Type", "'NONE'", "PYTHON")

    # Integrated Width

    fcIntersectLineNetwork = fcInputStreamLineNetwork
    if boolIntegratedWidthAttributes:
        fcIntegratedChannelWidth = gis_tools.newGISDataset(scratchWorkspace,"IW_Channel")
        fieldIWChannel = integrated_width(fcInputStreamLineNetwork, fcChannelSegmentPolygons, fcIntegratedChannelWidth, "Channel" , False)

        fcIntegratedWidth = gis_tools.newGISDataset(scratchWorkspace,"IW_ChannelAndValley")
        fieldIWValley = integrated_width(fcIntegratedChannelWidth,fcInputValleyBottomPolygon,fcIntegratedWidth,"Valley",True)

        fieldIWRatio = gis_tools.resetField(fcIntegratedWidth, "IW_Ratio", "DOUBLE")
        exp = "!" + fieldIWValley + r"! / !" + fieldIWChannel + "!"
        arcpy.CalculateField_management(fcIntegratedWidth, fieldIWRatio, exp, "PYTHON_9.3")
        fcIntersectLineNetwork = fcIntegratedWidth

    # Final Output
    arcpy.AddMessage("Preparing Final Output...")
    if arcpy.Exists(fcOutputRawConfiningState):
        arcpy.Delete_management(fcOutputRawConfiningState)
    arcpy.Intersect_analysis([fcRawConfiningNetworkSplit,fcIntersectLineNetwork], fcOutputRawConfiningState, "NO_FID")

    return


def determine_banks(fcInputStreamLineNetwork,fcChannelBankPolygons,scratchWorkspace):

    fcChannelBankSideBuffer = gis_tools.newGISDataset(scratchWorkspace,"BankSide_Buffer")
    fcChannelBankSidePoints = gis_tools.newGISDataset(scratchWorkspace,"BankSidePoints")
    arcpy.Buffer_analysis(fcInputStreamLineNetwork,fcChannelBankSideBuffer,"1 Meter","LEFT","FLAT","NONE")
    arcpy.FeatureToPoint_management(fcChannelBankSideBuffer,fcChannelBankSidePoints,"INSIDE")
    arcpy.AddField_management(fcChannelBankPolygons,"BankSide","TEXT","10")
    lyrChannelBanks = gis_tools.newGISDataset("Layer","lyrChannelBanks")
    arcpy.MakeFeatureLayer_management(fcChannelBankPolygons,lyrChannelBanks)
    arcpy.SelectLayerByLocation_management(lyrChannelBanks,"INTERSECT",fcChannelBankSidePoints,selection_type="NEW_SELECTION")
    arcpy.CalculateField_management(lyrChannelBanks,"BankSide","'LEFT'","PYTHON")
    arcpy.SelectLayerByAttribute_management(lyrChannelBanks,"SWITCH_SELECTION")
    arcpy.CalculateField_management(lyrChannelBanks,"BankSide","'RIGHT'","PYTHON")
    
    return 


def transfer_line(fcInLine,fcToLine,strStreamSide):
    outputWorkspace = arcpy.Describe(fcInLine).path
    fcOutput = gis_tools.newGISDataset(outputWorkspace,"LineNetworkConfinement" + strStreamSide)
    
    # Split Line Network by Line Ends 
    fcSplitPoints = gis_tools.newGISDataset(outputWorkspace,"SplitPoints_Confinement" + strStreamSide)
    arcpy.FeatureVerticesToPoints_management(fcInLine,fcSplitPoints,"BOTH_ENDS")
    tblNearPointsConfinement = gis_tools.newGISDataset(outputWorkspace,"NearPointsConfinement" + strStreamSide)
    arcpy.GenerateNearTable_analysis(fcSplitPoints,fcToLine,tblNearPointsConfinement,location="LOCATION",angle="ANGLE")
    lyrNearPointsConfinement = gis_tools.newGISDataset("Layer","lyrNearPointsConfinement"+ strStreamSide)
    arcpy.MakeXYEventLayer_management(tblNearPointsConfinement,"NEAR_X","NEAR_Y",lyrNearPointsConfinement,fcToLine)
    arcpy.SplitLineAtPoint_management(fcToLine,lyrNearPointsConfinement,fcOutput,search_radius="0.01 Meters")
    
    # Prepare Fields
    strConfinementField = "Con_" + strStreamSide
    arcpy.AddField_management(fcOutput,strConfinementField,"LONG")

    # Transfer Attributes by Centroids
    fcCentroidPoints = gis_tools.newGISDataset(outputWorkspace,"CentroidPoints_Confinement" + strStreamSide)
    arcpy.FeatureVerticesToPoints_management(fcInLine,fcCentroidPoints,"MID")
    tblNearPointsCentroid = gis_tools.newGISDataset(outputWorkspace,"NearPointsCentroid" + strStreamSide)
    arcpy.GenerateNearTable_analysis(fcCentroidPoints,fcToLine,tblNearPointsCentroid,location="LOCATION",angle="ANGLE")
    lyrNearPointsCentroid = gis_tools.newGISDataset("Layer","lyrNearPointsCentroid" + strStreamSide)
    arcpy.MakeXYEventLayer_management(tblNearPointsCentroid,"NEAR_X","NEAR_Y",lyrNearPointsCentroid,fcToLine)
    lyrToLineSegments = gis_tools.newGISDataset("Layer","lyrToLineSegments")
    arcpy.MakeFeatureLayer_management(fcOutput,lyrToLineSegments)
    
    arcpy.SelectLayerByLocation_management(lyrToLineSegments,"INTERSECT",lyrNearPointsCentroid,selection_type="NEW_SELECTION")#"0.01 Meter","NEW_SELECTION")
    arcpy.CalculateField_management(lyrToLineSegments,strConfinementField,1,"PYTHON")
    
    return fcOutput


def integrated_width(fcInLines, fcInPolygons, fcOutLines, strMetricName="", boolSegmentPolygon=False, temp_workspace="in_memory"):

    fcMemLines = gis_tools.newGISDataset(temp_workspace,"lineNetwork")
    arcpy.CopyFeatures_management(fcInLines,fcMemLines)
    fieldLength = gis_tools.resetField(fcMemLines,"IW_Length","DOUBLE")
    arcpy.CalculateField_management(fcMemLines,fieldLength,"!Shape!.length","PYTHON")

    fcMemPolygons = gis_tools.newGISDataset(temp_workspace,'Polygons')
    if boolSegmentPolygon:
        DividePolygonBySegment.main(fcMemLines, fcInPolygons, fcMemPolygons, temp_workspace, dblPointDensity=5.0)
    else:
        arcpy.CopyFeatures_management(fcInPolygons,fcMemPolygons)

    fieldPolygonArea = gis_tools.resetField(fcMemPolygons, strMetricName[0:6] + "Area","DOUBLE")
    arcpy.CalculateField_management(fcMemPolygons, fieldPolygonArea, "!Shape!.area", "PYTHON")

    f_mappings = arcpy.FieldMappings()
    f_mappings.addTable(fcMemLines)
    fmap_area = arcpy.FieldMap()
    fmap_area.addInputField(fcMemPolygons, fieldPolygonArea)

    f_mappings.addFieldMap(fmap_area)

    arcpy.SpatialJoin_analysis(fcMemLines, fcMemPolygons, fcOutLines, "JOIN_ONE_TO_ONE", "KEEP_ALL",
                               field_mapping=f_mappings, match_option="WITHIN")
    fieldIntegratedWidth = gis_tools.resetField(fcOutLines, "IW" + strMetricName[0:8], "DOUBLE")
    exp = "!" + fieldPolygonArea + r"! / !" + fieldLength + "!"
    print exp
    arcpy.CalculateField_management(fcOutLines, fieldIntegratedWidth, exp, "PYTHON_9.3")

    return fieldIntegratedWidth


if __name__ == "__main__":

    main(sys.argv[1],
         sys.argv[2],
         sys.argv[3],
         sys.argv[4],
         sys.argv[5],
         sys.argv[6])

