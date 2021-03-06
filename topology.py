from __future__ import print_function
import random
from time import sleep
from router import *
import pdb

BLUE =  '\033[1;38;2;32;64;227m'
RED =   '\033[1;38;2;227;32;32m'
GREEN = '\033[0;38;2;0;192;0m'
YELLOW ='\033[0;38;2;192;192;0m'
NC =    '\033[0m'

############
# Basic Mesh
############
class Mesh:
    def __init__(self, x, y, connectAllLinks = False):
        self.X, self.Y = x, y
        if(connectAllLinks):
            self.routers = [[Router([j,i],[1,1,1,1]) for j in range(self.X)] for i in range(self.Y)]
        else:
            self.routers = [[Router([j,i],[0,0,0,0]) for j in range(self.X)] for i in range(self.Y)]
        
    # initialises the topology to with all healthy links
    def initialise(self):
        for i in range(self.Y):
            for j in range(self.X):
                if(i == 0 and j == 0):
                    self.routers[i][j].setLinkHealthList([1,0,0,1])
                elif (i == self.Y-1 and j == 0):
                    self.routers[i][j].setLinkHealthList([1,1,0,0])
                elif (i == 0 and j == self.X-1):
                    self.routers[i][j].setLinkHealthList([0,0,1,1])
                elif (i == self.Y-1 and j == self.X-1):
                    self.routers[i][j].setLinkHealthList([0,1,1,0])
                elif (i == 0 and (j > 0 and j < self.X-1)):
                    self.routers[i][j].setLinkHealthList([1,0,1,1])
                elif (i == self.Y-1 and (j > 0 and j < self.X-1)):
                    self.routers[i][j].setLinkHealthList([1,1,1,0])
                elif (j == 0 and (i > 0 and i < self.Y - 1)):
                    self.routers[i][j].setLinkHealthList([1,1,0,1])
                elif (j == self.X-1 and (i > 0 and i < self.Y-1)):
                    self.routers[i][j].setLinkHealthList([0,1,1,1])
                else:
                    self.routers[i][j].setLinkHealthList([1,1,1,1])

    # return the dimensions of the topology
    def getDimensions(self):
        return self.X, self.Y

    # get active (healthy) neighbours' positions
    # Although this seems like a method more suitable to the router class,
    # only the topology will store the dimensions of the grid.
    def getActiveNeighbourPositions(self, pos):
        x, y = pos
        X, Y = self.getDimensions()
        active = []
        linkHealths = self.routers[y][x].getHealthyLinksList()
        r, u, l, d = wrap(x+1,0,X-1), wrap(y-1,0,Y-1), wrap(x-1,0,X-1), wrap(Y+1,0,Y-1) 
        for link in range(4):
            if(linkHealths[link] == 1):
                if(link == 0):
                    active.append((r,y))
                elif(link == 1):
                    active.append((x,u))
                elif(link == 2):
                    active.append((l,y))
                else:
                    active.append((x,d))
        return active

    # returns active neighbouring Router instances
    def getActiveNeighbours(self, pos):
        x, y = pos
        X, Y = self.getDimensions()
        active = []
        linkHealths = self.routers[y][x].getHealthyLinksList()
        r, u, l, d = wrap(x+1,0,X-1), wrap(y-1,0,Y-1), wrap(x-1,0,X-1), wrap(y+1,0,Y-1) 
        for link in range(4):
            if(linkHealths[link] == 1):
                if(link == 0):
                    active.append(self.routers[y][r])
                elif(link == 1):
                    active.append(self.routers[u][x])
                elif(link == 2):
                    active.append(self.routers[y][l])
                else:
                    active.append(self.routers[d][x])
        return active

    # returns router at given address
    def routerAt(self, posx, posy):
        return self.routers[posy][posx]

    # returns relative direction of destination wrt source, written specifically for use in findPath()
    def getRelativeDirection(self, source, destination):
        # just get relative position without any link health checks
        # findPath() is already doing that to create children
        x1, y1 = source.getPosition()
        x2, y2 = destination.getPosition()
        if(y2 == y1):
            return 0 if x2>x1 else 2
        else:
            return 3 if y2>y1 else 1

    # calculates heuristic values for path-finding
    def heuristic(self, current, destination, direction):
        # Euclidean distance serves as fixed heuristic
        h = (((current[0]-destination[0])**2 + (current[1]-destination[1])**2)**0.5)
        
        # second heuristic depends on the direction of link that is chosen
        # X : direction can be 0 (right) or 2 (left), (1-direction) is adjusted along conventional X
        # y : direction can be 1 (up) or 3 (down), (2-direction) is adjusted along conventional Y
        # Destination is on = dest[0]-curr[0] > 0 ? right : left. (should give -1:1 for heuristic)
        # Destination is on = dest[1]-curr[1] > 0 ? down : up. (should give 1:-1 for heuristic)
        gx, gy = (0,0)
        currentRouter = self.routers[current[1]][current[0]]
        linkWeight = currentRouter.getLinkWeight(direction)
        if(destination[0] != current[0] and direction%2 == 0):
            gx = (1-direction)*linkWeight*(1 if (destination[0] - current[0] > 0) else 2)
        if(destination[1] != current[1] and direction%2 == 1):
            gy = (2-direction)*linkWeight*(2 if (destination[1] - current[1] > 0) else 1)
        g = gx + gy
        f = h+g
        # print("F: %.3f, H: %.3f, G: %.3f, LW: %d, Dir: %d" % (f,h,g,linkWeight,direction) + " | {0}-->{1}".format(current,destination))
        return g,h

    # for clearing the path info : used when searching for multiple paths in one run
    def clearPathInfo(self):
        for i in range(self.Y):
            for j in range(self.X):
                self.routers[i][j].setCostHeuristic(cost=0, heuristic=0)
                self.routers[i][j].parent = None


#################
# 2D Planar Torus
#################
class Torus:
    def __init__(self, x, y, connectAllLinks = True):
        self.X, self.Y = x, y
        if(connectAllLinks):
            self.routers = [[Router([j,i],[1,1,1,1]) for j in range(self.X)] for i in range(self.Y)]
        else:
            self.routers = [[Router([j,i],[0,0,0,0]) for j in range(self.X)] for i in range(self.Y)]

    # initialises the topology to with all healthy links
    def initialise(self):
        for i in range(self.Y):
            for j in range(self.X):
                self.routers[i][j].setLinkHealthList([1,1,1,1])
        return

    # returns the dimensions of the topology
    def getDimensions(self):
        return self.X, self.Y

    # returns active neighbouring Router instances
    def getActiveNeighbours(self, pos):
        x, y = pos
        X, Y = self.getDimensions()
        active = []
        linkHealths = self.routers[y][x].getHealthyLinksList()
        r, u, l, d = wrap(x+1,0,X-1), wrap(y-1,0,Y-1), wrap(x-1,0,X-1), wrap(y+1,0,Y-1) 
        for link in range(4):
            if(linkHealths[link] == 1):
                if(link == 0):
                    active.append(self.routers[y][r])
                elif(link == 1):
                    active.append(self.routers[u][x])
                elif(link == 2):
                    active.append(self.routers[y][l])
                else:
                    active.append(self.routers[d][x])
        return active

    # returns router at given address
    def routerAt(self, posx, posy):
        return self.routers[posy][posx]

    # returns relative direction of destination wrt source, written specifically for use in findPath()
    def getRelativeDirection(self, source, destination):
        # just get relative position without any link health checks
        # findPath() is already doing that to create children
        x1, y1 = source.getPosition()
        x2, y2 = destination.getPosition()
        # print((x2,y2),(x1,y1))
        # print(abs(x2-x1), self.getDimensions()[0], self.getDimensions()[0])
        if(x2>x1):
            return 2 if abs(x1-x2) == self.getDimensions()[0]-1 else 0
        elif(x2<x1):
            return 0 if abs(x1-x2) == self.getDimensions()[0]-1 else 2
        elif(y2>y1):
            return 1 if abs(y1-y2) == self.getDimensions()[1]-1 else 3
        else:
            return 3 if abs(y1-y2) == self.getDimensions()[1]-1 else 1

    # calculates heuristic values for path-finding
    def heuristic(self, current, destination, direction):
        # Euclidean distance calculated on a circular path serves as fixed heuristic
        dx,dy = 0,0
        if(destination[0] != current[0]):
            dx = min(destination[0]-current[0], destination[0]-current[0]-self.X)
        if(destination[1] != current[1]):
            dy = min(destination[1]-current[1], destination[1]-current[1]-self.Y)
        h = ((dx**2 + dy**2)**0.5)
        gx, gy = (0,0)
        currentRouter = self.routers[current[1]][current[0]]
        linkWeight = currentRouter.getLinkWeight(direction)
        if(destination[0] != current[0] and direction%2 == 0):
            gx = linkWeight*(1 if (destination[0] - current[0] > 0) else 2)
        if(destination[1] != current[1] and direction%2 == 1):
            gy = linkWeight*(2 if (destination[1] - current[1] > 0) else 1)
        # pdb.set_trace()
        g = gx + gy
        f = h+g
        print("F: %.3f, H: %.3f, G: %.3f, LW: %d, Dir: %d" % (f,h,g,linkWeight, direction) + " | {0}-->{1}".format(current,destination))
        return g,h

    # for clearing the path info : used when searching for multiple paths in one run
    def clearPathInfo(self):
        for i in range(self.Y):
            for j in range(self.X):
                self.routers[i][j].setCostHeuristic(cost=0, heuristic=0)
                self.routers[i][j].parent = None


###########################
# Common topology functions
###########################
def injectLinkFault(topology, pos, direction):
    X,Y = topology.getDimensions()
    j,i = pos   # position of the router
    if(j > X-1 or i > Y-1):
        raise IndexError("Index out of range for given topology")
        return False
    else:
        # return true only if the link was healthy before
        if(topology.routers[i][j].getHealthyLinksList()[direction] == 1):
            topology.routers[i][j].setLinkHealth(direction, 0)
            if(direction == 0):
                topology.routers[i][wrap(j+1,0,X-1)].setLinkHealth(2,0)
            elif(direction == 1):
                topology.routers[wrap(i-1,0,Y-1)][j].setLinkHealth(3,0)
            elif(direction == 2):
                topology.routers[i][wrap(j-1,0,X-1)].setLinkHealth(0,0)
            else:
                topology.routers[wrap(i+1,0,Y-1)][j].setLinkHealth(1,0)
            return True
        else:
            print("Already a fault!")
            return False

def injectRouterFault(topology, pos):
    X,Y = topology.getDimensions()
    j,i = pos   # position of the router
    if(j > X-1 or i > Y-1):
        raise IndexError("Index out of range for given topology")
        return False
    else:
        topology.routers[i][j].setLinkHealthList([0,0,0,0])
        # modify neighbours
        r, u, l, d = wrap(j+1,0,X-1), wrap(i-1,0,Y-1), wrap(j-1,0,X-1), wrap(i+1,0,Y-1) 
        topology.routers[i][l].setLinkHealth(0,0)
        topology.routers[d][j].setLinkHealth(1,0)
        topology.routers[i][r].setLinkHealth(2,0)
        topology.routers[u][j].setLinkHealth(3,0)
        
'''
Injects 'n' random faults

Works well for Torus, but not for Mesh.
The fault injection is basically a randomisation of link-healths.
Example Error: Vertex-routers in mesh 'might' get updated to 3 healthy links or 4 links
Keeping a macro for different topologies, a if-else is very simple to implement.
I'd prefer a general solution.

A workaround can be to target only healthy links and modify them, which has been implemented.
'''
def injectRandomLinkFaults(topology, n):
    X,Y = topology.getDimensions()
    # a 2D planar topology will have 2*M*N links. Mesh will have M+N-2 less links.
    if n > 2*X*Y:
        raise ValueError("Too many elements. No faults injected.")
        return
    faults = []
    original = [i for i in range(2*X*Y)]
    while (n > 0):
        try:
            # choose a random router
            choice = random.choice(original)
        except:
            print("Couldn't inject " + str(n) + " faults")
            return faults
        # get coordinates
        i = int(choice/(2*X))
        j = int((choice%(2*X))/2)
        link = int((choice%(2*X))%2)
        # check if the link is healthy
        if(topology.routers[i][j].getHealthyLinksList()[link] == 1):
            faults.append(((j,i), link))
            topology.routers[i][j].setLinkHealth(link, 0)
            if(link == 0):
                topology.routers[i][wrap(j+1,0,X-1)].setLinkHealth(2,0)
            elif(link == 1):
                topology.routers[wrap(i-1,0,Y-1)][j].setLinkHealth(3,0)
            elif(link == 2):
                topology.routers[i][wrap(j-1,0,X-1)].setLinkHealth(0,0)
            else:
                topology.routers[wrap(i+1,0,Y-1)][j].setLinkHealth(1,0)
            # remove choice and decrement counter
            original.remove(choice)
            n = n-1
        else:
            # remove choice
            original.remove(choice)
    if len(faults) > 0:
        return faults

def injectRandomRouterFaults(topology, n, animate=False, frameDelay=0.05):
    X,Y = topology.getDimensions()
    if n > X*Y:
        raise ValueError("Too many elements. No faults injected.")
        return
    original = [i for i in range(X*Y)]
    for k in range(n):
        # choose a random router
        choice = random.choice(original)
        # get coordinates
        i = int(choice/X)
        j = int(choice%X)
        # kill router
        topology.routers[i][j].setLinkHealthList([0,0,0,0])
        # modify neighbours
        r, u, l, d = wrap(j+1,0,X-1), wrap(i-1,0,Y-1), wrap(j-1,0,X-1), wrap(i+1,0,Y-1) 
        # print(j+1,i-1,j-1,i+1)
        # print(r, u, l, d)
        topology.routers[i][l].setLinkHealth(0,0)
        topology.routers[d][j].setLinkHealth(1,0)
        topology.routers[i][r].setLinkHealth(2,0)
        topology.routers[u][j].setLinkHealth(3,0)
        original.remove(choice)
        if(animate):
            printTopologyMap(topology, True)
            sleep(frameDelay)
            for c in range(2*Y):
                print("\033[F", end = '')
    if(animate):
        for i in range(2*Y):
            print("\033[E", end = '')

# find shortest path between two nodes
def findPath(topology, source, destination, pathWeight = 1, linkWeight = 1):
    # customary check
    if(source.isIsolated() or destination.isIsolated()):
        return ([], "inf")
    openList = []
    closedList = []
    pathCost = 0
    openList.append(source)
    while len(openList) > 0:
        # fetch current
        currentNode = openList[0]
        currentIndex = 0
        for index, item in enumerate(openList):
            if item.getCost() < currentNode.getCost():
                # print("Searching node "+str(item.getPosition()))
                currentNode = item
                currentIndex = index
        # pop off current from open and add to closed
        openList.pop(currentIndex)
        closedList.append(currentNode)

        # found goal
        if currentNode == destination:
            path = []
            current = currentNode
            # pdb.set_trace()
            while current is not None:
                # print(RED + str(current.getPosition()) + NC)                
                path.append(current.getPosition())
                pathCost = pathCost + current.getCost()
                current.setWeight(current.getWeight()*pathWeight)
                try:
                    direction = topology.getRelativeDirection(current, current.parent)
                except AttributeError:
                    pass
                else:
                    pdir = (direction+2)%4
                    current.parent.setLinkWeight(pdir, linkWeight*current.parent.getLinkWeight(pdir))
                    current.setLinkWeight(direction, linkWeight*current.getLinkWeight(direction))
                    # print(current.getPosition(), direction, current.getLinkWeight(direction))
                    # print(current.parent.getPosition(), pdir, current.parent.getLinkWeight(pdir), current.parent.getCostHeuristic())
                # pdb.set_trace()
                current = current.parent
            return (path[::-1], pathCost)

        # create children
        children = []
        for newNode in topology.getActiveNeighbours(currentNode.getPosition()):
            if(newNode.parent == None and newNode != source):
                newNode.parent = currentNode
            children.append(newNode)

        for child in children:
            # is this a valid way to check for child's availability in the closedList?
            if child in closedList:
                continue
            
            # generate heuristic values
            dx = child.getPosition()[0] - currentNode.getPosition()[0]
            dy = child.getPosition()[1] - currentNode.getPosition()[1]
            direction = topology.getRelativeDirection(currentNode, child)
            # heuristic is subjective to topology
            g,h = topology.heuristic(child.getPosition(),destination.getPosition(),direction)
            child.setCostHeuristic(cost=g, heuristic=h)

            for openNode in openList:
                # if child == openNode and child.getCost() > openNode.getCost():
                if child == openNode and child.getCostHeuristic()[1] > openNode.getCostHeuristic()[1]:
                    continue

            openList.append(child)
    # return nothing if no path found
    return ([], "inf")

# highlight a path in Green
# coloured outputs can get pretty ugly in terminals not supporting colour escape codes
def showPath(topology, path):
    for i in range(topology.Y):
        for j in range(topology.X):
            num = topology.routers[i][j].getHealthyLinksCount()
            linkRight = topology.routers[i][j].getHealthyLinksList()[0]
            if(j < topology.X-1):
                if (j,i) in path:
                    print(GREEN + str(num) + NC, end = "")
                # elif(num == 0):
                #     print(RED + str(num) + NC, end = "")
                # elif(num == 1):
                #     print(YELLOW + str(num) + NC, end = "")
                else:
                    print(str(num), end = "")
                print("---", end = "") if(linkRight == 1) else print("   ", end = "")    
            else:
                if (j,i) in path:
                    print(GREEN + str(num) + NC)
                # elif(num == 0):
                #     print(RED + str(num) + NC)
                # elif(num == 1):
                #     print(YELLOW + str(num) + NC)
                else:
                    print(num)
        for j in range(topology.X):
            if(i != topology.Y-1):
                linkDown = topology.routers[i][j].getHealthyLinksList()[3]
                print("|", end = "   ") if(linkDown == 1) else print("    ", end = "")
        print()

# prints topology in readable format
# coloured outputs can get pretty ugly in terminals not supporting colour escape codes
def printTopologyMap(topology, colour):
    for i in range(topology.Y):
        for j in range(topology.X):
            num = topology.routers[i][j].getHealthyLinksCount()
            linkRight = topology.routers[i][j].getHealthyLinksList()[0]
            if(j < topology.X-1):
                if colour:
                    if(num == 0):
                        print(RED + str(num) + NC, end = "")
                    elif(num == 1):
                        print(YELLOW + str(num) + NC, end = "")
                    else:
                        print(str(num), end = "")
                    print("---", end = "") if(linkRight == 1) else print("   ", end = "")
                else:
                    if(num == 0):
                        print(" ", end = "")
                    else:
                        print(str(num), end = "")
                    print("---", end = "") if(linkRight == 1) else print("   ", end = "")
            else:
                if colour:
                    if(num == 0):
                        print(RED + str(num) + NC)
                    elif(num == 1):
                        print(YELLOW + str(num) + NC)
                    else:
                        print(str(num))
                else:
                    if(num == 0):
                        print(" ")
                    else:
                        print(str(num))
        for j in range(topology.X):
            if(i != topology.Y - 1):
                linkDown = topology.routers[i][j].getHealthyLinksList()[3]
                print("|", end = "   ") if(linkDown == 1) else print("    ", end = "")
        print()

# helper function for dealing with wrap around links
def wrap(variable, minval, maxval):
    # I should use mod here but lite for now
    if(variable < minval):
        return maxval-(minval+variable+1)
    elif(variable > maxval):
        return minval+(variable-maxval-1)
    else:
        return variable
