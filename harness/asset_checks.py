"""Strict self-contained untextured GLB profile; stdlib only, no file/URI loading.

This intentionally rejects otherwise valid glTF features outside the profile.
Validation is not renderer, provenance, authorization or OS-isolation evidence.
"""
import hashlib
import json
import math
import struct

from .model_core import (LIMITS, PROFILE, SceneError, bounds, cross, dot, identity,
                         keys, label, matrix, mm, number, point, sub, transform,
                         unit, vector)


class AssetError(ValueError):
    pass


def check(ok, reason):
    if not ok:
        raise AssetError(reason)


def _index(value, size):
    check(type(value) is int and 0 <= value < size, "invalid reference index")
    return value


def _list(value, low, high):
    check(type(value) is list and low <= len(value) <= high, "collection budget exceeded")
    return value


def _json(raw):
    check(len(raw) <= 2097152, "GLB JSON budget exceeded")
    # Bound nesting before parsing. Brackets inside escaped strings do not count.
    depth=0; quoted=False; escape=False
    for byte in raw:
        if quoted:
            if escape: escape=False
            elif byte==92: escape=True
            elif byte==34: quoted=False
        elif byte==34: quoted=True
        elif byte in (91,123):
            depth+=1;check(depth<=16,"GLB JSON nesting exceeded")
        elif byte in (93,125):
            depth-=1;check(depth>=0,"invalid GLB JSON structure")
    check(depth==0 and not quoted,"invalid GLB JSON structure")
    def pairs(items):
        result={}
        for key,value in items:
            check(key not in result,"duplicate GLB JSON key")
            result[key]=value
        return result
    def constant(_):
        raise AssetError("nonfinite GLB JSON constant")
    try:
        return json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,ValueError,RecursionError) as error:
        if isinstance(error,AssetError): raise
        raise AssetError("invalid GLB JSON") from None


def _validate(blob):
    check(type(blob) is bytes and 28 <= len(blob) <= LIMITS["glb_bytes"],"invalid GLB byte budget")
    magic,version,length=struct.unpack_from("<III",blob)
    check(magic==0x46546c67 and version==2 and length==len(blob),"invalid GLB header")
    json_length,json_kind=struct.unpack_from("<II",blob,12)
    check(json_kind==0x4e4f534a and json_length>0 and json_length%4==0 and 20+json_length+8<=len(blob),"invalid JSON chunk")
    bin_offset=20+json_length
    bin_length,bin_kind=struct.unpack_from("<II",blob,bin_offset)
    check(bin_kind==0x004e4942 and bin_length>0 and bin_length%4==0 and bin_offset+8+bin_length==len(blob),"invalid BIN chunk or trailing chunk")
    d=_json(blob[20:bin_offset]); binary=memoryview(blob)[bin_offset+8:]
    keys(d,("asset","scene","scenes","nodes","meshes","materials","accessors","bufferViews","buffers"))
    keys(d["asset"],("version","generator"))
    check(d["asset"]["version"]=="2.0" and d["asset"]["generator"]=="OAA original SceneSpec compiler 1","unsupported asset profile")
    check(type(d["scene"]) is int and d["scene"]==0,"invalid default scene")
    _list(d["buffers"],1,1);keys(d["buffers"][0],("byteLength",))
    check(type(d["buffers"][0]["byteLength"]) is int and d["buffers"][0]["byteLength"]==len(binary),"buffer length mismatch")
    _list(d["scenes"],1,1);scene=d["scenes"][0];keys(scene,("nodes","extras"))
    keys(scene["extras"],("units","axes","views"))
    check(scene["extras"]["units"]=="m" and scene["extras"]["axes"]=="right-handed-y-up","unsupported units or axes")
    view_ids=set()
    for v in _list(scene["extras"]["views"],1,LIMITS["views"]):
        keys(v,("id","label","position","target","up"));vid=identity(v["id"]);label(v["label"])
        check(vid not in view_ids,"duplicate view identity");view_ids.add(vid)
        direction=unit(sub(vector(v["target"],3),vector(v["position"],3)));up=vector(v["up"],3,-1,1)
        check(abs(dot(up,up)-1)<=1e-6 and dot(cross(direction,up),cross(direction,up))>1e-8,"invalid named view basis")
    materials=_list(d["materials"],1,LIMITS["materials"]);mids=set()
    for m in materials:
        keys(m,("name","pbrMetallicRoughness"));mid=identity(m["name"]);check(mid not in mids,"duplicate material identity");mids.add(mid)
        p=m["pbrMetallicRoughness"];keys(p,("baseColorFactor","metallicFactor","roughnessFactor"))
        color=vector(p["baseColorFactor"],4,0,1);check(color[3]==1,"transparent materials unsupported")
        number(p["metallicFactor"],0,1);number(p["roughnessFactor"],0,1)
    views=_list(d["bufferViews"],1,3*LIMITS["geometries"])
    ranges=[]
    for v in views:
        keys(v,("buffer","byteOffset","byteLength","target"))
        check(type(v["buffer"]) is int and v["buffer"]==0,"external or invalid buffer")
        offset,size=v["byteOffset"],v["byteLength"]
        check(type(offset) is int and type(size) is int and offset>=0 and size>0 and offset%4==0 and size%4==0 and
              offset+size<=len(binary) and type(v["target"]) is int and v["target"] in (34962,34963),"invalid buffer view bounds")
        ranges.append((offset,offset+size))
    cursor=0
    for a,b in sorted(ranges):
        check(a==cursor,"overlapping or unclaimed buffer bytes");cursor=b
    check(cursor==len(binary),"unclaimed buffer bytes")
    accessors=_list(d["accessors"],1,3*LIMITS["geometries"]);decoded=[];used_views=set();float_count=0;index_count=0;layouts=[]
    for a in accessors:
        keys(a,("bufferView","componentType","count","type"),("min","max"))
        vi=_index(a["bufferView"],len(views));check(vi not in used_views,"shared accessor buffer view unsupported");used_views.add(vi);v=views[vi]
        count=a["count"];check(type(count) is int and 0<count<=LIMITS["triangles"]*3,"accessor count exceeded")
        check(type(a["componentType"]) is int,"invalid accessor component")
        if a["type"]=="VEC3" and a["componentType"]==5126:
            check(v["target"]==34962 and v["byteLength"]==12*count,"invalid float accessor span")
            float_count+=count;check(float_count<=LIMITS["triangles"]*6,"decoded float budget exceeded")
            layouts.append((v,"<3f"))
        elif a["type"]=="SCALAR" and a["componentType"]==5125:
            check(v["target"]==34963 and v["byteLength"]==4*count,"invalid index accessor span")
            index_count+=count;check(index_count<=LIMITS["triangles"]*3,"decoded index budget exceeded")
            layouts.append((v,"<I"))
        else: raise AssetError("unsupported accessor type or compression")
    check(len(used_views)==len(views),"unreferenced buffer view")
    meshes=_list(d["meshes"],1,LIMITS["entities"]);used_accessors=set();used_materials=set();mesh_data=[];geometry_bindings={};unique_triangles=0;mesh_pairs=set()
    for m in meshes:
        keys(m,("primitives","extras"));keys(m["extras"],("geometry_id",));gid=identity(m["extras"]["geometry_id"])
        p=_list(m["primitives"],1,1)[0];keys(p,("attributes","indices","mode","material"));keys(p["attributes"],("POSITION","NORMAL"))
        check(type(p["mode"]) is int and p["mode"]==4,"nontriangle primitive unsupported")
        ai=[_index(p["attributes"][key],len(accessors)) for key in ("POSITION","NORMAL")]+[_index(p["indices"],len(accessors))]
        check(len(set(ai))==3,"aliased attributes")
        mat=_index(p["material"],len(materials));used_materials.add(mat);used_accessors.update(ai)
        check((gid,mat) not in mesh_pairs,"duplicate geometry-material mesh");mesh_pairs.add((gid,mat))
        pa,na,ia=[accessors[i] for i in ai]
        check(pa["type"]==na["type"]=="VEC3" and ia["type"]=="SCALAR" and pa["count"]==na["count"]==ia["count"] and ia["count"]%3==0,
              "incompatible primitive accessors")
        check(set(pa)=={"bufferView","componentType","count","type","min","max"} and
              set(na)==set(ia)=={"bufferView","componentType","count","type"},"invalid attribute metadata")
        lo,hi=vector(pa["min"],3),vector(pa["max"],3);check(all(a<=b for a,b in zip(lo,hi)),"invalid position bounds")
        signature=tuple(ai)
        if gid in geometry_bindings: check(geometry_bindings[gid]==signature,"conflicting geometry identity")
        else:
            check(all(not set(signature).intersection(v) for v in geometry_bindings.values()),"geometry accessor aliases another geometry")
            geometry_bindings[gid]=signature;unique_triangles+=ia["count"]//3
            check(len(geometry_bindings)<=LIMITS["geometries"] and unique_triangles<=LIMITS["triangles"],"unique geometry budget exceeded")
        mesh_data.append({"accessors":ai,"triangles":ia["count"]//3,"geometry":gid,"material":materials[mat]["name"],"min":lo,"max":hi})
    check(len(used_accessors)==len(accessors) and len(used_materials)==len(materials),"unreferenced geometry or material data")
    nodes=_list(d["nodes"],1,LIMITS["entities"]);ids=set();parents={};used_meshes=set();expanded=0
    for i,n in enumerate(nodes):
        keys(n,("name","mesh","translation","rotation","scale","extras"),("children",))
        label(n["name"]);keys(n["extras"],("entity_id",));eid=identity(n["extras"]["entity_id"])
        check(eid not in ids,"duplicate entity identity");ids.add(eid)
        mi=_index(n["mesh"],len(meshes));used_meshes.add(mi);expanded+=mesh_data[mi]["triangles"]
        check(expanded<=LIMITS["expanded_triangles"],"instance expansion budget exceeded")
        transform({k:n[k] for k in ("translation","rotation","scale")})
        for child in _list(n.get("children",[]),0,len(nodes)):
            child=_index(child,len(nodes));check(child not in parents and child!=i,"duplicate parent or cyclic node")
            parents[child]=i
    roots=_list(scene["nodes"],1,len(nodes));check(all(type(i) is int for i in roots) and len(set(roots))==len(roots),"invalid scene roots")
    check(set(roots)==set(range(len(nodes)))-parents.keys() and len(used_meshes)==len(meshes),"unreachable nodes or meshes")
    world_matrices={}
    def admit_node(index,parent_matrix,depth):
        check(index not in world_matrices and depth<=LIMITS["hierarchy_depth"],"cyclic or deep node graph")
        n=nodes[index];world=mm(parent_matrix,matrix(n));md=mesh_data[n["mesh"]]
        check(all(math.isfinite(x) and abs(x)<=LIMITS["coordinate"] for row in world for x in row),"expanded transform exceeds bounds")
        corners=[[x,y,z] for x in (md["min"][0],md["max"][0]) for y in (md["min"][1],md["max"][1]) for z in (md["min"][2],md["max"][2])]
        check(all(math.isfinite(x) and abs(x)<=LIMITS["coordinate"] for p in corners for x in point(world,p)),"world bounds exceeded")
        world_matrices[index]=world
        for child in n.get("children",[]):admit_node(child,world,depth+1)
    for root in roots:admit_node(root,[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],1)
    check(len(world_matrices)==len(nodes),"unreachable cyclic node graph")
    # All schema fields, references, spans, hierarchy and aggregate expansion costs
    # have now passed. Only then materialize bounded vertex/index arrays.
    for v,fmt in layouts:
        raw=binary[v["byteOffset"]:v["byteOffset"]+v["byteLength"]]
        data=list(struct.iter_unpack(fmt,raw))
        if fmt=="<I":data=[p[0] for p in data]
        else:check(all(math.isfinite(x) and abs(x)<=LIMITS["coordinate"] for p in data for x in p),"nonfinite or excessive vertex data")
        decoded.append(data)
    for ai in geometry_bindings.values():
        pos,normal,indices=[decoded[i] for i in ai];pa=accessors[ai[0]]
        actual=bounds(pos);check(pa["min"]==actual["min"] and pa["max"]==actual["max"],"position bounds mismatch")
        check(all(i==value for i,value in enumerate(indices)),"profile requires sequential triangle indices")
        check(all(abs(dot(n,n)-1)<=1e-5 for n in normal),"invalid unit normals")
        for i in range(0,len(pos),3):
            n=unit(cross(sub(pos[i+1],pos[i]),sub(pos[i+2],pos[i])))
            check(all(dot(n,normal[j])>1-1e-5 for j in (i,i+1,i+2)),"normal and winding mismatch")
    entity_map=[];all_bounds=[]
    for index,n in enumerate(nodes):
        md=mesh_data[n["mesh"]];pts=[point(world_matrices[index],p) for p in decoded[md["accessors"][0]]]
        b=bounds(pts);all_bounds.extend([b["min"],b["max"]]);entity_map.append({"id":n["extras"]["entity_id"],"node":index,"mesh":n["mesh"],"geometry":md["geometry"],"material":md["material"],"bounds":b})
    return {"profile":PROFILE,"asset_sha256":hashlib.sha256(blob).hexdigest(),"asset_bytes":len(blob),
            "counts":{"triangles":unique_triangles,"vertices":unique_triangles*3,"expanded_triangles":expanded,"entities":len(nodes)},
            "bounds":bounds(all_bounds),"entities":sorted(entity_map,key=lambda e:e["id"]),"views":scene["extras"]["views"],
            "self_contained":True,"textures":False,"rendered":"not_assessed","native":"not_assessed"}


def validate_glb(blob):
    """Return structural summary for exact bytes or raise AssetError. No external reads."""
    try:
        return _validate(blob)
    except SceneError as error:
        raise AssetError(str(error)) from None
