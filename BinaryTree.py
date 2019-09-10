# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 14:13:54 2019

@author: ndr15
"""


class BinaryTree:
    """
    Based on example of
    Bradley N. Miller, David L. Ranum
    Introduction to Data Structures and Algorithms in Python
    Copyright 2005
    but added link to parent node and added functions for parse tree operation
    """

    def __init__(self, nodeValue):
        """
        brand new free standing node
        has whatever value was passed, no parent, no children
        """
        self.value = nodeValue
        self.parent = None
        self.left = None
        self.right = None

    # get functions for value and children

    def getValue(self):
        return self.value

    def getParent(self):
        return self.parent

    def getLeftChild(self):
        return self.left

    def getRightChild(self):
        return self.right

    # is it a leaf?
    def isLeaf(self):
        return self.left is None and self.right is None

    def upTree(self):
        """
        climb the tree by one level
        will return either the parent node or None if we're at the top
        """
        return self.parent

    # set functions.  There isn't one for parent.  Use insertLeftAbove or
    # insertRightAbove

    def setValue(self, obj):
        self.value = obj          # can be any type of object

    # return the top parent node of tree

    def findAncestor(self):
        if self.parent is None:
            return self
        else:
            node = self.parent
            return node.findAncestor()

    def insertAboveLeft(self, node):
        """
        insert node above the  current node.  Argument can be:
        a a node or some other object.  If parameteer isn't a node
        then function will create a leaf node with the passed object as
        its parameter.  In any case, the node will be inserted above the
        current node with the current node as left child of the new node.
        return the new node
        """
        if isinstance(node, BinaryTree):    # adding a node or a tree
            n = node
        else:
            n = BinaryTree(node)

        up = self.parent    # the node above the insertion point
        if isinstance(up, BinaryTree):
            # check which side of parent we're hanging off
            if up.left == self:
                up.left = n  # it's on the left so repoint at the new node
            elif up.right == self:
                up.right = n  # on the right
            else:
                print("tree insert error: upstream doesn't point"
                      "to downstream", up, self)
                return

        # now we're linked to the upstream side in both directions
        n.parent = up
        n.left = self
        self.parent = n  # this completes the downstream linkage
        return n  # returns the newly inserted node

    # right - create new node above with existing node hanging off right
    def insertAboveRight(self, node):
        """
        insert node above the  current node.    In any case, the node will be inserted above the
        current node with the current node as right child of the new node.
        return the new node
        """
        if isinstance(node, BinaryTree):  # adding a node or a tree
            n = node
        else:
            n = BinaryTree(node)

        up = self.parent  # the node above the insertion point
        if isinstance(up, BinaryTree):
            # need to find if we are hanging of left or right side
            if up.left == self:
                up.left = n  # it's on the left so repoint at the new node
            elif up.right == self:
                up.right = n  # on the right
            else:
                print("tree insert error: upstream doesn't point"
                      "to downstream", up, self)
                return

        # now we're linked upstream in both directions
        n.parent = up
        n.right = self
        self.parent = n  # this completes the downstream linkage
        return n  # returns the newly inserted node

    def insertBelowLeft(self, node):
        """
        insert a new node as left child of current node. Argument can be:
        a a node or some other object.  If parameteer isn't a node
        then function will create a leaf node with the passed object as
        its parameter.  Return the new node
        """
        if isinstance(node, BinaryTree):  # adding a node or a tree
            n = node
        else:
            n = BinaryTree(node)

        if isinstance(self.left, BinaryTree):
            n.left = self.left                  # splice what's blow self
            self.left.parent = n                # onto the end of n

        n.left = self.left             # save downstream link on the left
        self.left = n
        n.parent = self
        return n

    def insertBelowRight(self, node):
        """
        insert a new node as right child of current node. Argument can be:
        a a node or some other object.  If parameteer isn't a node
        then function will create a leaf node with the passed object as
        its parameter.  Return the new node
        """
        if isinstance(node, BinaryTree):  # adding a node or a tree
            n = node
        else:
            n = BinaryTree(node)

        if isinstance(self.right, BinaryTree):
            n.right = self.right                  # splice what's blow self
            self.right.parent = n                # onto the end of n

        n.right = self.right                    # save downstream link
        self.right = n
        n.parent = self
        return n

    def insertBelowCross(self, node):
        """
        Insert for parsing algorithm. This will insert the new node
        as right child of the current node but will add the current node's
        old RIGHT child as the LEFT child of the new node.
        It will return the new node
        """
        if isinstance(node, BinaryTree):  # adding a node or a tree
            n = node
        else:
            n = BinaryTree(node)

        n.parent = self             # set the parent of the new node
        if isinstance(self.right, BinaryTree):
            # set the parent of the downstrem to be the new node
            self.right.parent = n
        n.left = self.right         # move the old right child.  May be None
        self.right = n              # now the current node points to new node

        return n                    # return the new node

    def deleteNode(self):
        """
        Delete's the current node from the tree and connects its parent
        to its right child.  Returns pointer to the parent unless there
        isn't one, i.e. we're deleting the node at the top of the tree.
        In that case, returns a pointer to the right child.
        """
        if isinstance(self.parent, BinaryTree):  # top of the tree?
            node = self.parent      # no.  Move up to parent
            node.right = self.right  # now set pointer to deleted node's child
            if isinstance(node.right, BinaryTree):  # does child exist?
                node.right.parent = node  # yes, set it's parent
        else:   # at top of tree
            node = self.right   # return right child
            node.parent = None  # clear upstrean pointer
        return node

    def print_tree(self):
        """
        print out the whole tree from self downwards
        this function needs work to make the output more readable
        """
        if self.parent is None:
            print('node is a root node')
        else:
            print('node''s parent', self.parent.value)

        print('node''s value', self.value)
        if isinstance(self.left, BinaryTree):
            print('node''s left branch')
            self.left.print_tree()
        if isinstance(self.right, BinaryTree):
            print('node''s right branch')
            self.right.print_tree()

        return
