from direct.showbase.ShowBase import ShowBase
import cv2
from pyzbar.pyzbar import decode
from panda3d.core import loadPrcFile
from panda3d.core import AmbientLight, PointLight, AmbientLight

from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode, CollisionHandlerPusher, CollisionPolygon, CollisionTube
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import TextNode, CollisionBox, Point3
from panda3d.core import LPoint3, LVector3, BitMask32, VBase4
from direct.gui.OnscreenText import OnscreenText, TextNode
from direct.showbase.DirectObject import DirectObject
from panda3d.core import Texture
from direct.task.Task import Task
import numpy as np
import sys
from panda3d.core import GeomNode, NodePath
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Geom, GeomNode, GeomVertexFormat, GeomVertexData
from panda3d.core import GeomTriangles, GeomVertexWriter
from panda3d.core import LVector3, OrthographicLens, PerspectiveLens, Camera, CollisionSphere
from panda3d.core import Point3, LineSegs
from direct.interval.LerpInterval import LerpFunc, LerpPosInterval
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectCheckButton
from direct.gui.DirectGui import *
from enum import Enum
from math import sin, pi

loadPrcFile('settings.prc')                             # Stand der dinge: limit mouse movement in der limit() function fir net rechte winkel
class Config:
    ROOM_CORNERS = {
        'tl': LVector3(-20, 20, 11),
        'tr': LVector3(20, 20, 11),
        'bl': LVector3(-20, -20, 11),
        'br': LVector3(20, -20, 11),
        '_tl': LVector3(-20, 20, -11),
        '_tr': LVector3(20, 20, -11),
        '_bl': LVector3(-20, -20, -11),
        '_br': LVector3(20, -20, -11)
    }

class CameraState(Enum):
    SIDE = 0
    BIRD_EYE = 1

class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        self.init_Buttons_and_Interfaces()
        
        self.init()
        self.collision_setup()
        self.createRoom()
        self.control()
        self.accept('space', self.toggleTransition)
        self.set_lights()
        self.add_instructions()

        self.accept('q', self.startWebcam)
        self.accept("r", self.start_rotation)
        self.accept("r-up", self.stop_rotation)
        self.accept("e", self.rotation)

        self.transitionUp.setDoneEvent("transitionUpCompleted")
        self.transitionDown.setDoneEvent("transitionDownCompleted")
        self.accept("transitionUpCompleted", self.onTransitionUpCompleted)
        self.accept("transitionDownCompleted", self.onTransitionDownCompleted)
        #self.create_furniture("S10-0400.glb")       #S10-0400.glb       55003551.glb
        #self.create_furniture("55003551.glb")
        self.create_furniture("M45-0800-43180.glb")

        self.BMInterface()           # do stian geblieben. andern zu one time call und a nuien taskmanager der sie updated
        
    def init(self):
        self.disableMouse()
        self.state = CameraState.BIRD_EYE
        self.lastMouseX = None
        self.orbit = 90                     # Camera orbit
        self.tl = Config.ROOM_CORNERS['tl']    # up, _ = down
        self.tr = Config.ROOM_CORNERS['tr']
        self.bl = Config.ROOM_CORNERS['bl']
        self.br = Config.ROOM_CORNERS['br']
        self._bl = Config.ROOM_CORNERS['_bl']
        self._br = Config.ROOM_CORNERS['_br']
        self._tl = Config.ROOM_CORNERS['_tl']
        self._tr = Config.ROOM_CORNERS['_tr']
        
        self.sides = [[self.bl, self.tl], [self.tl, self.tr], [self.br, self.tr], [self.br,self.bl]]
        self.stopPos = False
        self.tubsphPaths = []

        self.dragbl = False
        self.dragtl = False
        self.dragbr = False
        self.dragtr = False
        self.draglw = False
        self.dragtw = False
        self.dragrw = False
        self.dragbw = False

        self.dragging = False
        self.collision_node = False
        self.mouseTask = taskMgr.add(self.mouseTask, 'mouseTask')
        self.accept('mouse1', self.grabItem)
        self.accept('mouse1-up', self.releaseItem)
        self.accept('mouse3', self.onRightMousePress)
        self.accept('mouse3-up', self.onRightMouseRelease)
        self.accept('wheel_up', self.zoomIn)
        self.accept('wheel_down', self.zoomOut)

        self.startH = 45
        self.vid = False
        self.furniture = []
        self.BMode = self.toggleButton['indicatorValue']
        self.lensBM = OrthographicLens()
        aspect_ratio = base.win.getXSize() / base.win.getYSize()
        self.lensBM.setFilmSize(60 * aspect_ratio, 60)
        self.lens = PerspectiveLens()
        self.lens.setFov(base.camLens.getFov())
        self.lens.setNear(base.camLens.getNear())
        self.lens.setFar(base.camLens.getFar())
        self.grid = True
        self.transitionBlock = False
        self.lineNodePaths = []
    
    def init_Buttons_and_Interfaces(self):
        def cameraTransitionUp(t):
            self.transitionBlock = True
            rotation = 90*sin(pi * t/2)  # Adjust as necessary
            self.pivot.setP(rotation)
        # Define the downward transition function
        def cameraTransitionDown(t):
            self.transitionBlock = True
            rotation = 90*sin(pi * (1 - t/2))  # Adjust as necessary
            self.pivot.setP(rotation)
        
        self.transitionUp = LerpFunc(
            cameraTransitionUp,
            fromData=1,
            toData=0,
            duration=1.5  # Duration in seconds
        )
        self.transitionDown = LerpFunc(
            cameraTransitionDown,
            fromData=0,
            toData=1,
            duration=1.5  # Duration in seconds
        )

        self.toggleButton = DirectCheckButton(
            text="Builder Mode",
            scale=0.05,
            pos=(1, 0, .8),
            indicatorValue = 1,
            command=self.toggleBM
        )

        self.gridButton = DirectCheckButton(
            text="Toggle Grid",
            scale=0.05,
            pos=(1, 0, .7),
            indicatorValue = 1,
            command=self.toggleGrid
        )

    def control(self):
        self.pivot = self.render.attachNewNode("Pivot")
        camera.setPos(self.pivot, 0, 0, self.orbit)
        camera.reparentTo(self.pivot)
        camera.lookAt(0, 0, 5)
        self.camNode.setLens(self.lensBM)

    def createRoom(self):
        # Create a single node for all walls
        self.roomNode = self.render.attachNewNode("Room")

        # Create individual walls
        self.createWall(self.bl, self.tl, self._bl, self._tl, (1,0,0,1))
        self.createWall(self.tr, self.br, self._tr, self._br, (0,1,0,1))
        self.createWall(self.br, self.bl, self._br, self._bl, (0,0,1,1))
        self.createWall(self.tl, self.tr, self._tl, self._tr, (1,1,0,1))
        self.createWall(self._br, self._bl, self._tr, self._tl, (1,0,1,1), walls=False)
        self.createWall(self.bl, self.br, self.tl, self.tr, (0,1,1,1), walls=False)

    def createWall(self, p1, p2, p3, p4, color, walls = True):
        format = GeomVertexFormat.getV3c4()
        vdata = GeomVertexData('wall', format, Geom.UHDynamic)

        vertex = GeomVertexWriter(vdata, 'vertex')
        vertexColor = GeomVertexWriter(vdata, 'color')

        vertices = [p1, p2, p3, p4]
        for vert in vertices:
            vertex.addData3(vert)
            vertexColor.addData4(color)


        tris = GeomTriangles(Geom.UHDynamic)
        tris.addVertices(0, 2, 1)
        tris.addVertices(1, 2, 3)
        polygon = CollisionPolygon(p3, p4, p2, p1)

        wall = Geom(vdata)
        wall.addPrimitive(tris)
        wallNode = GeomNode('wall')
        wallNode.addGeom(wall)

        cnode = CollisionNode('wall_cnode')
        cnode.addSolid(polygon)

        cnode.setIntoCollideMask(BitMask32.bit(2))
        cnode.setFromCollideMask(BitMask32.allOff())

        wallNodePath = NodePath(wallNode)
        self.cnodePath = wallNodePath.attachNewNode(cnode)
        self.picker.addCollider(self.cnodePath, self.pq)
        
        if walls:
            colTube = CollisionTube(p1, p3, 0.5)
            dNode = CollisionNode('wall_dNode')
            dNode.addSolid(colTube)
            dNode.setIntoCollideMask(BitMask32.bit(1))
            dNode.set_from_collide_mask(0)
            dNodePath = wallNodePath.attachNewNode(dNode)
            self.picker.addCollider(dNodePath, self.pq)
            self.tubsphPaths.append(dNodePath)
        
            pAvg = (p1 + p2 + p3 + p4) / 4
            
            sphere = CollisionSphere(pAvg.x, pAvg.y, pAvg.z, 0.5)
            sphereNode = CollisionNode('wall_sphere')
            sphereNode.addSolid(sphere)
            sphereNode.setIntoCollideMask(BitMask32.bit(1))
            sphereNode.set_from_collide_mask(0)
            sphereNodePath = wallNodePath.attachNewNode(sphereNode)
            self.picker.addCollider(sphereNodePath, self.pq)
            self.tubsphPaths.append(sphereNodePath)

        self.roomNode.attachNewNode(wallNode)
        return

    def moveCorner(self, corner, x, y):
        for corner in corner:
            if self.grid:
                corner.setX(self.gridLock(x))
                corner.setY(self.gridLock(y))
            else:
                corner.setX(x)
                corner.setY(y)
        
        self.roomNode.removeNode()
        self.createRoom()
        self.BMInterface()
    
    def moveWall(self, wall, x, y):
        if self.draglw or self.dragrw:
            diff_x = x - self.stopPos[0].x
            for i, point in enumerate(wall):
                if self.grid:
                    point.setX(self.gridLock(point.x + diff_x))
                else:
                    point.setX(point.x + diff_x)

            self.stopPos = [point for point in wall]

        elif self.dragbw or self.dragtw:
            diff_y = y - self.stopPos[0].y
            for i, point in enumerate(wall):
                if self.grid:
                    point.setY(self.gridLock(point.y + diff_y))
                else:
                    point.setY(point.y + diff_y)
            
            self.stopPos = [point for point in wall]
        
        self.roomNode.removeNode()
        self.createRoom()
        self.BMInterface()
    
    def toggleGrid(self, status):
        self.grid = status

    def gridLock(self, x):
        grid = 5
        return round(x / grid) * grid

    def toggleTransition(self):
        if self.state == CameraState.SIDE and not self.transitionBlock:
            self.transitionUp.start()
            
        elif self.state == CameraState.BIRD_EYE and not self.transitionBlock:
            self.transitionDown.start()
            self.state = CameraState.SIDE
            
    def onTransitionUpCompleted(self):
        self.transitionBlock = False
        self.state = CameraState.BIRD_EYE

    def onTransitionDownCompleted(self):
        self.transitionBlock = False

    def set_lights(self):
        mainLight = PointLight('main light')
        mainLightNodePath = render.attachNewNode(mainLight)
        mainLightNodePath.setPos(0, 0, 19)
        mainLight.setColor(VBase4(1.9, 1.82, 1.33, 1))
        render.setLight(mainLightNodePath)

        ambientLight = AmbientLight('ambient light')
        ambientLight.setColor(VBase4(0.1, 0.1, 0.1, .8))
        ambientLightNodePath = render.attachNewNode(ambientLight)
        render.setLight(ambientLightNodePath)


    def create_furniture(self, model_path):
        object = loader.loadModel(model_path)  # Assuming you have a box model
        object.reparentTo(render)

        minPoint, maxPoint = object.getTightBounds()
        collisionBox = CollisionBox(minPoint, maxPoint)

        dragNode = CollisionNode(f'dragfur')
        dragNode.addSolid(collisionBox)
        dragNode.setIntoCollideMask(BitMask32.bit(1))
        dragNode.set_from_collide_mask(0)
        dragNodePath = object.attachNewNode(dragNode)
        self.picker.addCollider(dragNodePath, self.pq)

        model_copy = object.copy_to(base.render)
        model_copy.detach_node()
        # "bake" the transformations into the vertices
        model_copy.flatten_light()

        # create root node to attach collision nodes to
        collision_root = NodePath("collision_root")
        collision_root.reparent_to(object)

        combined_collision_node = CollisionNode("combined_collision")
        combined_collision_mesh = collision_root.attach_new_node(combined_collision_node)

        # create a collision mesh for each of the loaded models
        for model in model_copy.find_all_matches("**/+GeomNode"):
            model_node = model.node()

            # Calculate the bounding box for the entire GeomNode
            min_bound, max_bound = model.getTightBounds()
            
            # Create a collision box using the bounds
            coll_box = CollisionBox(min_bound, max_bound)
            combined_collision_node.addSolid(coll_box)

        combined_collision_node.setFromCollideMask(BitMask32.bit(2))
        combined_collision_node.setIntoCollideMask(BitMask32.bit(2))
        combined_collision_mesh.show()

        # Add the combined collider to the pusher and picker
        self.pusher.addCollider(combined_collision_mesh, object)
        self.picker.addCollider(combined_collision_mesh, self.pusher)
        self.furniture.append(object)

    def collision_setup(self):
        self.picker = CollisionTraverser()
        self.pq = CollisionHandlerQueue()
        self.pusher = CollisionHandlerPusher()

        self.picker.setRespectPrevTransform(True)

        self.pickerNode = CollisionNode('mouseRay')
        self.pickerNP = camera.attachNewNode(self.pickerNode)
        self.pickerNode.setFromCollideMask(BitMask32.bit(1))
        self.pickerRay = CollisionRay()
        self.pickerNode.addSolid(self.pickerRay)
        self.picker.addCollider(self.pickerNP, self.pq)



    def mouseTask(self, task):
        def setlimit(x,y):
            x = min(x, self.tr.getX())
            x = max(x, self.tl.getX())
            y = min(y, self.tl.getY())
            y = max(y, self.bl.getY())

            print(x,y)
            return x,y
        if self.state == CameraState.BIRD_EYE:

            if self.BMode:
                for i in range(len(self.tubsphPaths)):
                    self.tubsphPaths[i].show()
                self.transitionBlock = True
            else:
                for i in range(len(self.tubsphPaths)):
                    self.tubsphPaths[i].hide()
                self.transitionBlock = False

            if self.mouseWatcherNode.hasMouse():  
                self.mpos = self.mouseWatcherNode.getMouse()
                self.pickerRay.setFromLens(self.camNode, self.mpos.getX(), self.mpos.getY())
                nearPoint = render.getRelativePoint(
                    camera, self.pickerRay.getOrigin())
                nearVec = render.getRelativeVector(
                    camera, self.pickerRay.getDirection())
                newPos = PointAtZ(.5, nearPoint, nearVec)
            
                if self.dragging : 
                    taskMgr.remove("mouseDragTask")
                    if not hasattr(self, 'prevPos'):
                        self.prevPos = self.dragging.getPos()
                    if not hasattr(self, 'rotate'):
                        self.rotate = False

                    if self.prevPos and newPos:
                        base_speed = 0
                        acceleration_factor = 10
                        x,y = setlimit(newPos.x,newPos.y)
                        effPos = Point3(x,y, 0.5)
                        direction = effPos - self.prevPos
                        distance = direction.length()
                        
                        speed = base_speed + distance * acceleration_factor
                        if speed > 60:
                            speed = 60
                        direction.normalize()

                        # Calculate the movement for this frame
                        movement = direction * speed * globalClock.getDt()

                        self.dragging.setFluidPos(self.dragging.getPos() + movement)

                        # Update previous position
                        self.prevPos = self.dragging.getPos()
                    
                    if self.rotate:
                        self.dragging.setH(self.dragging.getH() + 1)

                if self.collision_node:
                    for i in range(self.collision_node.getNumSolids()):
                        solid = self.collision_node.getSolid(i)
                        
                        if isinstance(solid, CollisionTube):
                            v1 = LVector3(solid.getPointA())
                    
                            if v1 == self.bl:
                                self.dragbl = True
                            elif v1 == self.tl:
                                self.dragtl = True
                            elif v1 == self.br:
                                self.dragbr = True
                            elif v1 == self.tr:
                                self.dragtr = True
                        
                        if isinstance(solid, CollisionSphere):
                            pCh1 = (self.bl + self.tl + self._bl + self._tl) / 4
                            pCh2 = (self.br + self.tr + self._br + self._tr) / 4
                            pCh3 = (self.bl + self.br + self._bl + self._br) / 4
                            pCh4 = (self.tl + self.tr + self._tl + self._tr) / 4

                            if solid.getCenter() == pCh1:
                                self.draglw = True
                                if not self.stopPos:
                                    self.stopPos = [LVector3(self.bl), LVector3(self.tl), LVector3(self._bl), LVector3(self._tl)]
                            elif solid.getCenter() == pCh2:
                                self.dragrw = True
                                if not self.stopPos:
                                    self.stopPos = [LVector3(self.br), LVector3(self.tr), LVector3(self._br), LVector3(self._tr)]
                            elif solid.getCenter() == pCh3:
                                self.dragbw = True
                                if not self.stopPos:
                                    self.stopPos = [LVector3(self.bl), LVector3(self.br), LVector3(self._bl), LVector3(self._br)]
                            elif solid.getCenter() == pCh4:
                                self.dragtw = True
                                if not self.stopPos:
                                    self.stopPos = [LVector3(self.tl), LVector3(self.tr), LVector3(self._tl), LVector3(self._tr)]

                    if self.dragbl:
                        self.moveCorner([self.bl,self._bl], newPos.getX(), newPos.getY())
                    elif self.dragtl:
                        self.moveCorner([self.tl,self._tl], newPos.getX(), newPos.getY())
                    elif self.dragbr:
                        self.moveCorner([self.br,self._br], newPos.getX(), newPos.getY())
                    elif self.dragtr:
                        self.moveCorner([self.tr,self._tr], newPos.getX(), newPos.getY())
                    elif self.draglw:
                        self.moveWall([self.bl,self._bl, self.tl, self._tl], newPos.getX(), newPos.getY())
                    elif self.dragrw:
                        self.moveWall([self.br,self._br, self.tr, self._tr], newPos.getX(), newPos.getY())
                    elif self.dragbw:
                        self.moveWall([self.bl,self._bl, self.br, self._br], newPos.getX(), newPos.getY())
                    elif self.dragtw:
                        self.moveWall([self.tl,self._tl, self.tr, self._tr], newPos.getX(), newPos.getY())

                else:
                    self.dragbl = False
                    self.dragtl = False
                    self.dragbr = False
                    self.dragtr = False
                    self.draglw = False
                    self.dragrw = False
                    self.dragbw = False
                    self.dragtw = False
                    self.stopPos = False

                self.picker.traverse(render)
                if self.pq.getNumEntries() > 0:
                    self.pq.sortEntries()

        elif self.BMode:
            self.toggleButton['indicatorValue'] = False
            self.BMode = False
        return Task.cont
    
    def startWebcam(self):
        self.vid = True
        cap = cv2.VideoCapture(0)
        while self.vid:
            ret,frame = cap.read()
            if ret:
                self.data = self.decoder(frame)
            if self.data:
                if "55003551" in str(self.data):
                    self.create_furniture("55003551.glb")
                elif "M45-0800-43180" in str(self.data):
                    self.create_furniture("M45-0800-43180.glb")
                elif "S10-0400" in str(self.data):
                    self.create_furniture("S10-0400.glb")
                else:
                    print("No matching furniture found")
            cv2.imshow('image',frame)
            # Check for 'e' key press to exit the webcam feed
            if cv2.waitKey(1) & 0xFF == 27:
                print("exiting webcam")
                self.vid = False
        cap.release()
        cv2.destroyAllWindows()

    def decoder(self, img):
        detectedBarcodes = decode(img)
        
        # If not detected then print the message
        if detectedBarcodes:
            for barcode in detectedBarcodes: 
            
                # Locate the barcode position in image
                (x, y, w, h) = barcode.rect
                
                # Put the rectangle in image using 
                # cv2 to highlight the barcode
                cv2.rectangle(img, (x-10, y-10),
                            (x + w+10, y + h+10), 
                            (255, 0, 0), 2)
                
                if barcode.data!="":
                
                # Print the barcode data
                    print(barcode.data)
                    print(barcode.type)
                    self.vid = False
                    return barcode.data

    def start_rotation(self):
        self.rotate = True

    def stop_rotation(self):
        self.rotate = False

    def rotation(self):
        if self.dragging:
            angle = self.dragging.getH()%360
            if angle >= 0 and angle < 90:
                self.dragging.setH(90)
            elif angle >= 90 and angle < 180:
                self.dragging.setH(180)
            elif angle >= 180 and angle < 270:
                self.dragging.setH(270)
            elif angle >= 270 and angle < 360:
                self.dragging.setH(0)
    

    def grabItem(self):
        if self.pq.getNumEntries() > 0:
            if "dragfur" in self.pq.getEntry(0).getIntoNodePath().getName():
                self.dragging = self.pq.getEntry(0).getIntoNodePath().getParent()
                self.movObject = self.pq.getEntry(0).getIntoNodePath()
                self.transitionBlock = True
            elif self.BMode:
                self.collision_node = self.pq.getEntry(0).getIntoNodePath().node()

    def releaseItem(self):
        self.dragging = False
        self.transitionBlock = False
        self.collision_node = False
    
    def onRightMousePress(self):
        if self.lastMouseX is None:
            self.lastMouseX = self.mouseWatcherNode.getMouse().getX()
            taskMgr.add(self.mouseDragTask, "mouseDragTask")

    def onRightMouseRelease(self):
        taskMgr.remove("mouseDragTask")
        self.lastMouseX = None

    def mouseDragTask(self, task):
        speed = -50
        if self.lastMouseX:
            mpos = self.mouseWatcherNode.getMouse()
            pivotRot = self.pivot.getH() + (mpos.getX() - self.lastMouseX) * speed
            self.pivot.setH(pivotRot)
            self.lastMouseX = mpos.getX()
        return Task.cont

    def add_instructions(self):
        self.bmsg = "Builder Mode active\nClick Button to end"
        self.msg = "Q: Start webcam\nE: Rotate 90\nR: Start rotation\nSpace: Switch view\nMouse Right: Move camera\nMouse Left: Drag furniture\nMouse wheel: Zoom in/out"
        pos = 0.06, 0.06
        self.text = OnscreenText(text=self.bmsg, parent=self.a2dTopLeft, scale=.05, 
                            pos=(pos[0], -pos[1] - 0.04), fg=(1, 1, 1, 0.7),
                            align=TextNode.ALeft, shadow=(0, 0, 0, 0.5))
        return
    
    def zoomIn(self):
        if self.orbit > 20:
            self.orbit -= 4
            camera.setFluidPos(self.pivot, 0, 0, self.orbit)

    def zoomOut(self):
        if self.orbit < 150:
            self.orbit += 4
            camera.setFluidPos(self.pivot, 0, 0, self.orbit)

    def toggleBM(self, status):
        if status:
            self.BMode = True
            self.text.setText(self.bmsg)
            self.BMInterface()
            self.camNode.setLens(self.lensBM)
            self.gridButton['state'] = DGG.NORMAL
            
        else:
            self.BMode = False
            self.text.setText(self.msg)
            self.BMInterface()
            self.camNode.setLens(self.lens)
            self.gridButton['state'] = DGG.DISABLED

    def BMInterface(self):
        for lineNodePath in self.lineNodePaths:
            lineNodePath.removeNode()

        self.lineNodePaths.clear()  # Clear the list
        if self.BMode:
            def calc(start, end):
                midpoint = (start.x + end.x) / 2, (start.y + end.y) / 2, (start.z + end.z) / 2
                lenght = (start - end).length()
                return (midpoint,lenght)

            self.lines = LineSegs()
            self.lines.setColor(1, 1, 1, 1)
            self.lines.setThickness(3)
            text_offset = -3, 4

            for i,side in enumerate(self.sides):
                midpoint, lenght = calc(side[0], side[1])

                # Create a text node and set its properties
                text = TextNode('line_label')
                text.setText("{:.2f}".format(lenght))
                offset = text.getWidth()
                textNodePath = render.attachNewNode(text)

                if i%2 == 0:
                    self.lines.moveTo(side[0].x, side[0].y, side[0].z)
                    self.lines.drawTo(side[1].x, side[1].y, side[1].z)
                    if i == 0:
                        textNodePath.setPos(midpoint[0]+text_offset[0], midpoint[1] - offset, midpoint[2])
                    elif i == 2:
                        textNodePath.setPos(midpoint[0]+text_offset[1], midpoint[1] - offset, midpoint[2])
                    textNodePath.setHpr(90, -90, 0)
                    
                else:
                    self.lines.moveTo(side[0].x, side[0].y, side[0].z)
                    self.lines.drawTo(side[1].x, side[1].y, side[1].z)
                    if i == 1:
                        textNodePath.setPos(midpoint[0] - offset, midpoint[1]-text_offset[0], midpoint[2])
                    elif i == 3:
                        textNodePath.setPos(midpoint[0] - offset, midpoint[1]-text_offset[1], midpoint[2])
                    textNodePath.setHpr(0, -90, 0)
                
                lineNode = self.lines.create()
                lineNodePath = render.attachNewNode(lineNode)
                
                # Add the NodePath to the list
                self.lineNodePaths.append(lineNodePath)

                textNodePath.setScale(2)  # adjust the scale as per your needs
                textNodePath.setColor(1, 1, 1, 1)
                lineNodePath.setLightOff()
                textNodePath.setLightOff()

                self.lineNodePaths.append(textNodePath)


def PointAtZ(z, point, vec):
    if vec.getZ() != 0:
        return point + vec * ((z - point.getZ()) / vec.getZ())

app = MyApp()
app.run()