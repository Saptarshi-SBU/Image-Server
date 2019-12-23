# -*- coding: utf-8 -*-
#!/usr/bin/python

import sys

def edit_distance_recur(text, i, N, pattern, j, M, op):
    '''
        A recursive method to compute edit-distance.
        Complexity is exponential
    '''
    # base case
    if i >= N and j >= M:
        #print op
        return 0

    # exceeded text boundary
    if i >= N:
        return M - j #sys.maxint - 1

    # short pattern
    if j >= M:
        #print op + 'I' * (N -j)
        return N - i

    # substituition
    if text[i] != pattern[j]:
        subst = 1 + edit_distance_recur(text, i + 1, N, pattern, j + 1, M, op + 'S')
    else:
        subst = edit_distance_recur(text, i + 1, N, pattern, j + 1, M, op + 'M')
    #print 's={}'.format(subst)

    # deletion
    delete = 1 + edit_distance_recur(text, i, N, pattern, j + 1, M, op + 'D') 
    #print 'd={}'.format(delete)

    # insertion 
    insert = 1 + edit_distance_recur(text, i + 1, N, pattern, j, M, op + 'I')
    #print 'i={}'.format(insert)

    edits = min(subst, delete, insert)
    #print 's={} d={} t={} v={} i={} j={} op={}'.format(subst, delete, insert, edits, i, j, op)
    return edits

def edit_distance_dp(text, pattern):
    '''
        dynamic programming approach to compute edit-distance
        Complexity :O(MN)
    '''
    N = len(text)
    M = len(pattern)

    #create 2D array with rows of pattern elements and colums with text elements
    D = [ [] for x in range(M + 1) ]
    for i in range(len(D)):
        D[i] = [ N for x in range(N + 1) ]

    #super important, boundary values.
    #idea is for boundary conditions, the edit-distance computation is straight-forward
    #either append or delete. This is base case
    for j in range(N):
        D[M][j] = N - j
    for i in range(M):
        D[i][N] = M - i

    D[M][N] = 0

    for i in reversed(range(M)):

        for j in reversed(range(N)):

            #substituition
            if text[j] != pattern[i]:
                subst = 1 + D[i + 1][j + 1]
            else:
                subst = D[i + 1][j + 1]

            #deletion
            delete = 1 + D[i + 1][j]

            #insertion
            insert = 1 + D[i][j+ 1]

            #edit-distance
            D[i][j] = min(subst, delete, insert)
            #print 'i={} j={} ed={}'.format(i, j, D[i][j])

    return D[0][0]

def edit_distance(text, pattern, dp=False):
    '''
        public function
    '''    
    if dp:
        return edit_distance_dp(text, pattern)
    else:
        return edit_distance_recur(text, 0, len(text), pattern, 0, len(pattern), '')
