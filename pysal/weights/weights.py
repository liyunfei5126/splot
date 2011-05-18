__all__ = ['W', 'WSP']
__author__  = "Sergio J. Rey <srey@asu.edu> "
from pysal.common import *
from scipy import sparse
import gc
import util

class W(object):
    """
    Spatial weights

    Parameters
    ----------
    neighbors       : dictionary
                      key is region ID, value is a list of neighbor IDS
                      Example:  {'a':['b'],'b':['a','c'],'c':['b']}
    weights = None  : dictionary
                      key is region ID, value is a list of edge weights
                      If not supplied all edge wegiths are assumed to have a weight of 1.
                      Example: {'a':[0.5],'b':[0.5,1.5],'c':[1.5]}
    id_order = None : list 
                      An ordered list of ids, defines the order of
                      observations when iterating over W if not set,
                      lexicographical ordering is used to iterate and the
                      id_order_set property will return False.  This can be
                      set after creation by setting the 'id_order' property.

    Attributes
    ----------

    asymmetries
    cardinalities
    diagW2
    diagWtW
    diagWtW_WW
    histogram
    id2i            
    id_order
    id_order_set
    islands
    max_neighbors
    mean_neighbors
    min_neighbors
    n               
    neighbor_offsets
    nonzero
    pct_nonzero
    s0              
    s1              
    s2
    s2array
    sd
    sparse          
    trcW2
    trcWtW
    trcWtW_WW
    transform

                    

                      

    Examples
    --------
    >>> from pysal import W, lat2W
    >>> neighbors={0: [3, 1], 1: [0, 4, 2], 2: [1, 5], 3: [0, 6, 4], 4: [1, 3, 7, 5], 5: [2, 4, 8], 6: [3, 7], 7: [4, 6, 8], 8: [5, 7]}
    >>> weights={0: [1, 1], 1: [1, 1, 1], 2: [1, 1], 3: [1, 1, 1], 4: [1, 1, 1, 1], 5: [1, 1, 1], 6: [1, 1], 7: [1, 1, 1], 8: [1, 1]}
    >>> w=W(neighbors,weights)
    >>> w.pct_nonzero
    0.29629629629629628

    Read from external gal file

    >>> import pysal
    >>> w=pysal.open("../examples/stl.gal").read()
    >>> w.n
    78
    >>> w.pct_nonzero
    0.065417488494411577

    Set weights implicitly 

    >>> neighbors={0: [3, 1], 1: [0, 4, 2], 2: [1, 5], 3: [0, 6, 4], 4: [1, 3, 7, 5], 5: [2, 4, 8], 6: [3, 7], 7: [4, 6, 8], 8: [5, 7]}
    >>> w=W(neighbors)
    >>> w.pct_nonzero
    0.29629629629629628
    >>> w=lat2W(100,100)
    >>> w.trcW2
    39600.0
    >>> w.trcWtW
    39600.0
    >>> w.transform='r'
    >>> w.trcW2
    2530.7222222222586
    >>> w.trcWtW
    2533.6666666666774

    Cardinality Histogram

    >>> w=pysal.rook_from_shapefile("../examples/sacramentot2.shp")
    >>> w.histogram
    [(1, 1), (2, 6), (3, 33), (4, 103), (5, 114), (6, 73), (7, 35), (8, 17), (9, 9), (10, 4), (11, 4), (12, 3), (13, 0), (14, 1)]

    """
    def __init__(self,neighbors,weights=None,id_order=None):
        self.transformations={}
        self.neighbors=ROD(neighbors)
        if not weights:
            weights = {}
            for key in neighbors:
                weights[key] = [1.] * len(neighbors[key])
        self.weights=ROD(weights)
        self.transformations['O']=self.weights #original weights
        self.transform='O'
        if id_order == None:
            self._id_order=self.neighbors.keys()
            self._id_order.sort()
            self._id_order_set=False
        else:
            self._id_order=id_order
            self._id_order_set=True
        self._reset()
        self._n=len(self.weights)


    def _reset(self):
        """
        Reset properties
        """
        self._cache={}

    @property
    def sparse(self):
        """
        Sparse matrix object

        For any matrix manipulations required for w, w.sparse should be
        used. This is based on scipy.sparse. 
        """
        if 'sparse' not in self._cache:
            self._sparse=self._build_sparse()
            self._cache['sparse']=self._sparse
        return self._sparse

    def _build_sparse(self):
        """
        construct the sparse attribute
        """
        
        row=[]
        col=[]
        data=[]
        gc.disable()
        id2i=self.id2i
        for id, neigh_list in self.neighbor_offsets.iteritems():
            card=self.cardinalities[id]
            row.extend([id2i[id]]*card)
            col.extend(neigh_list)
            data.extend(self.weights[id])
        gc.enable()
        row=np.array(row)
        col=np.array(col)
        data=np.array(data)
        s=sparse.csr_matrix((data,(row,col)), shape=(self.n, self.n))
        return s

    @property
    def id2i(self):
        """
        Dictionary where the key is an ID and the value is that ID's
        index in W.id_order.
        """
        if 'id2i' not in self._cache:
            self._id2i={}
            for i,id in enumerate(self._id_order):
                self._id2i[id]=i
            self._id2i=ROD(self._id2i)
            self._cache['id2i']=self._id2i
        return self._id2i

    @property
    def n(self):
        """
        number of units
        """
        if "n" not in self._cache:
            self._n=len(self.neighbors)
            self._cache['n']=self._n
        return self._n


    @property
    def s0(self):
        """
        float

        .. math::

               s0=\sum_i \sum_j w_{i,j}

        """
        if 's0' not in self._cache:
            self._s0=self.sparse.sum()
            self._cache['s0']=self._s0
        return self._s0

    @property
    def s1(self):
        """
        float

        .. math::

               s1=1/2 \sum_i \sum_j (w_{i,j} + w_{j,i})^2

        """
        if 's1' not in self._cache:
            t=self.sparse.transpose()
            t=t+self.sparse
            t2=t.multiply(t) # element-wise square
            self._s1=t2.sum()/2.
            self._cache['s1']=self._s1
        return self._s1

    @property
    def s2array(self):
        """
        individual elements comprising s2


        See Also
        --------
        s2

        """
        if 's2array' not in self._cache:
            s=self.sparse
            self._s2array= np.array(s.sum(1)+s.sum(0).transpose())**2
            self._cache['s2array']=self._s2array
        return self._s2array

    @property
    def s2(self):
        """
        float


        .. math::

                s2=\sum_j (\sum_i w_{i,j} + \sum_i w_{j,i})^2

        """
        if 's2' not in self._cache:
            self._s2=self.s2array.sum()
            self._cache['s2']=self._s2
        return self._s2

    @property
    def trcW2(self):
        """
        Trace of :math:`WW`

        See Also
        --------
        diagW2

        """
        if 'trcW2' not in self._cache:
            self._trcW2=self.diagW2.sum()
            self._cache['trcw2']=self._trcW2
        return self._trcW2


    @property
    def diagW2(self):
        """
        Diagonal of :math:`WW` : array

        See Also
        --------
        trcW2

        """
        if 'diagw2' not in self._cache:
            self._diagW2=(self.sparse*self.sparse).diagonal()
            self._cache['diagW2']=self._diagW2
        return self._diagW2

    @property
    def diagWtW(self):
        """
        Diagonal of :math:`W^{'}W`  : array

        See Also
        --------
        trcWtW

        """
        if 'diagWtW' not in self._cache:
            self._diagWtW=(self.sparse.transpose()*self.sparse).diagonal()
            self._cache['diagWtW']=self._diagWtW
        return self._diagWtW

    @property 
    def trcWtW(self):
        """
        Trace of :math:`W^{'}W`  : float

        See Also
        --------
        diagWtW

        """
        if 'trcWtW' not in self._cache:
            self._trcWtW=self.diagWtW.sum()
            self._cache['trcWtW']=self._trcWtW
        return self._trcWtW

    @property
    def diagWtW_WW(self):
        """
        diagonal of :math:`W^{'}W + WW`
        """
        if 'diagWtW_WW' not in self._cache:
            wt=self.sparse.transpose()
            w=self.sparse
            self._diagWtW_WW=(wt*w+w*w).diagonal()
            self._cache['diagWtW_WW']=self._diagWtW_WW
        return self._diagWtW_WW

    @property
    def trcWtW_WW(self):
        """
        trace of :math:`W^{'}W + WW`
        """
        if 'trcWtW_WW' not in self._cache:
            self._trcWtW_WW=self.diagWtW_WW.sum()
            self._cache['trcWtW_WW']=self._trcWtW_WW
        return self._trcWtW_WW

    @property
    def pct_nonzero(self):
        """
        percentage of nonzero weights
        """
        if 'pct_nonzero' not in self._cache:
            self._pct_nonzero=self.sparse.nnz/(1.*self._n**2)
            self._cache['pct_nonzero']=self._pct_nonzero
        return self._pct_nonzero

    @property
    def cardinalities(self):
        """
        number of neighbors for each observation : dict
        """
        if 'cardinalities' not in self._cache:
            c={}
            for i in self._id_order:
                c[i]=len(self.neighbors[i])
            self._cardinalities=c
            self._cache['cardinalities']=self._cardinalities
        return self._cardinalities

    @property
    def max_neighbors(self):
        """
        largest number of neighbors
        """
        if 'max_neighbors' not in self._cache:
            self._max_neighbors=max(self.cardinalities.values())
            self._cache['max_neighbors']=self._max_neighbors
        return self._max_neighbors


    @property
    def mean_neighbors(self):
        """
        average number of neighbors
        """
        if 'max_neighbors' not in self._cache:
            self._mean_neighbors=np.mean(self.cardinalities.values())
            self._cache['mean_neighbors']=self._mean_neighbors
        return self._mean_neighbors


    @property
    def min_neighbors(self):
        """
        minimum number of neighbors
        """
        if 'min_neighbors' not in self._cache:
            self._min_neighbors=min(self.cardinalities.values())
            self._cache['min_neighbors']=self._min_neighbors
        return self._min_neighbors


    @property
    def nonzero(self):
        """
        number of nonzero weights
        """
        if 'nonzero' not in self._cache:
            self._nonzero=self.sparse.nnz
            self._cache['nonzero']=self._nonzero
        return self._nonzero

    @property
    def sd(self):
        """
        standard deviation of number of neighbors : float
        """
        if 'sd' not in self._cache:
            self._sd=np.std(self.cardinalities.values())
            self._cache['sd']=self._sd
        return self._sd


    @property
    def asymmetries(self):
        """
        list of id pairs with asymmetric weights
        """
        if 'asymmetries' not in self._cache:
            self._asymmetries=self.asymmetry()
            self._cache['asymmetries']=self._asymmetries
        return self._asymmetries

    @property
    def islands(self):
        """
        list of ids without any neighbors
        """
        if 'islands' not in self._cache:
            self._islands = [i for i,c in self.cardinalities.items() if c==0]
            self._cache['islands']=self._islands
        return self._islands


    @property
    def histogram(self):
        """
        cardinality histogram as a dictionary, key is the id, value is the
        number of neighbors for that unit
        """
        if 'histogram' not in self._cache:
            ct,bin=np.histogram(self.cardinalities.values(),range(self.min_neighbors,self.max_neighbors+2))
            self._histogram=zip(bin,ct)
            self._cache['histogram']=self._histogram
        return self._histogram


    def __getitem__(self,key):
        """
        Allow a dictionary like interaction with the weights class.

        Examples
        --------
        >>> from pysal import rook_from_shapefile as rfs
        >>> from pysal import lat2W
        >>> w=rfs('../examples/10740.shp')
        >>> w[0]
        {1: 1.0, 4: 1.0, 101: 1.0, 85: 1.0, 5: 1.0}
        >>> w = lat2W()
        >>> w[1]
        {0: 1.0, 2: 1.0, 6: 1.0}
        >>> w[0]
        {1: 1.0, 5: 1.0}
        """
        return dict(zip(self.neighbors[key],self.weights[key]))


    def __iter__(self):
        """
        Support iteration over weights

        Examples
        --------
        >>> import pysal
        >>> w=pysal.lat2W(3,3)
        >>> for i,wi in enumerate(w):
        ...     print i,wi
        ...     
        0 {1: 1.0, 3: 1.0}
        1 {0: 1.0, 2: 1.0, 4: 1.0}
        2 {1: 1.0, 5: 1.0}
        3 {0: 1.0, 4: 1.0, 6: 1.0}
        4 {1: 1.0, 3: 1.0, 5: 1.0, 7: 1.0}
        5 {8: 1.0, 2: 1.0, 4: 1.0}
        6 {3: 1.0, 7: 1.0}
        7 {8: 1.0, 4: 1.0, 6: 1.0}
        8 {5: 1.0, 7: 1.0}
        >>> 
        """
        class _W_iter:
            def __init__(self,w):
                self.w = w
                self.n = len(w._id_order)
                self._idx = 0
            def next(self):
                if self._idx >= self.n:
                    self._idx=0
                    raise StopIteration
                value = self.w.__getitem__(self.w._id_order[self._idx])
                self._idx+=1
                return value
        return _W_iter(self)

    def __set_id_order(self, ordered_ids):
        """
        Set the iteration order in w.

        W can be iterated over. On construction the iteration order is set to
        the lexicographic order of the keys in the w.weights dictionary. If a specific order
        is required it can be set with this method.

        Parameters
        ----------

        ordered_ids : sequence
                      identifiers for observations in specified order

        Notes
        -----

        ordered_ids is checked against the ids implied by the keys in
        w.weights. If they are not equivalent sets an exception is raised and
        the iteration order is not changed.

        Examples
        --------

        >>> import pysal
        >>> w=pysal.lat2W(3,3)
        >>> for i,wi in enumerate(w):
        ...     print i,wi
        ...     
        0 {1: 1.0, 3: 1.0}
        1 {0: 1.0, 2: 1.0, 4: 1.0}
        2 {1: 1.0, 5: 1.0}
        3 {0: 1.0, 4: 1.0, 6: 1.0}
        4 {1: 1.0, 3: 1.0, 5: 1.0, 7: 1.0}
        5 {8: 1.0, 2: 1.0, 4: 1.0}
        6 {3: 1.0, 7: 1.0}
        7 {8: 1.0, 4: 1.0, 6: 1.0}
        8 {5: 1.0, 7: 1.0}

        >>> w.id_order
        [0, 1, 2, 3, 4, 5, 6, 7, 8]
        >>> w.id_order=range(8,-1,-1)
        >>> w.id_order
        [8, 7, 6, 5, 4, 3, 2, 1, 0]
        >>> for i,w_i in enumerate(w):
        ...     print i,w_i
        ...     
        0 {5: 1.0, 7: 1.0}
        1 {8: 1.0, 4: 1.0, 6: 1.0}
        2 {3: 1.0, 7: 1.0}
        3 {8: 1.0, 2: 1.0, 4: 1.0}
        4 {1: 1.0, 3: 1.0, 5: 1.0, 7: 1.0}
        5 {0: 1.0, 4: 1.0, 6: 1.0}
        6 {1: 1.0, 5: 1.0}
        7 {0: 1.0, 2: 1.0, 4: 1.0}
        8 {1: 1.0, 3: 1.0}
        >>> 
        
        """
        if set(self._id_order) == set(ordered_ids):
            self._id_order=ordered_ids
            self._idx=0
            self._id_order_set=True
            self._reset()
        else:
            raise Exception, 'ordered_ids do not align with W ids'

    def __get_id_order(self):
        """returns the ids for the observations in the order in which they
        would be encountered if iterating over the weights."""
        return self._id_order

    id_order=property(__get_id_order, __set_id_order)

    @property
    def id_order_set(self):
        """returns True if user has set id_order, False if not.

        Examples
        --------
        >>> from pysal import lat2W
        >>> w=lat2W()
        >>> w.id_order_set
        True
        """
        return self._id_order_set


    @property
    def neighbor_offsets(self):
        """
        Given the current id_order, neighbor_offsets[id] is the offsets of the
        id's neighrbors in id_order

        Examples
        --------
        >>> from pysal import W
        >>> neighbors={'c': ['b'], 'b': ['c', 'a'], 'a': ['b']}
        >>> weights ={'c': [1.0], 'b': [1.0, 1.0], 'a': [1.0]}
        >>> w=W(neighbors,weights)
        >>> w.id_order = ['a','b','c']
        >>> w.neighbor_offsets['b']
        [2, 0]
        >>> w.id_order = ['b','a','c']
        >>> w.neighbor_offsets['b']
        [2, 1]
        """
        if "neighbors_0" not in self._cache:
            self.__neighbors_0={}
            id2i=self.id2i
            for id, neigh_list in self.neighbors.iteritems():
                self.__neighbors_0[id]=[id2i[neigh] for neigh in neigh_list] 
            self._cache['neighbors_0']=self.__neighbors_0
        return self.__neighbors_0


    def get_transform(self):
        """
        Getter for transform property

        Returns
        -------
        transformation : string (or none)

        Examples
        --------
        >>> from pysal import lat2W
        >>> w=lat2W()
        >>> w.weights[0]
        [1.0, 1.0]
        >>> w.transform
        'O'
        >>> w.transform='r'
        >>> w.weights[0]
        [0.5, 0.5]
        >>> w.transform='b'
        >>> w.weights[0]
        [1.0, 1.0]
        >>> 
        """
        return self._transform

    def set_transform(self, value="B"):
        """
        Transformations of weights.

        Parameters
        ----------
        transform : string (not case sensitive)
                    B: Binary 
                    R: Row-standardization (global sum=n)
                    D: Double-standardization (global sum=1)
                    V: Variance stabilizing
                    O: Restore original transformation (from instantiation)

        Examples
        --------
        >>> from pysal import lat2W
        >>> w=lat2W()
        >>> w.weights[0]
        [1.0, 1.0]
        >>> w.transform
        'O'
        >>> w.transform='r'
        >>> w.weights[0]
        [0.5, 0.5]
        >>> w.transform='b'
        >>> w.weights[0]
        [1.0, 1.0]
        >>> 
        """
        value=value.upper()
        self._transform = value
        if self.transformations.has_key(value):
            self.weights=self.transformations[value]
            self._reset()
        else:
            if value == "R": 
                # row standardized weights
                weights={}
                for i in self.weights:
                    wijs = self.weights[i]
                    row_sum=sum(wijs)*1.0
                    weights[i]=[wij/row_sum for wij in wijs]
                weights=ROD(weights)
                self.transformations[value]=weights
                self.weights=weights
                self._reset()
            elif value == "D":
                # doubly-standardized weights
                # update current chars before doing global sum
                self._reset()
                s0=self.s0
                ws=1.0/s0
                weights={}
                for i in self.weights:
                    wijs = self.weights[i]
                    weights[i]=[wij*ws for wij in wijs]
                weights=ROD(weights)
                self.transformations[value]=weights
                self.weights=weights
                self._reset()
            elif value == "B":
                # binary transformation
                weights={}
                for i in self.weights:
                    wijs = self.weights[i]
                    weights[i]=[1.0 for wij in wijs]
                weights=ROD(weights)
                self.transformations[value]=weights
                self.weights=weights
                self._reset()
            elif value == "V":
                # variance stabilizing
                weights={}
                q={}
                k=self.cardinalities
                s={}
                Q=0.0
                for i in self.weights:
                    wijs = self.weights[i]
                    q[i] = math.sqrt(sum([wij*wij for wij in wijs]))
                    s[i] = [wij / q[i] for wij in wijs]
                    Q+=sum([si for si in s[i]])
                nQ=self.n/Q
                for i in self.weights:
                    weights[i] = [ w*nQ for w in s[i]]
                weights=ROD(weights)
                self.transformations[value]=weights
                self.weights=weights
                self._reset()
            elif value =="O":
                # put weights back to original transformation
                weights={}
                original=self.transformations[value]
                self.weights=original
                self._reset()
            else:
                print 'unsupported weights transformation'

    transform = property(get_transform, set_transform)
    

    def asymmetry(self):
        """
        Checks for w_{i,j} == w_{j,i} forall i,j

        Returns
        -------
        asymmetries : list 
                      empty if no asymmetries are found
                      if asymmetries, first list is row indices, second
                      list is column indices of asymmetric cells

        Examples
        --------

        >>> from pysal import lat2W
        >>> w=lat2W(3,3)
        >>> w.asymmetry()
        []
        >>> w.transform='r'
        >>> result = w.asymmetry()[0:2]
        >>> print result[0]
        [1 3 0 2 4 1 5 0 4 6 1 3 5 7 2 4 8 3 7 4 6 8 5 7]
        >>> print result[1]
        [0 0 1 1 1 2 2 3 3 3 4 4 4 4 5 5 5 6 6 7 7 7 8 8]
        >>> neighbors={0:[1,2,3], 1:[1,2,3], 2:[0,1], 3:[0,1]}
        >>> weights={0:[1,1,1], 1:[1,1,1], 2:[1,1], 3:[1,1]}
        >>> w=W(neighbors,weights)
        >>> result = w.asymmetry()
        >>> print result[0]
        [1 0]
        >>> print result[1]
        [0 1]
        """

        wd=self.sparse.transpose()-self.sparse
        ids=np.nonzero(wd)
        if len(ids[0])==0:
            return []
        else:
            return ids


    def full(self):
        """
        Generate a full numpy array

        Returns
        -------

        implicit : tuple
                   first element being the full numpy array and second element
                   keys being the ids associated with each row in the array.



        Examples
        --------
        >>> from pysal import W
        >>> neighbors={'first':['second'],'second':['first','third'],'third':['second']}
        >>> weights={'first':[1],'second':[1,1],'third':[1]}
        >>> w=W(neighbors,weights)
        >>> wf,ids=w.full()
        >>> wf
        array([[ 0.,  1.,  0.],
               [ 1.,  0.,  1.],
               [ 0.,  1.,  0.]])
        >>> ids
        ['first', 'second', 'third']

        See also
        --------
        full
        """
        return util.full(self)


    def shimbel(self):
        """
        Find the Shmibel matrix for the first order contiguity matrix.
        
        Returns
        -------

        implicit : list of lists
                   one list for each observation which stores the shortest
                   order between it and each of the the other observations.

        Examples
        --------
        >>> from pysal import lat2W
        >>> w5=lat2W()
        >>> w5_shimbel=w5.shimbel()
        >>> w5_shimbel[0][24]
        8
        >>> w5_shimbel[0][0:4]
        [-1, 1, 2, 3]
        >>>

        See Also
        --------
        shimbel

        """
        return util.shimbel(self)


    def order(self,kmax=3):
        """
        Determine the non-redundant order of contiguity up to a specific
        order.

        Parameters
        ----------

        kmax    : int
                  maximum order of contiguity

        Returns
        -------

        implicit : dict
                   observation id is the key, value is a list of contiguity
                   orders with a negative 1 in the ith position


        Notes
        -----
        Implements the algorithm in Anselin and Smirnov (1996) [1]_


        Examples
        --------
        >>> from pysal import rook_from_shapefile as rfs
        >>> w=rfs('../examples/10740.shp')
        >>> w3=w.order()
        >>> w3[1][0:5]
        [1, -1, 1, 2, 1]

        References
        ----------
        .. [1] Anselin, L. and O. Smirnov (1996) "Efficient algorithms for
           constructing proper higher order spatial lag operators. Journal of
           Regional Science, 36, 67-89. 

        See also
        --------
        order

        """
        return util.order(self,kmax)


    def higher_order(self,k=3):
        """
        Contiguity weights object of order k 

        Parameters
        ----------

        k     : int
                order of contiguity

        Returns
        -------

        implicit : W
                   spatial weights object 


        Notes
        -----
        Implements the algorithm in Anselin and Smirnov (1996) [1]_

        Examples
        --------
        >>> from pysal import lat2W
        >>> w5=lat2W()
        >>> w5_shimbel=w5.shimbel()
        >>> w5_shimbel[0][24]
        8
        >>> w5_shimbel[0][0:4]
        [-1, 1, 2, 3]
        >>> w5_8th_order=w5.higher_order(8)
        >>> w5_8th_order.neighbors[0]
        [24]
        >>> from pysal import rook_from_shapefile as rfs
        >>> w=rfs('../examples/10740.shp')
        >>> w2=w.higher_order(2)
        >>> w[1]
        {0: 1.0, 2: 1.0, 83: 1.0, 4: 1.0}
        >>> w2[1]
        {3: 1.0, 5: 1.0, 6: 1.0, 10: 1.0, 82: 1.0, 85: 1.0, 91: 1.0, 92: 1.0, 101: 1.0}
        >>> w[147]
        {144: 1.0, 146: 1.0, 164: 1.0, 165: 1.0, 150: 1.0}
        >>> w[85]
        {0: 1.0, 101: 1.0, 83: 1.0, 84: 1.0, 90: 1.0, 91: 1.0, 93: 1.0}
        >>> 

        References
        ----------
        .. [1] Anselin, L. and O. Smirnov (1996) "Efficient algorithms for
           constructing proper higher order spatial lag operators. Journal of
           Regional Science, 36, 67-89. 

        See also
        --------
        higher_order
        """
        return util.higher_order(self,k)

class WSP(object):
    """
    Thin W class for spreg

    Parameters
    ----------

    n: int
       number of observations

    rows: list
       row indices for nonzero weights

    cols: list
       column indices for nonzero weights

    weights: list (optional)
       value of weights


    Examples
    --------

    From GAL information

    >>> w = WSP(4, [0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 3])
    >>> w.s0
    6.0
    >>> w.trcWtW_WW
    11.0
    >>> w.n
    4

    With weights specified

    >>> w = WSP(4, [0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 3], weights = [1, 0.75, 0.25, 0.9, 0.1, 1])
    >>> w.s0
    4.0
    >>> w.trcWtW_WW
    6.3949999999999996
    >>> w.n
    4

    
    """
    def __init__(self, n, row, col, weights = []):
        if not weights:
            weights = np.ones(len(row))
        self.sparse = sparse.csr_matrix((weights, (row,col)), shape = (n,n))
        self.n = n
        self._cache = {}

    @property
    def s0(self):
        """
        float

        .. math::

               s0=\sum_i \sum_j w_{i,j}

        """
        if 's0' not in self._cache:
            self._s0=self.sparse.sum()
            self._cache['s0']=self._s0
        return self._s0


    @property
    def trcWtW_WW(self):
        """
        trace of :math:`W^{'}W + WW`
        """
        if 'trcWtW_WW' not in self._cache:
            self._trcWtW_WW=self.diagWtW_WW.sum()
            self._cache['trcWtW_WW']=self._trcWtW_WW
        return self._trcWtW_WW

    @property
    def diagWtW_WW(self):
        """
        diagonal of :math:`W^{'}W + WW`
        """
        if 'diagWtW_WW' not in self._cache:
            wt=self.sparse.transpose()
            w=self.sparse
            self._diagWtW_WW=(wt*w+w*w).diagonal()
            self._cache['diagWtW_WW']=self._diagWtW_WW
        return self._diagWtW_WW


if __name__ == "__main__":

    import doctest
    doctest.testmod(verbose=False)
