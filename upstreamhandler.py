"""
Handles tiff i/o and translates them to/from flt32 files. Wrapper for upstream averaging in c.
"""
import subprocess
import numpy as np
from osgeo import gdal
import os

deminfile = './data/input_DEM.tif'
varinfile = './data/input_var.tif'
outfile = './data/upstreamavg.tif'
TMP_DIR = './data/tmp'
iot_dem = './data/io_test/Plainfield_DEM.tif'
iot_var = './data/io_test/Plainfield_Slope.tif'

DEM_FLT_INFILE = './data/tmp/input_dem.flt'
VAR_FLT_INFILE = './data/tmp/input_var.flt'
UPSTRMAVG_FLT_OUTFILE = './data/tmp/output.flt'
EXECUTABLE = './data/tmp/upstreamavg.exe'
tif_tags = ['metadata', 'dx', 'Nx', 'Ny', 'nodata']
source_info = {}

def tiff_get_tags(tiff_inf):
    """
    Get tags from a tiff file.
    """
    raster = gdal.Open(tiff_inf)
    metadata = raster.GetMetadata()
    gt = raster.GetGeoTransform()
    dx = gt[1]
    dy = gt[5]
    Ny = raster.RasterYSize
    Nx = raster.RasterXSize
    nodata = raster.GetRasterBand(1).GetNoDataValue()
    return [metadata, dx, Nx, Ny, nodata]
 
def tiff_to_flt(tiff_inf, flt_outf):
    """
    Convert a tiff file to a flt file.
    """
    raster = gdal.Open(tiff_inf)
    if raster is None:
        raise FileNotFoundError(f"Could not open TIFF file: {tiff_inf}")
    b1 = raster.GetRasterBand(1)
    arr = b1.ReadAsArray()
    with open(flt_outf, 'wb') as f:
        f.write(arr.astype(np.float32).tobytes())

def invoke_upstream(x, y, d, v, exe):
    """
    Invoke upstreamavg.c with the given parameters.
    """
    subprocess.run(['gcc', '-o', exe, 'upstreamavg.c', 'utilities.c', '-lm', '-Wall'])
    subprocess.run([exe, '-x', str(x), '-y', str(y), '-d', str(d), '-v', str(v)])
    print('Upstream averaging executed successfully.')

def flt_to_tiff(flt_inf, tiff_outf, Nx, Ny):
    """
    Convert a flt file to a tiff file.
    """
    with open(flt_inf, 'rb') as f:
        arr = np.fromfile(f, dtype=np.float32)
    arr = arr.reshape((Ny, Nx))
    to_gtiff = gdal.GetDriverByName('GTiff')
    out_raster = to_gtiff.Create(tiff_outf, Nx, Ny, 1, gdal.GDT_Float32)
    out_raster.GetRasterBand(1).WriteArray(arr)
    out_raster.FlushCache()
    out_raster = None
    return arr

def tmp_destroy():
    """
    Remove the temporary directory and its contents.
    """
    if os.path.exists(TMP_DIR):
        for file in os.listdir(TMP_DIR):
            file_path = os.path.join(TMP_DIR, file)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    os.rmdir(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
        os.rmdir(TMP_DIR)
    return print(f'Temporary directory {TMP_DIR} removed.')
    

if __name__ == "__main__":

    os.makedirs(TMP_DIR, exist_ok=True)

    '''
    deminfile = './data/' + input("Enter DEM filename with extension: ").strip()
    varinfile = '.data/' + input("Enter variable filename with extension: ").strip()

    if os.path.isfile(deminfile) and os.path.isfile(varinfile):
        print(f"Files found:\nDEM file: {deminfile}\nVariable file: {varinfile}")
    else:
        print("Error: One or both files do not exist. Please check the paths.")
    '''
    for k, v in zip(tif_tags, tiff_get_tags(iot_dem)):
        source_info[k] = v    

    print(f"Tags for {deminfile}: {source_info}")
    
    tiff_to_flt(iot_dem, DEM_FLT_INFILE)
    tiff_to_flt(iot_var, VAR_FLT_INFILE)

    print(f"Invoking upstream handler with {DEM_FLT_INFILE} and {VAR_FLT_INFILE}")
    invoke_upstream(source_info['Nx'], source_info['Ny'], source_info['dx'], source_info['nodata'], EXECUTABLE)

    ##outfile = input('Enter path for output file (default: ./data/upstreamavg.tif): ').strip() or outfile
    flt_to_tiff(UPSTRMAVG_FLT_OUTFILE, outfile, source_info['Nx'], source_info['Ny'])

    tmp_destroy()
    print(f"Output written to {outfile}")
    print('Done.')