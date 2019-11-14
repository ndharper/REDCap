from BinaryTree import BinaryTree

tree = BinaryTree('A')
tree.insertBelowLeft('B')
tree.insertBelowRight('C')
tree.left.insertBelowLeft('D')
tree.left.insertBelowRight('E')
tree.right.insertBelowLeft('D')
tree.right.insertBelowRight('E')

print(repr(tree))
print(str(tree))
print(tree)


def printTree(tree, depth=0):
    space = len(repr(tree))+1
    rtn = ''
    if tree.right:
        rtn += printTree(tree.right, depth + 1)
    rtn += '\n' +' ' * (space * depth) + repr(tree)
    if tree.left:
        rtn += printTree(tree.left, depth + 1)
    return rtn
