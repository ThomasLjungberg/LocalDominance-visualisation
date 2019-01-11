from gdal import AllRegister, Open, GetDriverByName, GDT_Float32
from numpy import zeros, arange, sqrt, arctan, abs, round, sum
from numpy.linalg import norm as nlnorm
from multiprocessing import Pool
from bisect import bisect_left
from os.path import abspath, join, dirname

basepath = dirname(abspath(__file__))
with(open(join(basepath, 'argFile.txt'), 'r')) as f:
    args = f.readlines()

# input and output files
inFile = args[0].rstrip()
outFile = args[1].rstrip()

# number of cores to use
ncores = int(args[6])

# fraction of pixels to use
pixelFrac = float(args[5]) / 100.

# search radius and observer height
minDist = int(args[2])
maxDist = int(args[3])
obsHeight = float(args[4])

AllRegister()

tiff = Open(inFile)
band = tiff.GetRasterBand(1)
proj = tiff.GetProjection()
dem = band.ReadAsArray() * 1.
gtf_in = tiff.GetGeoTransform()
dx =  abs(gtf_in[1])
dy =  abs(gtf_in[5])
nrow, ncol = dem.shape


frameX = int(round(maxDist/dx))
frameY = int(round(maxDist/dy))
nRowsInRange = 2 * frameY + 1
nColsInRange = 2 * frameX + 1
ldNRows, ldNCols = (nrow - 2 * frameY, ncol - 2 * frameX)
obsHeights = dem[frameY:-frameY, frameX:-frameX] + obsHeight


def equal_dist_els(my_list, fraction):
    """
    Chose a fraction of equally distributed elements.
    :param my_list: The list to draw from
    :param fraction: The ideal fraction of elements
    :return: Elements of the list with the best match
    """
    length = len(my_list)
    list_indexes = range(length)
    nbr_bins = int(round(length * fraction))
    step = length / float(nbr_bins)  # the size of a single bin
    bins = [step * i for i in range(nbr_bins)]  # list of bin ends
    # distribute indexes into the bins
    splits = [bisect_left(list_indexes, wall) for wall in bins]
    splits.append(length)  # add the end for the last bin
    # get a list of (start, stop) indexes for each bin
    bin_limits = [(splits[i], splits[i + 1]) for i in range(len(splits) - 1)]
    out = []
    for bin_lim in bin_limits:
        f, t = bin_lim
        in_bin = my_list[f:t]  # choose the elements in my_list belonging in this bin
        out.append(in_bin[int(0.5 * len(in_bin))])  # choose the most central element
    return out


def FilterMatrix():
    filterMatrix = zeros((nRowsInRange, nColsInRange), dtype=bool)
    Xs = equal_dist_els(arange(nColsInRange), sqrt(pixelFrac))
    Ys = equal_dist_els(arange(nRowsInRange), sqrt(pixelFrac))

    for i in Ys:
        for j in Xs:
            filterMatrix[i,j] = 1
    
    return filterMatrix


def LocalD(startStop):
    filterMatrix = FilterMatrix()
    norm = []
    tmp = zeros((nrow - 2 * frameY, ncol - 2 * frameX), dtype=dem.dtype)
    for i in range(startStop[0], startStop[1]):
        for j in range(nColsInRange):
            if filterMatrix[i,j]:
                dist = nlnorm([(i-frameY)*dy, (j-frameX)*dx])
                if minDist <= dist <= maxDist:
                    vDist = obsHeights - dem[i:i+ldNRows,j:j+ldNCols]
                    tmp += arctan(vDist/dist)
                    norm.append(arctan(obsHeight/dist))
            else:
                pass
    return tmp, norm


def WriteOutFile(ld):
    outXMin = gtf_in[0] + frameX * dx
    outYMax = gtf_in[3] - frameY * dy
    
    driver = GetDriverByName('GTiff')
    
    outData = driver.Create(outFile, ldNCols, ldNRows, 1, GDT_Float32)
    outData.SetGeoTransform((outXMin, dx, gtf_in[2], outYMax, gtf_in[4], gtf_in[5]))
    outData.SetProjection(proj)
    outBand = outData.GetRasterBand(1)
    outBand.WriteArray(ld)
    outData = None

def main():

    chunk = int(round(nRowsInRange/ncores))
    argList = []
    
    for i in range(ncores):
        argList.append([i * chunk, (i+1) * chunk])
    argList[-1][-1] = nRowsInRange
    
#    print('Processing data using {0} cores'.format(ncores))
    pool = Pool(processes=ncores)
    results = pool.map(LocalD, argList)
#    print('Processing finished, terminating child processes')
    pool.close()
    pool.join()

    norm = sum(sum([i[1] for i in results]))
    ld = zeros((ldNRows, ldNCols), dtype=dem.dtype)
    for i in results:
        ld += i[0] / norm
    
#    print('Writing output file')
    WriteOutFile(ld)


if __name__ == '__main__':
#    print('Reading input file...')
    main()

