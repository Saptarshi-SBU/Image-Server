#!/usr/bin/python
#
# Approximate string matching
#
# https://signal-to-noise.xyz/post/bk-tree/
#

from edit_distance import edit_distance

class BKNode(object):
    
    def __init__(self, text, parent=None):
        '''
            dist has edit-distance as key 
        '''
        self.dist = {}
        self.text = text
        self.parent = None

class BKTree(object):

    def __init__(self, text):
        self.root = BKNode(text)

    def add_node(self, text, parent=None):
        if parent is None:
            parent = self.root
        dist = edit_distance(text, parent.text, dp=True)
        if dist not in parent.dist:
            parent.dist[dist] = BKNode(text)
        else:
            self.add_node(text, parent.dist[dist])

    def lookup_node(self, node, threshold, r1, r2, result):
        assert node is not None
        child_nodes = { k : v for k, v in node.dist.iteritems() if k >= r1 and k <= r2 }
        for k in child_nodes:
            dist = edit_distance(self.query, child_nodes[k].text, dp=True)
            if dist <= threshold:
                result.append(child_nodes[k].text)
            self.lookup_node(child_nodes[k], threshold, dist - threshold, dist + threshold, result)    

    def approximate_match(self, text, threshold):
        match_list = []
        self.query = text
        dist = edit_distance(text, self.root.text, dp=True)
        self.lookup_node(self.root, threshold, dist - threshold, dist + threshold, match_list)
        return match_list


def CreateBkTree(word_list):
    bktree = BKTree(word_list[0])
    for i in range(1, len(word_list)):
        bktree.add_node(word_list[i])
    return bktree

def ApproximateMatch(bktree, pattern, threshold):    
    return bktree.approximate_match(pattern, threshold) 
