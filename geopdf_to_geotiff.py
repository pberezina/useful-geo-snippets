import sys
import arcpy
import os
import argparse
import tempfile


parser=argparse.ArgumentParser(
    description='''Convert geopdf files to geotiff files using ArcGIS arcpy.\nRequired input: ''')
parser.add_argument('--f', type=str, help='Input folder path')
parser.add_argument('--o', type=str, help='Output folder path')
args=parser.parse_args()

    
if __name__ == "__main__":
    arcpy.env.workspace = sys.argv[2]
    arcpy.env.compression = "JPEG 10"
    temp_dir = tempfile.TemporaryDirectory()

    pdf_list = [f for f in os.listdir(sys.argv[1]) if f.lower().endswith('.pdf')]

    # Reproject a TIFF image with Datumn transfer
    for inPDF in pdf_list:
        outTIFF = os.path.join(temp_dir, inPDF[:-4] + '.tif')
        outTIFFproj = inPDF[:-4] + '.tif'
        arcpy.PDFToTIFF_conversion(inPDF, outTIFF)
        arcpy.ProjectRaster_management(outTIFF, outTIFFproj, arcpy.SpatialReference(4326), "NEAREST")
    
    # Clean up temporary files and xml, ovr in output
    for item in os.listdir():
        if item.endswith(".xml") or item.endswith(".ovr"):
            os.remove(item)
    temp_dir.cleanup()