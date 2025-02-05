#!/usr/bin/env python

""" MultiTree objects """

from collections import defaultdict
from .tree import Toytree
from .tree import COLORS
from . import ete3mini
import numpy as np
import requests
import toyplot
import copy
import re
import os


DEFAULTS_MULTITREE = {
    # edge defaults
    "edge_style": {
        "stroke": "#292724",
        "stroke-width": 2,
        # "stroke-linecap": "round",
        "opacity": 0.2,
        },

    "edge_align_style": {
        "stroke": "darkgrey",  # copies edge_style
        # "stroke-linecap": "round",
        "stroke-dasharray": "2, 4",
        },

    # node label defaults
    "node_labels": False,
    "node_labels_style": {
        "font-size": "9px",
        "fill": "262626"},

    # node defaults
    "node_size": None,
    "node_color": COLORS[0],
    "node_style": {
        "fill": COLORS[0],
        "stroke": COLORS[0],
        },
    "vmarker": "o",

    # tip label defaults
    "tip_labels": True,
    "tip_labels_color": toyplot.color.near_black,
    "tip_labels_align": False,
    "tip_labels_style": {
        "font-size": "12px",
        "text-anchor": "start",
        "-toyplot-anchor-shift": "12px",
        "fill": "#292724",
        },

    # tree style and axes
    "tree_style": "p",
}


###############################################
# MultiTree Class object
###############################################
class MultiTree(object):
    """
    Toytree MultiTree object for representing multiple trees.

    Attributes:
    -----------
    treelist: list
        A list of toytree objects from the parsed newick file

    Functions():
    ------------
    consenstree: str
        Returns a consenus tree object...

    """
    def __init__(self,
        newick,
        tree_format=None,
        treeslice=(None, None, None),
        skip=None,
        fixed_order=None,
        orient='down',
        use_edge_lengths=True,
        # root=None,
        ):

        # setting attributes
        self.newick = newick
        self.colors = COLORS
        self._ts = treeslice
        self._tformat = tree_format
        self._fixed_order = fixed_order
        self._orient = orient
        self._use_edge_lengths = use_edge_lengths
        self._kwargs = {}
        self._default_style = DEFAULTS_MULTITREE

        # parse the newick treefile
        self._parse_multinewick()


    # attributes of multitrees
    def __len__(self):
        return len(self.treelist)


    # private functions --------------------------------------------
    def _treelines_to_treelist(self, treelines):
        """
        Parses a multi-line newick file based on detected format
        to allow weird tree file types like the bpp outputs
        """
        # check if a bpp tree
        if (" #" in treelines[0]) and (": " in treelines[0]):
            self._tformat = "bpp"
        else:
            self._tformat = "normal"

        # badnewick to goodnewick
        if self._tformat == "bpp":
            treelines = [bpp2newick(i.strip()) for i in treelines]

        # if good newick to toytree
        if self._fixed_order:
            self.treelist = [Toytree(i.strip(), fixed_order=self._fixed_order)
                             for i in treelines]
        else:
            # order nodes for plotting
            self.treelist = [Toytree(i.strip()) for i in treelines]
            self._fixed_order = self.get_consensus_tree().get_tip_labels()[::-1]
            # redefine treelist with trees plotted in consensus tip order
            self.treelist = [
                Toytree(i.tree.write(), fixed_order=self._fixed_order)
                for i in self.treelist]


    def _parse_multinewick(self):
        """
        Parse a multiline newick from str, file, or url, and store
        new attributes to self for .newick, .tree_list, and ._tformat
        """

        # sample one line for testing --------------------------------
        # check if newick is a url
        if any(i in self.newick for i in ("http://", "https://")):
            try:
                response = requests.get(self.newick)
                response.raise_for_status()
                treelines = response.text.strip().split("\n")
                treelines = treelines[self._ts[0]:self._ts[1]:self._ts[2]]
                self._treelines_to_treelist(treelines)
            except Exception as inst:
                raise inst

        # check if newick is a file handle
        elif os.path.isfile(self.newick):
            self.newick = os.path.abspath(os.path.expanduser(self.newick))
            with open(self.newick) as infile:
                treelines = infile.read().split("\n")
                treelines = treelines[self._ts[0]:self._ts[1]:self._ts[2]]
                self._treelines_to_treelist(treelines)

        # assume remaining type is a str
        else:
            treelines = self.newick.strip().split("\n")
            treelines = treelines[self._ts[0]:self._ts[1]:self._ts[2]]
            self._treelines_to_treelist(treelines)


    def _set_dims_from_tree_size(self):
        """
        Calculate reasonable height and width for tree given N tips
        """
        tlen = len(self.treelist[0])
        if self._kwargs.get("orient") in ["right", "left"]:
            # long tip-wise dimension
            if not self._kwargs.get("height"):
                self._kwargs["height"] = max(275, min(1000, 18 * (tlen)))
            if not self._kwargs.get("width"):
                self._kwargs["width"] = max(225, min(500, 18 * (tlen)))
        else:
            # long tip-wise dimension
            if not self._kwargs.get("width"):
                self._kwargs["width"] = max(275, min(1000, 18 * (tlen)))
            if not self._kwargs.get("height"):
                self._kwargs["height"] = max(225, min(500, 18 * (tlen)))


    # public API functions of multitrees ------------
    def get_consensus_tree(self, cutoff=0.0):
        constre, clade_counts = consensus_tree(self.treelist, cutoff=cutoff)
        return Toytree(constre.write())


    def draw_cloudtree(self,
        axes=None,
        height=None,
        width=None,
        tip_labels=True,
        tip_labels_color=None,
        tip_labels_style=None,
        #tip_labels_align=False,
        node_labels=None, #False,
        node_labels_style=None,
        node_size=None,
        node_color=None,
        node_style=None,
        #edge_width=None,
        edge_style=None,
        edge_align_style=None,
        use_edge_lengths=True, #False,
        orient="down",
        tree_style="c",
        #print_args=False,
        #fixed_order=None,
        ):

        ## return nothing if tree is empty
        if not self.treelist:
            print("Tree is empty")
            return

        ## re-decompose tree for new orient and edges args
        for tidx in xrange(len(self.treelist)):
            #tre = self.treelist[tidx]
            self.treelist[tidx]._decompose_tree(
                orient=orient,
                use_edge_lengths=use_edge_lengths,
                fixed_order=self._fixed_order)

        ## stick all entered option into kwargs
        ## start from default styles copied
        self._kwargs = copy.deepcopy(self._default_style)
        entered = {
            "height": height,
            "width": width,
            "tip_labels": tip_labels,
            "tip_labels_color": tip_labels_color,
            "tip_labels_style": tip_labels_style,
            #"tip_labels_align": tip_labels_align,
            "node_labels": node_labels,
            "node_labels_style": node_labels_style,
            "node_size": node_size,
            "node_color": node_color,
            "node_style": node_style,
            #"edge_width": edge_width
            "edge_style": edge_style,
            "edge_align_style": edge_align_style,
            "tree_style": tree_style,
        }
        ## We don't allow the setting of None to update defaults.
        entered = {i:j for i,j in entered.items() if j != None}
        for key, val in entered.items():
            if val != None:
                if isinstance(val, dict):
                    self._kwargs[key].update(entered[key])
                else:
                    self._kwargs[key] = val
        ## if dims not set then guess a reasonable height & width
        self._set_dims_from_tree_size()
        #    self._kwargs["width"] = min(1000, 25*len(self.treelist[0].tree))
        #if not 
        #    self._kwargs["height"] = self._kwargs["width"]

        ## if not canvas then create one else use the existing
        if axes:
            canvas = None
        else:
            canvas = toyplot.Canvas(
                height=self._kwargs['height'],
                width=self._kwargs['width'],
                )
            axes = canvas.cartesian(
                #bounds=("10%", "90%", "10%", "90%"))
                padding=50,
                )
            axes.show = False


        ## plot trees
        for tre in self.treelist:
            _, axes = tre.draw(
                axes=axes,
                use_edge_lengths=use_edge_lengths,
                node_labels=False,
                orient=orient,
                tree_style=self._kwargs["tree_style"],
                edge_style=self._kwargs["edge_style"],
                tip_labels=False,
                )

        ## add tip labels
        angle = 0
        if orient == "down":
            angle = -90
        if tip_labels == True:
            self._kwargs["tip_labels"] = self._fixed_order
        if self._kwargs["tip_labels"]:
            axes.text(
                #tre.verts[-1*len(tre):, 0],
                #tre.verts[-1*len(tre):, 1],
                tre.verts[:len(tre), 0],
                tre.verts[:len(tre), 1],
                self._kwargs["tip_labels"],
                style=self._kwargs["tip_labels_style"],
                angle=angle,
            )

        return canvas, axes




# some functions called by Toytree class objects -----------------------

def consensus_tree(trees, names=None, cutoff=0.0):
    """
    An extended majority rule consensus function for ete.
    Modelled on the similar function from scikit-bio tree module. If
    cutoff=0.5 then it is a normal majority rule consensus, while if
    cutoff=0.0 then subsequent non-conflicting clades are added to the tree.
    """
    assert cutoff < 1, "cutoff should be a float proportion (e.g., 0.5)"

    ## find which clades occured with freq > cutoff
    namedict, clade_counts = _find_clades(trees, names=names)

    ## filter out the < cutoff clades
    fclade_counts = _filter_clades(clade_counts, cutoff)

    ## build tree
    consens_tree, _ = _build_trees(fclade_counts, namedict)
    ## make sure no singleton nodes were left behind
    return consens_tree, clade_counts



def _find_clades(trees, names):
    """
    A subfunc of consensus_tree(). Traverses trees to count clade
    occurrences. Names are ordered by names, else they are in
    the order of the first tree.
    """
    ## index names from the first tree
    if not names:
        names = trees[0].get_tip_labels() #leaf_names()
    ndict = {j:i for i, j in enumerate(names)}
    namedict = {i:j for i, j in enumerate(names)}

    ## store counts
    clade_counts = defaultdict(int)
    ## count as bitarray clades in each tree
    for tree in trees:
        #tree.tree.unroot()
        for node in tree.tree.traverse('postorder'):
            #bits = bitarray('0'*len(tree))
            bits = np.zeros(len(tree), dtype=np.bool_)
            for child in node.iter_leaf_names():
                bits[ndict[child]] = True
                #bits[ndict[child]] = 1
            bitstring = "".join([np.binary_repr(i) for i in bits])
            clade_counts[bitstring] += 1
            #clade_counts[bits.to01()] += 1

    ## convert to freq
    for key, val in clade_counts.items():
        clade_counts[key] = val / float(len(trees))

    ## return in sorted order
    clade_counts = sorted(clade_counts.items(),
                          key=lambda x: x[1],
                          reverse=True)
    return namedict, clade_counts



def _filter_clades(clade_counts, cutoff):
    """
    A subfunc of consensus_tree(). Removes clades that occur
    with freq < cutoff.
    """

    ## store clades that pass filter
    passed = []
    clades = np.array([list(i[0]) for i in clade_counts], dtype=np.int8)
    counts = np.array([i[1] for i in clade_counts], dtype=np.float64)

    for idx in xrange(clades.shape[0]):
        conflict = False

        if counts[idx] < cutoff:
            continue

        if np.sum(clades[idx]) > 1:
            # check the current clade against all the accepted clades to see if
            # it conflicts. A conflict is defined as:
            # 1. the clades are not disjoint
            # 2. neither clade is a subset of the other
            # OR:
            # 1. it is inverse of clade (affects only <fake> root state)
            # because at root node it mirror images {0011 : 95}, {1100 : 5}.
            for aidx in passed:
                #intersect = clade.intersection(accepted_clade)
                summed = clades[idx] + clades[aidx]
                intersect = np.max(summed) > 1
                subset_test0 = np.all(clades[idx] - clades[aidx] >= 0)
                subset_test1 = np.all(clades[aidx] - clades[idx] >= 0)
                invert_test = np.bool_(clades[aidx]) != np.bool_(clades[idx])

                if np.all(invert_test):
                    counts[aidx] += counts[idx]
                    conflict = True
                if intersect:
                    if (not subset_test0) and (not subset_test1):
                        conflict = True

        if conflict == False:
            passed.append(idx)

    ## rebuild the dict
    rclades = []#j for i, j in enumerate(clade_counts) if i in passed]
    ## set the counts to include mirrors
    for idx in passed:
        rclades.append((clades[idx], counts[idx]))
    return rclades



def _build_trees(fclade_counts, namedict):
    """
    A subfunc of consensus_tree(). Build an unrooted consensus tree
    from filtered clade counts.
    """

    ## storage
    nodes = {}
    idxarr = np.arange(len(fclade_counts[0][0]))
    queue = []

    ## create dict of clade counts and set keys
    countdict = defaultdict(int)
    for clade, count in fclade_counts:
        mask = np.int_(list(clade)).astype(np.bool)
        ccx = idxarr[mask]
        queue.append((len(ccx), frozenset(ccx)))
        countdict[frozenset(ccx)] = count

    while queue:
        queue.sort()
        (clade_size, clade) = queue.pop(0)
        new_queue = []

        # search for ancestors of clade
        for (_, ancestor) in queue:
            if clade.issubset(ancestor):
                # update ancestor such that, in the following example:
                # ancestor == {1, 2, 3, 4}
                # clade == {2, 3}
                # new_ancestor == {1, {2, 3}, 4}
                new_ancestor = (ancestor - clade) | frozenset([clade])
                countdict[new_ancestor] = countdict.pop(ancestor)
                ancestor = new_ancestor

            new_queue.append((len(ancestor), ancestor))

        # if the clade is a tip, then we have a name
        if clade_size == 1:
            name = list(clade)[0]
            name = namedict[name]
        else:
            name = None

        # the clade will not be in nodes if it is a tip
        children = [nodes.pop(c) for c in clade if c in nodes]
        node = ete3mini.Tree(name=name)
        #node = toytree.tree(name=name).tree
        for child in children:
            node.add_child(child)
        if not node.is_leaf():
            node.dist = int(round(100*countdict[clade]))
            node.support = int(round(100*countdict[clade]))
        else:
            node.dist = int(100)
            node.support = int(100)

        nodes[clade] = node
        queue = new_queue
    nodelist = list(nodes.values())
    tre = nodelist[0]
    #tre.unroot()
    ## return the tree and other trees if present
    return tre, nodelist



def bpp2newick(bppnewick):
    """
    converts bpp newick format to normal newick
    """
    regex1 = re.compile(r" #[-+]?[0-9]*\.?[0-9]*[:]")
    regex2 = re.compile(r" #[-+]?[0-9]*\.?[0-9]*[;]")
    regex3 = re.compile(r": ")
    new = regex1.sub(":", bppnewick)
    new = regex2.sub(";", new)
    new = regex3.sub(":", new)
    return new

