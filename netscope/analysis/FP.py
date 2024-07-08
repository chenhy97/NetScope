class TreeNode:
    def __init__(self, nodeName, count, nodeParent):
        self.nodeName = nodeName
        self.count = count
        self.nodeParent = nodeParent
        self.nextSimilarItem = None
        # self.prevSimilarItem = None
        self.children = {}

    def increaseC(self, count):
        self.count += count

    def display(self, ind=1):
        print(' | ' * ind, self.nodeName, self.count)
        for child in self.children.values():
            child.display(ind + 1)


def createFPTree(frozenDataSet):
    headPointTable = {}  # 头指针表 计数器
    for items in frozenDataSet:
        for item in items:
            headPointTable[item] = headPointTable.get(
                item, 0) + frozenDataSet[items]

    headPointTable = {k: [v, None] for k, v in headPointTable.items()}
    fptree = TreeNode("null", -1, None)  # 根节点

    # scan dataset at the second time, filter out items for each record
    for items, count in frozenDataSet.items():  # items 是一行数据
        frequentItemsInRecord = {}  # 针对于树的某一条分支的频繁项集
        for item in items:  # 一行中的每一项
            frequentItemsInRecord[item] = headPointTable[item][0]

        if len(frequentItemsInRecord) > 0:
            orderedFrequentItems = [v[0] for v in sorted(sorted(frequentItemsInRecord.items(), key=lambda x:x[0]),
                                                         key=lambda v:v[1], reverse=True)]
            updateFPTree(fptree, orderedFrequentItems, headPointTable, count)

    return fptree, headPointTable


def updateFPTree(fptree, orderedFrequentItems, headPointTable, count):
    '''fptree: 父节点
    @lin2020fast: alg2 FP-Tree Construction'''
    # handle the first item
    itemName = orderedFrequentItems[0]
    if itemName in fptree.children:
        fptree.children[itemName].increaseC(count)
    else:
        fptree.children[itemName] = TreeNode(itemName, count, fptree)
        # update headPointTable
        if headPointTable[itemName][1] == None:
            headPointTable[itemName][1] = fptree.children[itemName]
        else:
            updateHeadPointTable(
                headPointTable[itemName][1], fptree.children[itemName])

    # handle other items except the first item
    if (len(orderedFrequentItems) > 1):  # 继续递归
        updateFPTree(fptree.children[itemName],
                     orderedFrequentItems[1::], headPointTable, count)


def updateHeadPointTable(headPointBeginNode, targetNode):
    while(headPointBeginNode.nextSimilarItem != None):
        headPointBeginNode = headPointBeginNode.nextSimilarItem
    headPointBeginNode.nextSimilarItem = targetNode
#     targetNode.prevSimilarItem = headPointBeginNode


def mineFPTree(headPointTable, prefix, frequentPatterns, indexes=None, level=0):
    if indexes is None:
        indexes = []
    # global conditionalFPtreeTest
    # for each item in headPointTable, find conditional prefix path, create conditional fptree,
    # then iterate until there is only one element in conditional fptree
    headPointItems = [v[0] for v in sorted(
        headPointTable.items(), key=lambda v: v[1][0])]  # 升序，从小数还是遍历

    for headPointItem in headPointItems:
        newPrefix = prefix.copy()
        newPrefix.add(headPointItem)
        newIndexes = indexes.copy()
        newIndexes.append(headPointItem)

        support = headPointTable[headPointItem][0]  # 支持数/计数
        frequentPatterns[frozenset(newPrefix)] = support + \
            frequentPatterns.get(frozenset(newPrefix), 0)
        prefixPath = getPrefixPath(headPointTable, headPointItem)

        if prefixPath != {}:
            # 再建树
            conditionalFPtree, conditionalHeadPointTable = createFPTree(
                prefixPath)

            if conditionalHeadPointTable != None:
                # conditionalFPtreeTest = conditionalFPtree
                # 递归
                mineFPTree(conditionalHeadPointTable, newPrefix,
                           frequentPatterns, newIndexes, level + 1)  # 递归


def getPrefixPath(headPointTable, headPointItem):
    '''获取向上爬到根节点的所有前缀路径'''
    prefixPath = {}
    beginNode = headPointTable[headPointItem][1]  # treeNode
    prefixs = ascendTree(beginNode)
    if(prefixs != []):  # 不是根节点下第一个
        # 往上路径的count就是最底下那个node的count
        prefixPath[frozenset(prefixs)] = beginNode.count

    while(beginNode.nextSimilarItem != None):
        beginNode = beginNode.nextSimilarItem
        prefixs = ascendTree(beginNode)
        if (prefixs != []):
            prefixPath[frozenset(prefixs)] = beginNode.count
    return prefixPath


def ascendTree(treeNode):
    prefixs = []
    while((treeNode.nodeParent != None) and (treeNode.nodeParent.nodeName != 'null')):  # 直到根节点下第一个
        treeNode = treeNode.nodeParent
        prefixs.append(treeNode.nodeName)
    return prefixs
