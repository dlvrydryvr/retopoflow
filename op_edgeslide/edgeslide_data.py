'''
Created on Jul 12, 2015

@author: Patrick
'''
import bpy
import bmesh

class EdgeSlide(object):
    
    def __init__(self, context, targ_obj, source_obj = None):
        self.target_name =targ_obj.name
        self.source_name = None
        if source_obj:
            self.source_name = source_obj.name
            
        self.edge_loop_eds = []
        self.vert_loop_vs = []
        self.edge_loop_right = []
        self.edge_loop_left = []
        
        self.vert_snaps_local = []
        self.vert_snaps_world = []
        self.world_right = []
        
        self.pct = 0
        self.cyclic = False
        
    def clear(self):
        self.edge_loop_eds = []
        self.vert_loop_vs = []
        self.edge_loop_right = []
        self.edge_loop_left = []
        self.world_right = []
        
        self.vert_snaps_local = []
        self.vert_snaps_world = []
        self.pct = 0
        self.cyclcic = False
        
    def find_edge_loop(self,bme, ed, select = False):
        '''takes a bmedgse and walks parallel to it'''
        #reality check
        if not ed.is_manifold: return
        bme.edges.ensure_lookup_table()
        bme.verts.ensure_lookup_table()
        def ed_to_vect(ed):
            vect = ed.verts[1].co - ed.verts[0].co
            vect.normalize()
            return vect
            
        def next_edge(cur_ed, cur_vert):
            ledges = [ed for ed in cur_vert.link_edges if ed != cur_ed]
            
            fset = set([f.index for f in cur_ed.link_faces])
            
            next_edge = [ed for ed in ledges if not fset & set([f.index for f in ed.link_faces])][0]
            
            forward = cur_vert.co - cur_ed.other_vert(cur_vert).co
            forward.normalize()
            
            sides = set(ledges)
            sides.remove(next_edge)
            esides = list(sides)
            side0 = esides[0].other_vert(cur_vert).co - cur_vert.co
            side1 = esides[1].other_vert(cur_vert).co - cur_vert.co
            
            
            if cur_vert.normal.dot(side0.cross(forward)) > 0:
                v_right, v_left = side0, side1
            else:
                v_left, v_right = side0, side1

            return next_edge, v_right, v_left
        
        def next_vert(cur_ed, cur_vert):
            next_vert = cur_ed.other_vert(cur_vert)
            return next_vert
        
        loop_eds = []
        loop_verts = []
        loop_rights = []
        loop_lefts = []
        
        self.cyclic = False
        
        for v in ed.verts:
            
            if len(v.link_edges) != 4: continue            
            eds = [ed.index]
            vs = [v.index]
            
            rights = []   
            lefts = []
            
            
            ed_cur = ed
            v_cur = v
            v_next = True
            while v_next != v:
                
                if select:
                    v_cur.select_set(True) 
                    ed_cur.select_set(True)
                
                ed_next, right, left = next_edge(ed_cur, v_cur)
                eds += [ed_next.index]
                rights += [right]
                lefts += [left]
                
                v_next = next_vert(ed_next, v_cur)
                
                if len(v_next.link_edges) != 4:
                    
                    if all(ed.is_manifold for ed in v_next.link_edges):  break #this is a pole for sure
                    
                    elif len([ed for ed in v_next.link_edges if ed.is_manifold]) == 1 and len(v_next.link_edges) == 3:
                         forward = v_next.co - ed_next.other_vert(v_next).co
                         esides = [ed for ed in v_next.link_edges if ed != ed_next]
                         side0 = esides[0].other_vert(v_next).co - v_next.co
                         side1 = esides[1].other_vert(v_next).co - v_next.co
                         
                         if v_next.normal.dot(side0.cross(forward)) > 0:
                             v_right, v_left = side0, side1
                         else:
                             v_left, v_right = side0, side1
                            
                         vs += [v_next.index]
                         rights += [v_right]
                         lefts += [v_left]
                         break
                         
                vs += [v_next.index]
                ed_cur = ed_next
                v_cur = v_next
                
            
            if v_next == v: #we looped
                self.cyclic = True
                self.vert_loop_vs = vs[:len(vs)-1]
                self.edge_loop_eds = eds[:len(eds)-1] #<--- discard the edge we walked across to get back to start vert
                self.edge_loop_right = rights
                self.edge_loop_left = lefts

                return
            else:
                if len(vs):
                    loop_verts.append(vs)
                    loop_eds.append(eds)
                    loop_rights.append(rights)
                    loop_lefts.append(lefts)
        
        if len(loop_verts) == 2:    
            loop_verts[0].reverse()    
            self.vert_loop_vs = loop_verts[0] +  loop_verts[1]
            tip = loop_eds[0][1:]
            tip.reverse()
            self.edge_loop_eds = tip + loop_eds[1]
            
            loop_rights[0].reverse()
            loop_lefts[0].reverse()
            
            self.edge_loop_right = loop_lefts[0] + loop_rights[1]
            self.edge_loop_left = loop_rights[0] + loop_lefts[1]
            
        else:
            self.vert_loop_vs = loop_verts[0]
            self.edge_loop_eds = loop_eds[0]
            self.edge_loop_right = loop_rights[0]
            self.edge_loop_left = loop_lefts[0]
            
        return
    
    def calc_snaps(self,bme):
        if not len(self.edge_loop_eds): return
        self.vert_snaps_local = []
        self.vert_snaps_world = []
        self.world_right = []
        
        if self.source_name:
            ob = bpy.data.objects[self.source_name]
            mx_src = ob.matrix_world
            imx_src = mx_src.inverted()
            
        mx_trg = bpy.data.objects[self.target_name].matrix_world
        imx_trg = mx_trg.inverted()

        for i, n in enumerate(self.vert_loop_vs):
            vert = bme.verts[n]
            
            if self.right:
                v = vert.co + self.pct * self.edge_loop_right[i]    
            else:
                v = vert.co + self.pct * self.edge_loop_left[i]
                
            if not self.source_name:
                self.vert_snaps_local += [v]
                self.vert_snaps_world += [mx_trg * v]
            else:
                loc, no, indx = ob.closest_point_on_mesh(imx_src * mx_trg * v)
                self.vert_snaps_local += [imx_trg * mx_src * loc]
                self.vert_snaps_world += [mx_src * loc]
                self.world_right += [mx_trg * (v + self.edge_loop_right[i])]
                
       
    def move_loop(self, bme):

        vs = [bme.verts[i] for i in self.vert_loop_vs]
        
        for i, v in enumerate(vs):
            v.co = self.vert_snaps_local[i]
            
        return
    
    def push_to_edit_mesh(self,bme):
        target_ob = bpy.data.objects[self.target_name]
        bmesh.update_edit_mesh(target_ob.data)
    