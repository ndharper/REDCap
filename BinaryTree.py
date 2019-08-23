# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 14:13:54 2019

@author: ndr15
"""

#from pythonds.trees import BinaryTree
#from pythonds.basic import Stack


class BinaryTree:
    """
    Based on example of 
    # Bradley N. Miller, David L. Ranum
    # Introduction to Data Structures and Algorithms in Python
    # Copyright 2005
    but added link to parent
    
    """
    
    def __init__(self,nodeValue):
        """
        brand new free standing node
        has whatever value was passed, no parent, no children
        
        """
        
        self.value=nodeValue        # 
        self.parent=None
        self.left=None
        self.right = None



   
    
    # get and set functions for value and children
    
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
        return self.left == None and self.right == None

    # move up one level
  
    def upTree(self):
        return self.parent
        
        
    # set functions.  There isn't one for parent.  Use insertLeftAbove or insertRightAbove
    
    def setValue(self,obj):
        self.value=obj          # can be any type of object
        
#    def setLeftChild(self,node):
#        if isinstance(node,BinaryTree): # adding a node or a tree
#            self.left = node
#        else:
#            self.left= BinaryTree(node) # adding some other object.  Create an new node below with value = to passed object
#            
#    def setRightChild(self,node):
#        if isinstance(node,BinaryTree): # adding a node or a tree
#            self.right = node
#        else:
#            self.right= BinaryTree(node) # adding some other object.  Create an new node below with value = to passed object           
            
    # find the top parent of a node.  Recusive, searches up the tree until it finds the top
    
    def findAncestor(self):
        if self.parent == None:
            return self
        else:
            node = self.parent
            return node.findAncestor()
        
    
    
    
    # insert node above the  current node.  Argument can be:
    # a parameter: create a leaf node with that value and insert between self and self's parent with
    #    new node pointing to self on the left or the right side.
    # a single node with no parent or children.  Insert between self and self's parent with the 
    #    inserted node hanging off the left or the right side
    #
    # 
    
    
    
    # left - create new node above with existing node hanging off left
    def insertAboveLeft(self, node):
        if isinstance(node,BinaryTree): # adding a node or a tree
            n=node
        else:
            n=BinaryTree(node)

        up = self.parent # the node above the insertion point
        if isinstance(up,BinaryTree):
                
            if up.left == self: # need to find if we are hanging of left or right side
                up.left = n # it's on the left so repoint at the new node
            elif up.right == self:
                up.right = n # on the right
            else:
                print('tree insert error: upstream doesn''t point to downstream',up,self)
                return                
              
        n.parent = up # now we're linked to te upstream side in both directions
        n.left = self
        self.parent = n # this completes the downstream linkage
        return n # returns the newly inserted node
    
    # right - create new node above with existing node hanging off right
    def insertAboveRight(self, node):
        if isinstance(node,BinaryTree): # adding a node or a tree
            n=node
        else:
            n=BinaryTree(node)


        up = self.parent # the node above the insertion point
        if isinstance(up,BinaryTree):   
            if up.left == self: # need to find if we are hanging of left or right side
                up.left = n # it's on the left so repoint at the new node
            elif up.right == self:
                up.right = n # on the right
            else:
                print('tree insert error: upstream doesn''t point to downstream',up,self)
                return                
        
        

        n.parent = up # now we're linked to te upstream side in both directions
        n.right = self
        self.parent = n # this completes the downstream linkage

        return n # returns the newly inserted node
    
        
    # insert nodes below current node.  Argument can be:
    # a parameter: create a leaf node with that value and insert between self and self's left or right child
    #    new node pointing to to self's child on the left or the right side.
    # a single node with no parent or children.  Insert between self and self's left or right child
    #    new node pointing to to self's child on the left or the right side.
    # 
    # 
      
    def insertBelowLeft(self,node):        
        if isinstance(node,BinaryTree): # adding a node or a tree
            n=node
        else:
            n=BinaryTree(node)
        
        if isinstance(self.left,BinaryTree):
            n.left = self.left                  # splice what's blow self
            self.left.parent = n                # onto the end of n
        
        
        n.left = self.left             # save downstream link on the left
        self.left = n 
        n.parent = self
        return n
    
    
    def insertBelowRight(self,node):        
        if isinstance(node,BinaryTree): # adding a node or a tree
            n=node
        else:
            n=BinaryTree(node)
        
        if isinstance(self.right,BinaryTree):
            n.right = self.right                  # splice what's blow self
            self.right.parent = n                # onto the end of n
        
        
        n.right = self.right                    # save downstream link
        self.right = n 
        n.parent = self
        return n
    
    # Insert for parsing algorithm.  This will insert the new node as right child
    # of the current node but will add the current node's old RIGHT child as the
    # LEFT child of the new node.  It will return the new node
    
    def insertBelowCross(self,node):
        if isinstance(node,BinaryTree): # adding a node or a tree
            n=node
        else:
            n=BinaryTree(node)
            
        n.parent = self             # set the parent of the new node
        if isinstance(self.right,BinaryTree):
            self.right.parent=n     # set the parent of the downstrem to be the new node
        
        n.left = self.right         # move the old right child.  May be None
        self.right = n              # now the current node points to new node
        
        
        
        return n                    # return the new node 
    
    
    
    # print out tree
    def print_tree(self):
        if self.parent==None:
            print('node is a root node')
        else:
            print('node''s parent',self.parent.value)
        
        print('node''s value',self.value)
        if isinstance(self.left,BinaryTree):
            print('node''s left branch')
            self.left.print_tree()
        if isinstance(self.right,BinaryTree):
            print('node''s right branch')
            self.right.print_tree()
                
        return




