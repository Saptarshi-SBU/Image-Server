#!/usr/bin/python
#
# Suffix Trie
#

class TrieNode(object):

    def __init__(self, char):
        # character
        self.key = char
        # child nodes
        self.children = {}
        # terminal node
        if char == '$':
            self.leaf = True
        else:
            self.leaf = False
        # document index
        self.doc_index = []

    def set_doc_index(self, doc_index):
        self.doc_index.append(doc_index)

class SuffixTrie(object):

    def __init__(self):
        self.root = TrieNode(None)

    def add(self, string, doc_index):
        n = len(string)
        node = self.root

        for i in range(n):
            key = string[i]
            #print '==>', i, key, string, node.children.keys(), node.leaf
            # match
            if key in node.children:
                #print 'M', key
                node = node.children[key]
            else:
            # new char
                #print 'N', key
                node.children[key] = TrieNode(key)
                node = node.children[key]

            # terminal
            if i == n - 1:
                node.set_doc_index(doc_index)

    def match(self, pattern):
        '''
            drive pattern match
        '''
        docs = []
        node = self.root

        match = True
        for i in pattern:
            if i in node.children:
                node = node.children[i]
            else:
                match = False

        if match:
            stack = []
            stack.append(node)
            while len(stack) > 0:
                node = stack.pop()
                if node.leaf:
                    docs.extend([ x for x in node.doc_index if x not in docs ])
                else:
                    for key in node.children.keys():
                        stack.append(node.children[key])
        return docs

    def show(self, node=None, string=''):
        if node is None:
            node = self.root

        if node.leaf:
            print string, node.doc_index
            return

        #print node.children.keys()
        for i in node.children:
            self.show(node.children[i], string + i)
