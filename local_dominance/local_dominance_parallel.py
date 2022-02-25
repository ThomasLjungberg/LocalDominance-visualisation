from builtins import range
from osgeo.gdal import AllRegister, Open, GetDriverByName, GDT_Float32
from numpy import zeros, arange, sqrt, arctan, abs, round, sum, ceil
from numpy.linalg import norm as nlnorm
from multiprocessing import Pool
from bisect import bisect_left
from os.path import abspath, join, dirname
from sys import argv
from PyQt5.QtWidgets import QMainWindow, QApplication, QProgressBar

basepath = dirname(abspath(__file__))
with(open(join(basepath, 'argFile.txt'), 'r')) as f:
    args = f.readlines()


# input and output files
inFile = args[0].rstrip()
outFile = args[1].rstrip()

# number of cores to use
ncores = int(args[5])

# fraction of pixels to use
pixelFrac = float(args[4]) / 100.

# search radius and observer height
minDist = int(args[2])
maxDist = int(args[3])

AllRegister()

# get necessary information from input file
tiff = Open(inFile)
band = tiff.GetRasterBand(1)
proj = tiff.GetProjection()
dem = band.ReadAsArray() * 1.
gtf_in = tiff.GetGeoTransform()
dx =  abs(gtf_in[1])
dy =  abs(gtf_in[5])
nrow, ncol = dem.shape

# size of the "frame" (in pixels) along the border of the input file where we
# cannot compute a result
frameX = int(round(maxDist/dx))
frameY = int(round(maxDist/dy))
# number of rows and columns in range of the max search radius
nRowsInRange = 2 * frameY + 1
nColsInRange = 2 * frameX + 1
# size of the resulting visualisation
ldNRows, ldNCols = (nrow - 2 * frameY, ncol - 2 * frameX)


# function that chooses an equally distributed fraction of elements from a list.
# Found on Stack Overflow, unfortunally I don't remember the name of the author
def equal_dist_els(my_list, fraction):
    """
    Chose a fraction of equally distributed elements.
    :param my_list: The list to draw from
    :param fraction: The ideal fraction of elements
    :return: Elements of the list with the best match
    """
    length = len(my_list)
    list_indexes = list(range(length))
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


# Find indices of the pixels that are to be used for calculation, and return a 
# list of tuples (row_ind, col_ind, distance)
def ChoosePixels():
    Xs = equal_dist_els(arange(nColsInRange), sqrt(pixelFrac))
    Ys = equal_dist_els(arange(nRowsInRange), sqrt(pixelFrac))
    pixelList = []
    for i in Ys:
        for j in Xs:
            dist = nlnorm([(i-frameY)*dy, (j-frameX)*dx])
            if minDist <= dist <= maxDist:
                pixelList.append((i,j, dist))
    return pixelList


# progress bar
class ProgBar(QMainWindow):

    def __init__(self, pixelList):
        super(ProgBar, self).__init__()
        self.setGeometry(150, 150, 500, 100)
        self.setWindowTitle("Local Dominance Visualisation")
        self.pixelList = pixelList[0]
        self.home()

    def home(self):
        self.progress = QProgressBar(self)
        self.progress.setGeometry(50, 40, 400, 30)
        self.center()
        self.show()
        
        
    def LocalD(self):
        tmp = zeros((nrow - 2 * frameY, ncol - 2 * frameX), dtype=dem.dtype)
        for i, elem in enumerate(self.pixelList):
            vDist = dem[frameY:-frameY, frameX:-frameX] - dem[elem[0]:elem[0]+ldNRows, elem[1]:elem[1]+ldNCols]
            tmp += arctan(vDist/elem[2])
            self.progress.setValue((i*100)/len(self.pixelList))
            QApplication.processEvents()
        return tmp
    
    def center(self):
        """Center progress bar on the current screen."""
        self.showNormal()
        window_geometry = self.frameGeometry()
        mouse_pos = QApplication.desktop().cursor().pos()
        screen_number = QApplication.desktop().screenNumber(mouse_pos)
        center = QApplication.desktop().screenGeometry(screen_number).center()
        window_geometry.moveCenter(center)
        return bool(not self.move(window_geometry.topLeft()))
        

# run the visualisation. First process is sent to progress bar
def run_LocalD(pixelList):
    if pixelList[1] == 0:
        app = QApplication(argv)
        tmp = ProgBar(pixelList).LocalD()
        app.exit()
    else:
        tmp = zeros((nrow - 2 * frameY, ncol - 2 * frameX), dtype=dem.dtype)
        for i in pixelList[0]:
            vDist = dem[frameY:-frameY, frameX:-frameX] - dem[i[0]:i[0]+ldNRows, i[1]:i[1]+ldNCols]
            tmp += arctan(vDist/i[2])
            
    return tmp


# name says it all
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


# parallel processing
def main():
    pixelList = ChoosePixels()
    chunk = int(ceil(len(pixelList)/ncores))
    argList = [[pixelList[i:i+chunk], i] for i in range(0, len(pixelList), chunk)]
    
    pool = Pool(processes=ncores)
    results = pool.map(run_LocalD, argList)
    pool.close()
    pool.join()
    ld = sum(results, axis=0)
    WriteOutFile(ld)

    


if __name__ == '__main__':
    __spec__ = None
    main()

