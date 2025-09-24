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
tif_tags = ['metadata', 'gt', 'proj', 'dx', 'Nx', 'Ny', 'nodata']
flags = []
source_info = {}

def tiff_get_tags(tiff_inf):
    """
    Get tags from a tiff file, return list in order of tif_tags.

    Parameters:
    -----------
    tiff_inf : str
        Input tiff file path.
    -----------
    Returns:
    list
        List of tags in order of tif_tags.
    """
    raster = gdal.Open(tiff_inf)
    metadata = raster.GetMetadata()
    gt = raster.GetGeoTransform()
    proj = raster.GetProjection()
    dx = gt[1]
    dy = gt[5]
    Ny = raster.RasterYSize
    Nx = raster.RasterXSize
    nodata = raster.GetRasterBand(1).GetNoDataValue()
    return [metadata, gt, proj, dx, Nx, Ny, nodata]
 
def tiff_to_flt(tiff_inf, flt_outf, blocksize=1024):
    """
    Convert a tiff file to a flt file in blocks to handle large files. 

    Parameters:
    -----------
    tiff_inf : str
        Input tiff file path.
    flt_outf : str
        Output flt file path.
    blocksize : int
        Number of rows per blocks for reading the tiff file, arbitrary, default is 1024.
    
    """
    # Open the tiff file, raise error if it cannot be opened
    raster = gdal.Open(tiff_inf, gdal.GA_ReadOnly)
    if raster is None:
        raise FileNotFoundError(f"Could not open TIFF file: {tiff_inf}")
    
    b1 = raster.GetRasterBand(1)
    Nx = raster.RasterXSize
    Ny = raster.RasterYSize

    with open(flt_outf, 'wb') as f:
        for i in range(0, Ny, blocksize):
            num_rows = min(blocksize, rows - i)
            arr = b1.ReadAsArray(0, i, Nx, num_rows)
            if arr is None:
                raise ValueError(f"Could not read data from TIFF file: {tiff_inf}")
            f.write(arr.astype(np.float32).tobytes())

    print(f"Converted {tiff_inf} to {flt_outf} successfully.")

    b1 = None
    raster = None
    gdal.ErrorReset()


def invoke_upstream(x, y, d, v, exe, flags):
    """
    Invoke upstreamavg.c with the given parameters.
    """
    subprocess.run(['gcc', '-o', exe, 'upstreamavg.c', 'utilities.c', '-lm', '-Wall'])
    if flags:
        subprocess.run([exe, '-x', str(x), '-y', str(y), '-d', str(d), '-v', str(v), str(flags)])
    else:
        subprocess.run([exe, '-x', str(x), '-y', str(y), '-d', str(d), '-v', str(v)])
    print('Upstream averaging executed successfully.')

def flt_to_tiff(flt_inf, tiff_outf, gt, proj, Nx, Ny, nodata, blocksize=1024):
    """
    Convert a flt file to a tiff file.

    Parameters:
    -----------
    flt_inf : str
        Input flt file path.
    tiff_outf : str
        Output tiff file path.
    gt : tuple
        GeoTransform tuple.
    proj : str
        Projection string.
    Nx, Ny : int
        Number of columns and rows.
    nodata : float
        NoData value.
    blocksize : int
        Number of rows per blocks for writing the tiff file, arbitrary, default is 1024.
    -----------
    """

    to_gtiff = gdal.GetDriverByName('GTiff')
    raster = to_gtiff.Create(tiff_outf, Nx, Ny, 1, gdal.GDT_Float32, options=['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=IF_SAFER'])
    raster.SetGeoTransform(gt)
    raster.SetProjection(proj)
    b1 = raster.GetRasterBand(1)
    b1.SetNoDataValue(nodata)

    with open(flt_inf, 'rb') as f:
        for i in range(0, Ny, blocksize):
            num_rows = min(blocksize, Ny - i)
            count = Nx * num_rows
            arr = np.fromfile(f, dtype=np.float32, count=count)
            if arr.size != count:
                raise ValueError(f"Unexpected EOF in {flt_inf} at row {i}. Expected {count} values, got {arr.size}.")
            arr = arr.reshape((num_rows, Nx))
            b1.WriteArray(arr, xoff=0, yoff=i)
    
    b1.FlushCache()
    b1 = None
    raster = None
    gdal.ErrorReset()
    print(f"Converted {flt_inf} to {tiff_outf} successfully.")

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
    print(f'Temporary directory {TMP_DIR} removed.')
    

if __name__ == "__main__":

    # Ensure temporary directory exists, create if not
    os.makedirs(TMP_DIR, exist_ok=True)

    # Get user input for file names, store in data directory
    deminfile = './data/' + input("Enter DEM filename with extension: ").strip()
    varinfile = './data/' + input("Enter variable filename with extension: ").strip()
    outfile = './data/' + (input("Enter output filename with extension (default: upstreamavg.tif): ").strip() or 'upstreamavg.tif')
    
    # Get user input for flags, store in flags list
    flags_input = input("Enter any flags (-s for sum, ) separated by spaces (default: none): ").strip()
    if flags_input: flags = flags_input.split()
    print(f"Flags set: {flags}")

    # Check if input files exist, exit if not
    if os.path.isfile(deminfile) and os.path.isfile(varinfile):
        print(f"Files found:\nDEM file: {deminfile}\nVariable file: {varinfile}")
    else:
        print("Error: One or both files do not exist. Please check the paths.")
        exit(1)

    # Extract tags from input DEM file, store in source_info dictionary, validate presence of required tags
    for k, v in zip(tif_tags, tiff_get_tags(deminfile)):
        source_info[k] = v    

    print(f"Tags for {deminfile}: {source_info}")
    
    # Convert input tiff files to flt files
    tiff_to_flt(deminfile, DEM_FLT_INFILE)
    tiff_to_flt(varinfile, VAR_FLT_INFILE)

    # Invoke upstream averaging
    print(f"Invoking upstream handler with {DEM_FLT_INFILE} and {VAR_FLT_INFILE}")
    invoke_upstream(source_info['Nx'], source_info['Ny'], source_info['dx'], source_info['nodata'], EXECUTABLE, flags)

    # Convert output flt file to tiff file
    outfile = (input('Enter path for output file (default: ./data/upstreamavg.tif): ').strip() or outfile)
    flt_to_tiff(UPSTRMAVG_FLT_OUTFILE, outfile, source_info['gt'], source_info['proj'], source_info['Nx'], source_info['Ny'], source_info['nodata'])
    print(f"Output written to {outfile}")

    # Clean up temporary files
    tmp_destroy()
    print('Done.')