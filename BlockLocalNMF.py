from os import getcwd
from numpy import sum, zeros, reshape, r_, ix_, exp, arange, sqrt, pi, dot, outer, prod


import numpy as np


def GetHomeFolder():
    # Obtains the folder in which data is saved - change accordingly
    return getcwd()


def GetFileName(params):
    # generate file names for saving  (important parameters should appear in
    # name)
    return 'Saved_Results_sigma=' + str(params['sigma_vector'][0]) + '_lambda0=' + str(params['lambda'])


def GetBox(centers, R, dims):
    D = len(R)
    box = zeros((D, 2), dtype=int)
    for dd in range(D):
        box[dd, 0] = max(centers[dd] - R[dd], 0)
        box[dd, 1] = min(centers[dd] + R[dd] + 1, dims[dd])
    return box


def RegionAdd(Z, X, box):
    # Parameters:
    #  Z -  dataset [XxYxZ...]xT array
    #  box - Dx2 array defining spatial box to put X in
    #  X -  Input array (prod(diff(box,1))xT)

    # return:
    #  Z=Z+X on box region - a [XxYxZ...]xT array
    Z[ix_(*map(lambda a: range(*a), box))] += reshape(X,
                                                      (r_[box[:, 1] - box[:, 0], -1]))
    return Z


def RegionCut(X, box, *args):
    # CUTREGION Summary of this function goes here
    # Parameters:
    #  X -  an [XxYxZ...]xT array
    #  box - region to cut
    #  args - specificy dimensions of whole picture (optional)

    # return:
    #  res - Matrix of size prod(R)xT
    dims = X.shape
    if len(args) > 0:
        dims = args[0]
    if len(dims) - 1 != len(box):
        raise Exception('box has the wrong number of dimensions')
    return X[ix_(*map(lambda a: range(*a), box))].reshape((-1, dims[-1]))

def LocalNMF(data, centers, activity, sig, NonNegative=False, tol=1e-7, iters=100, verbose=False):
    #        Input:
    #            data - Tx(XxYx...Z) array of the data
    #            centers - list of L centers of suspected neurons, of length L, where D is spatial dimension (2 or 3)
    #            activity - list of L traces of temporal activity, of length L
    #            sig - size of the gaussian kernel in different spatial directions
    #          Optional:
    #           NonNegative -  if true, neurons should be considered as non-negative
    #           tol  - tolerance for stopping algorithm
    #           iters - maximum number of iterations
    #           verbose - print progress if true
    #        Output:
    #            MSE_array - Mean square error during algorithm operation
    #            shapes  - the neuronal shape vectors
    #            activity - the neuronal activity for each shape
    #            boxes -  edges of the boxes in which each neuronal shapes lie

    # Initialize Parameters
    dims = data.shape
    D = len(dims)
    R = 3 * np.array(sig)  # size of bounding box is 3 times size of neuron
    L = len(centers)
    shapes = []
    boxes = []
    MSE_array = []
    residual = data

# Initialize shapes, activity, and residual
    for ll in range(L):
        boxes.append(GetBox(centers[ll], R, dims))
        if D > 3:
            xm = arange(dims[0]).reshape(dims[0], 1, 1)
            ym = arange(dims[1]).reshape(1, dims[1], 1)
            zm = arange(dims[2]).reshape(1, 1, dims[2])

            temp = exp(-(((xm - centers[ll][0]) ** 2) / (2 * sig[0]))
                       - ((ym - centers[ll][1]) ** 2) / (2 * sig[1])
                       - ((zm - centers[ll][2]) ** 2) / (2 * sig[2])) / sqrt(2 * pi) / prod(sig)
            temp = temp.reshape((dims[1], dims[2], dims[3], 1))
        else:
            xm = arange(dims[1]).reshape(dims[1], 1)
            ym = arange(dims[2]).reshape(1, dims[2])

            temp = exp(-(((xm - centers[ll][0]) ** 2) / (2 * sig[0]))
                       - ((ym - centers[ll][1]) ** 2) / (2 * sig[1])) / sqrt(2 * pi) / prod(sig)
            temp = temp.reshape((dims[1], dims[2], 1))

        temp = RegionCut(temp, boxes[ll])
        shapes.append(temp[:, 0])

        residual = RegionAdd(
            residual, -outer(shapes[ll], activity[ll]), boxes[ll])


# Main Loop

    for kk in range(iters):
        for ll in range(L):
            # add region
            residual = RegionAdd(
                residual, outer(shapes[ll], activity[ll]), boxes[ll])

            # cut region
            X = RegionCut(residual, boxes[ll])

            # NonNegative greedy PCA
            greedy_pca_iterations = 5
            for ii in range(greedy_pca_iterations):
                temp = dot(X.T, shapes[ll]) / sum(shapes[ll] ** 2)
                if NonNegative:
                    temp[temp < 0] = 0
                activity[ll] = temp

                temp = dot(X, activity[ll]) / sum(activity[ll] ** 2)
                if NonNegative:
                    temp[temp < 0] = 0
                shapes[ll] = temp

            # Subtract region
            residual = RegionAdd(
                residual, -outer(shapes[ll], activity[ll]), boxes[ll])

        # Measure MSE
        MSE = sum(residual ** 2) / prod(dims)
        if kk > 0 and abs(1 - MSE / MSE_array[-1]) < tol:
            break
        if kk == (iters - 1):
            print('Maximum iteration limit reached')
        MSE_array.append(MSE)
        if verbose:
            print('{0:1d}: MSE = {1:.3f}'.format(kk, MSE))

    return MSE_array, shapes, activity, boxes


T = 50
X = 200
Y = 100
data = np.random.randn(X, Y, T)
centers = [[40, 30]]
activity = [np.random.randn(T)]
sig = [3, 3]
R = 3 * np.array(sig)
dims = data.shape
MSE_array, shapes, activity, boxes=LocalNMF(data, centers, activity, sig, NonNegative=True)