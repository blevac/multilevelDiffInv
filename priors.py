import torch.nn.functional as F
import torch
import torch.nn as nn
import torch.distributions as td
import numpy as np
from numpy.linalg import svd
from fno import *




class StandardNormal(nn.Module):

    def __init__(self):
        super(StandardNormal, self).__init__()

    def __repr__(self):
        return "StandardNormal"

    #standard noise
    def sample(self,shape_vec):
        x = torch.randn(shape_vec[0],1,shape_vec[2],shape_vec[3]).to(device)
        return self.Qmv(x)

    #covariance
    def Qmv(self,v):
        return v

    #loss structure
    #g*a means the Q in reverse drift is learned implicitly in a
    #self.Qmv(g*a) means the Q is given explictly
    def Q_g2_s(self, g,a): 
        return g*a 

class FNOprior(nn.Module):
    def __init__(self,k1=16,k2=9):
        super(FNOprior, self).__init__()
        self.k1 = k1
        self.k2 = k2
        self.conv = SpectralConv2d(1,1,k1,k2, rand = False).to(device)

    def __repr__(self):
        return "FNOprior(k1=%d, k2=%d)" %(self.k1,self.k2)
    def sample(self,shape_vec):
        x = torch.randn(shape_vec[0],1,shape_vec[2],shape_vec[3]).to(device)
        return self.Qmv(x)

    def Qmv(self,v):
        return self.conv(v)

    def Q_g2_s(self, g,a): 
        return g*a #Qmv(g*a) 


class ImplicitConv(nn.Module):
    """
    Compute the covariance matrix as

    Q = conv(K)^{-1/2}

    where K is a separable stencil, e.g., the standard 5-point Laplacian.
    """

    def __init__(self,K=None):
        super(ImplicitConv, self).__init__()
        # tbd: check if K is separable
        self.K = K
        self.is_sep = self.sep(K)

    def __repr__(self):
        return "ImplicitConv(k1=%d, k2=%d)" %(self.k1,self.k2)

    def sep(self, K):
        U, S, V = svd(K)
        is_sep = np.count_nonzeros(S) == 1
        return is_sep

    def sample(self,shape_vec):
        x = torch.randn(shape_vec[0],1,shape_vec[2],shape_vec[3]).to(device)
        return self.Qmv(x)

    def Qmv(self,v):
        return self.compConv(v, fun = lambda x: (1/torch.sqrt(x)))[0]

    def Q_g2_s(self, g,a): #method
        return g*a #self.Qmv(g*a) 

    # #Laplacian
    # def stencil(self, hx, hy):
    #     K = torch.zeros(3,3)
    #     K[1,1] = 2.0/(hx**2) + 2.0/(hy**2)
    #     K[0,1] = -1.0/(hy**2)
    #     K[1,0] = -1.0/(hx**2)
    #     K[2,1] = -1.0/(hy**2)
    #     K[1,2] = -1.0/(hx**2)
    #
    #     return K

    def compConv(self,x,fun= lambda x : x):
        """
        compute fun(conv_op(K))*x assuming periodic boundary conditions on x

        where
        K       - is a 2D convolution stencil (assumed to be separable)
        conv_op - means that we build the matrix representation of the operator
        fun     - is a function applied to the operator (as a matrix-function, not
    component-wise), default fun(x)=x
        x       - are images, torch.tensor, shape=N x 1 x nx x ny
        """

        n = x.shape
        #stencil
        nx = n[2]
        ny = n[3]
        hx = 1.0/nx
        hy = 1.0/ny
        K = self.K
        m = K.shape
        mid1 = (m[0]-1)//2
        mid2 = (m[1]-1)//2
        Bp = torch.zeros(n[2],n[3], device = device)
        Bp[0:mid1+1,0:mid2+1] = K[mid1:,mid2:]
        Bp[-mid1:, 0:mid2 + 1] = K[0:mid1, -(mid2 + 1):]
        Bp[0:mid1 + 1, -mid2:] = K[-(mid1 + 1):, 0:mid2]
        Bp[-mid1:, -mid2:] = K[0:mid1, 0:mid2]
        xh = torch.fft.rfft2(x)
        Bh = torch.fft.rfft2(Bp)
        lam = fun(torch.abs(Bh)).to(device)
        xh = xh.to(device)
        lam[torch.isinf(lam)] = 0.0
        xBh = xh * lam.unsqueeze(0).unsqueeze(0)
        xB = torch.fft.irfft2(xBh)
        xB = 9*xB

        return xB,lam






