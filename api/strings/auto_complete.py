from string import ascii_lowercase
from .suffix_trie import SuffixTrie
from .edit_distance import edit_distance
from .bktree import CreateBkTree, ApproximateMatch

def AutoCorrect(tl, text, k=2):
    #tokenize
    tw = []
    for t in tl:
        tw.extend(t.split())
    #core
    dw = {}
    bktree = CreateBkTree(tw)
    nw = ApproximateMatch(bktree, text, k)
    for w in nw:
        d = edit_distance(text, w, dp=True)
        if d in dw:
            dw[d].append(w)
        else:
            dw[d] = [ w ]
    #order matches by distance
    nw = []
    for i in sorted(dw.keys()):
        nw.extend(dw[i])
    return nw

def AutoComplete(tl, text):
    result = []
    text = text.lower()
    suffix_trie = SuffixTrie()
    for t in tl:
        for i in reversed(range(len(t))):
            if t[i] in ascii_lowercase:
                suffix_trie.add(t[i:] + '$', tl.index(t))

    ti = suffix_trie.match(text)
    if len(ti) == 0 and len(text.split()) == 1:
        nw = AutoCorrect(tl, text)
        for t in nw:
            ti = suffix_trie.match(t)
            result.extend([tl[i] for i in ti if tl[i] not in result])
    else:
        result = [ tl[i] for i in ti ]
    return result
