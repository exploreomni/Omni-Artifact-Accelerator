"""Original bounded SceneSpec compiler. Standard library only; no I/O or launcher.

These functions are not an isolation boundary. Untrusted jobs belong in a
separately authorized worker; this module never loads dependencies or assets.
"""
import hashlib
import json
import math
import re
import struct

PROFILE = "oaa-glb-untextured-v1"
LIMITS = {"input_bytes": 1048576, "json_values": 100000, "depth": 12,
          "entities": 1024, "geometries": 128, "materials": 64, "views": 32,
          "points": 128, "segments": 64, "triangles": 100000,
          "expanded_triangles": 200000, "glb_bytes": 16777216,
          "coordinate": 1000000, "hierarchy_depth": 32}
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class SceneError(ValueError):
    """Bounded diagnostic; does not include supplied labels or field values."""


def require(ok, reason):
    if not ok:
        raise SceneError(reason)


def keys(value, required, optional=()):
    require(type(value) is dict and set(required) <= value.keys() and
            value.keys() <= set(required) | set(optional), "unknown or missing fields")


def number(value, low=-1000000, high=1000000):
    require(type(value) in (int, float) and low <= value <= high and math.isfinite(value),
            "number outside finite bounds")
    return float(value)


def integer(value, low, high):
    require(type(value) is int and low <= value <= high, "integer outside bounds")
    return value


def vector(value, size, low=-1000000, high=1000000):
    require(type(value) is list and len(value) == size, "invalid vector")
    return [number(x, low, high) for x in value]


def identity(value):
    require(type(value) is str and _ID.fullmatch(value) is not None, "invalid stable identity")
    return value


def label(value):
    require(type(value) is str and 0 < len(value) <= 120 and value.strip() and
            not any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value), "invalid label")
    return value


def bounded_json(value):
    count = 0
    active = set()
    def visit(item, depth):
        nonlocal count
        count += 1
        require(count <= LIMITS["json_values"] and depth <= LIMITS["depth"], "JSON budget exceeded")
        if type(item) in (dict, list):
            require(id(item) not in active and len(item) <= LIMITS["json_values"], "cyclic or oversized JSON")
            active.add(id(item))
            if type(item) is dict:
                require(len(item) <= 64 and all(type(k) is str and len(k) <= 64 for k in item), "invalid object keys")
                for child in item.values():
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
            active.remove(id(item))
        elif type(item) is str:
            require(len(item) <= 256, "oversized string")
        elif type(item) in (int, float):
            number(item)
        else:
            require(item is None or type(item) is bool, "non-JSON value")
    visit(value, 0)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    require(len(raw) <= LIMITS["input_bytes"], "input byte budget exceeded")
    return raw


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def add(a, b):
    return [x+y for x, y in zip(a, b)]


def mul(a, s):
    return [x*s for x in a]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(a):
    length = math.sqrt(dot(a, a))
    require(length > 1e-10, "degenerate direction or triangle")
    return mul(a, 1/length)


def transform(value):
    keys(value, (), ("translation", "rotation", "scale"))
    t = vector(value.get("translation", [0, 0, 0]), 3, -10000, 10000)
    r = vector(value.get("rotation", [0, 0, 0, 1]), 4, -1, 1)
    s = vector(value.get("scale", [1, 1, 1]), 3, .0001, 10000)
    require(abs(dot(r, r)-1) <= 1e-6, "rotation must be a unit quaternion")
    return {"translation": t, "rotation": r, "scale": s}


def matrix(trs):
    x, y, z, w = trs["rotation"]
    sx, sy, sz = trs["scale"]
    tx, ty, tz = trs["translation"]
    return [[(1-2*y*y-2*z*z)*sx, (2*x*y-2*z*w)*sy, (2*x*z+2*y*w)*sz, tx],
            [(2*x*y+2*z*w)*sx, (1-2*x*x-2*z*z)*sy, (2*y*z-2*x*w)*sz, ty],
            [(2*x*z-2*y*w)*sx, (2*y*z+2*x*w)*sy, (1-2*x*x-2*y*y)*sz, tz],
            [0, 0, 0, 1]]


def mm(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def point(m, p):
    return [sum(m[i][j]*p[j] for j in range(3))+m[i][3] for i in range(3)]


def bounds(points):
    return {"min": [min(p[i] for p in points) for i in range(3)],
            "max": [max(p[i] for p in points) for i in range(3)]}


def orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def outline(points):
    require(type(points) is list and 3 <= len(points) <= LIMITS["points"], "invalid outline size")
    p = [vector(v, 2, -10000, 10000) for v in points]
    n = len(p)
    require(len({tuple(v) for v in p}) == n, "duplicate outline point")
    for i in range(n):
        require(abs(orient(p[i-1], p[i], p[(i+1) % n])) > 1e-8, "collinear outline edge")
        for j in range(i+1, n):
            if j in ((i+1) % n, (i-1) % n):
                continue
            a, b, c, d = p[i], p[(i+1) % n], p[j], p[(j+1) % n]
            if max(min(a[0], b[0]), min(c[0], d[0])) > min(max(a[0], b[0]), max(c[0], d[0])) or \
               max(min(a[1], b[1]), min(c[1], d[1])) > min(max(a[1], b[1]), max(c[1], d[1])):
                continue
            require(not (orient(a, b, c)*orient(a, b, d) <= 0 and orient(c, d, a)*orient(c, d, b) <= 0),
                    "self-intersecting outline")
    area = sum(p[i][0]*p[(i+1) % n][1]-p[(i+1) % n][0]*p[i][1] for i in range(n))
    require(abs(area) > 1e-8, "zero outline area")
    return p if area > 0 else list(reversed(p))


def geometry(g):
    keys(g, ("id", "type"), ("size", "radius", "height", "segments", "outline", "path", "profile"))
    identity(g["id"])
    kind = g["type"]
    fields = {"box": ("size",), "cylinder": ("radius", "height", "segments"),
              "extrusion": ("outline", "height"), "tube": ("path", "radius", "segments"),
              "revolution": ("profile", "segments")}
    require(type(kind) is str and kind in fields, "unsupported geometry operation")
    keys(g, ("id", "type", *fields[kind]))
    result = {"id": g["id"], "type": kind}
    if kind == "box":
        result["size"] = vector(g["size"], 3, .0001, 10000)
        cost = 12
    if "segments" in fields[kind]:
        result["segments"] = integer(g["segments"], 3, LIMITS["segments"])
    if "height" in fields[kind]:
        result["height"] = number(g["height"], .0001, 10000)
    if "radius" in fields[kind]:
        result["radius"] = number(g["radius"], .0001, 10000)
    if kind == "cylinder":
        cost = 4*result["segments"]
    elif kind == "extrusion":
        result["outline"] = outline(g["outline"])
        cost = 4*len(result["outline"])-4
    elif kind == "tube":
        require(type(g["path"]) is list and 2 <= len(g["path"]) <= LIMITS["points"], "invalid tube path size")
        result["path"] = [vector(p, 3, -10000, 10000) for p in g["path"]]
        directions = []
        for a, b in zip(result["path"], result["path"][1:]):
            d = sub(b, a)
            require(dot(d, d) >= (2*result["radius"])**2, "tube segment too short for radius")
            directions.append(unit(d))
        require(all(dot(a, b) > -.95 for a, b in zip(directions, directions[1:])), "tube reversal unsupported")
        cost = 2*len(result["path"])*result["segments"]
    elif kind == "revolution":
        require(type(g["profile"]) is list and 2 <= len(g["profile"]) <= LIMITS["points"], "invalid revolution profile size")
        result["profile"] = [vector(p, 2, -10000, 10000) for p in g["profile"]]
        require(all(p[0] >= .0001 for p in result["profile"]), "profile radius must be positive")
        require(all(b[1]-a[1] >= .0001 for a, b in zip(result["profile"], result["profile"][1:])), "profile height must increase")
        cost = 2*len(result["profile"])*result["segments"]
    return result, cost


def validate_scene(spec):
    """Return normalized SceneSpec and preflight cost as a dict; never allocate mesh arrays."""
    bounded_json(spec)
    keys(spec, ("schema_version", "units", "axes", "materials", "geometries", "entities", "views"), ("instance_sets",))
    require(type(spec["schema_version"]) is int and spec["schema_version"] == 1 and spec["units"] == "m" and
            spec["axes"] == "right-handed-y-up", "unsupported scene version, units or axes")
    for field, low, high in [("materials", 1, LIMITS["materials"]), ("geometries", 1, LIMITS["geometries"]),
                             ("entities", 0, LIMITS["entities"]), ("views", 1, LIMITS["views"])]:
        require(type(spec[field]) is list and low <= len(spec[field]) <= high, "collection budget exceeded")
    materials, geometries, costs, entities, views = {}, {}, {}, {}, {}
    for item in spec["materials"]:
        keys(item, ("id", "base_color", "metallic", "roughness"))
        mid = identity(item["id"])
        require(mid not in materials, "duplicate material identity")
        color = vector(item["base_color"], 4, 0, 1)
        require(color[3] == 1, "only opaque materials supported")
        materials[mid] = {"id": mid, "base_color": color, "metallic": number(item["metallic"], 0, 1), "roughness": number(item["roughness"], 0, 1)}
    for item in spec["geometries"]:
        g, cost = geometry(item)
        require(g["id"] not in geometries, "duplicate geometry identity")
        geometries[g["id"]], costs[g["id"]] = g, cost
    def entity(item):
        keys(item, ("id", "label", "geometry", "material"), ("parent", "transform"))
        eid = identity(item["id"])
        require(eid not in entities and len(entities) < LIMITS["entities"], "duplicate identity or entity budget exceeded")
        require(type(item["geometry"]) is str and item["geometry"] in geometries and type(item["material"]) is str and item["material"] in materials,
                "unknown geometry or material reference")
        e = {"id": eid, "label": label(item["label"]), "geometry": item["geometry"], "material": item["material"], "transform": transform(item.get("transform", {}))}
        if "parent" in item:
            e["parent"] = identity(item["parent"])
        entities[eid] = e
    for item in spec["entities"]:
        entity(item)
    sets = spec.get("instance_sets", [])
    require(type(sets) is list and len(sets) <= LIMITS["geometries"], "instance set budget exceeded")
    for group in sets:
        keys(group, ("geometry", "material", "instances"), ("parent",))
        require(type(group["instances"]) is list and 1 <= len(group["instances"]) <= LIMITS["entities"]-len(entities), "instance expansion budget exceeded")
        for item in group["instances"]:
            keys(item, ("id", "label"), ("transform",))
            entity({**{k: v for k, v in group.items() if k != "instances"}, **item})
    require(entities, "scene requires an entity")
    # No implicit order-based IDs: canonical order is stable under source reordering.
    entities = dict(sorted(entities.items()))
    world, depths = {}, {}
    def world_matrix(eid, active):
        require(eid not in active and len(active) < LIMITS["hierarchy_depth"], "cyclic or deep hierarchy")
        if eid in world:
            return world[eid]
        e = entities[eid]
        result = matrix(e["transform"]); depth = 1
        if "parent" in e:
            require(e["parent"] in entities, "unknown parent identity")
            result = mm(world_matrix(e["parent"], active+[eid]), result)
            depth = depths[e["parent"]]+1
        require(depth <= LIMITS["hierarchy_depth"], "hierarchy depth exceeded")
        depths[eid] = depth
        require(all(math.isfinite(v) and abs(v) <= 1000000 for row in result for v in row), "expanded transform exceeds bounds")
        world[eid] = result
        return result
    for eid in entities:
        world_matrix(eid, [])
    require({e["geometry"] for e in entities.values()} == set(geometries) and
            {e["material"] for e in entities.values()} == set(materials), "unreferenced geometry or material")
    # Conservative transformed local boxes are checked before triangle allocation.
    # Tube boxes expand its supplied centerline by radius on every axis.
    for e in entities.values():
        g = geometries[e["geometry"]]
        if g["type"] == "box":
            lo = [-v/2 for v in g["size"]]; hi = [v/2 for v in g["size"]]
        elif g["type"] == "cylinder":
            r, h = g["radius"], g["height"]/2; lo, hi = [-r,-h,-r], [r,h,r]
        elif g["type"] == "extrusion":
            lo = [min(p[0] for p in g["outline"]),0,min(p[1] for p in g["outline"])]
            hi = [max(p[0] for p in g["outline"]),g["height"],max(p[1] for p in g["outline"])]
        elif g["type"] == "revolution":
            r=max(p[0] for p in g["profile"]);lo,hi=[-r,g["profile"][0][1],-r],[r,g["profile"][-1][1],r]
        else:
            b=bounds(g["path"]);lo=[v-g["radius"] for v in b["min"]];hi=[v+g["radius"] for v in b["max"]]
        corners = [[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
        require(all(abs(v)<=LIMITS["coordinate"] and math.isfinite(v) for p in corners for v in point(world[e["id"]],p)),
                "transformed geometry budget exceeded")
    for item in spec["views"]:
        keys(item, ("id", "label", "position", "target", "up"))
        vid = identity(item["id"])
        require(vid not in views, "duplicate view identity")
        v = {"id": vid, "label": label(item["label"]), "position": vector(item["position"], 3),
             "target": vector(item["target"], 3), "up": vector(item["up"], 3, -1, 1)}
        direction = unit(sub(v["target"], v["position"]))
        require(abs(dot(v["up"], v["up"])-1) <= 1e-6 and dot(cross(direction, v["up"]), cross(direction, v["up"])) > 1e-8,
                "invalid named view basis")
        views[vid] = v
    triangles = sum(costs.values())
    expanded = sum(costs[e["geometry"]] for e in entities.values())
    require(triangles <= LIMITS["triangles"] and expanded <= LIMITS["expanded_triangles"], "mesh expansion budget exceeded")
    # Flat triangle positions + normals + uint32 indices are 84 bytes/triangle.
    require(triangles*84+len(entities)*2048+len(geometries)*2048 < LIMITS["glb_bytes"], "output allocation budget exceeded")
    normalized = {"schema_version": 1, "units": "m", "axes": "right-handed-y-up",
                  "materials": [materials[k] for k in sorted(materials)], "geometries": [geometries[k] for k in sorted(geometries)],
                  "entities": list(entities.values()), "views": [views[k] for k in sorted(views)]}
    return {"scene": normalized, "cost": {"triangles": triangles, "vertices": triangles*3, "expanded_triangles": expanded,
                                           "entities": len(entities)}, "world_matrices": world}


def _ears(p):
    indices, result = list(range(len(p))), []
    while len(indices) > 3:
        for k, b in enumerate(indices):
            a, c = indices[k-1], indices[(k+1) % len(indices)]
            if orient(p[a], p[b], p[c]) <= 1e-10:
                continue
            if any(orient(p[a], p[b], p[j]) >= -1e-10 and orient(p[b], p[c], p[j]) >= -1e-10 and
                   orient(p[c], p[a], p[j]) >= -1e-10 for j in indices if j not in (a, b, c)):
                continue
            result.append((a, b, c)); del indices[k]; break
        else:
            raise SceneError("outline triangulation failed")
    return result+[tuple(indices)]


def _triangles(g):
    """Original triangle construction; outward winding, flat face normals."""
    kind = g["type"]
    faces = []
    def quad(a, b, c, d):
        faces.extend(((a, b, c), (a, c, d)))
    if kind == "box":
        x, y, z = [v/2 for v in g["size"]]
        p = [[a*x, b*y, c*z] for a, b, c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        for a,b,c,d in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(0,1,5,4),(3,7,6,2)]:
            quad(p[a],p[b],p[c],p[d])
    elif kind == "extrusion":
        p, h = g["outline"], g["height"]
        low, high = [[x, 0, z] for x,z in p], [[x, h, z] for x,z in p]
        for a,b,c in _ears(p):
            faces.extend(((low[a],low[b],low[c]),(high[c],high[b],high[a])))
        for i in range(len(p)):
            j = (i+1) % len(p)
            quad(low[i],high[i],high[j],low[j])
    elif kind in ("cylinder", "revolution"):
        profile = [[g["radius"],-g["height"]/2],[g["radius"],g["height"]/2]] if kind == "cylinder" else g["profile"]
        n = g["segments"]
        rings = [[[r*math.cos(2*math.pi*j/n), y, r*math.sin(2*math.pi*j/n)] for j in range(n)] for r,y in profile]
        for a,b in zip(rings,rings[1:]):
            for i in range(n):
                j=(i+1) % n; quad(a[i],b[i],b[j],a[j])
        for i in range(n):
            j=(i+1) % n
            faces.extend((([0,profile[0][1],0],rings[0][i],rings[0][j]),([0,profile[-1][1],0],rings[-1][j],rings[-1][i])))
    elif kind == "tube":
        p,n,r=g["path"],g["segments"],g["radius"]
        directions=[unit(sub(b,a)) for a,b in zip(p,p[1:])]
        tangents=[directions[0]]+[unit(add(a,b)) for a,b in zip(directions,directions[1:])]+[directions[-1]]
        rings=[]; previous=None
        for center,t in zip(p,tangents):
            normal=sub(previous,mul(t,dot(previous,t))) if previous else [0,0,0]
            if dot(normal,normal)<1e-8:
                axis=min([[1,0,0],[0,1,0],[0,0,1]],key=lambda a:abs(dot(a,t)))
                normal=cross(t,axis)
            normal=unit(normal); side=cross(t,normal); previous=normal
            rings.append([add(center,mul(add(mul(normal,math.cos(2*math.pi*j/n)),mul(side,math.sin(2*math.pi*j/n))),r)) for j in range(n)])
        for a,b in zip(rings,rings[1:]):
            for i in range(n):
                j=(i+1) % n; quad(a[i],a[j],b[j],b[i])
        for i in range(n):
            j=(i+1) % n
            faces.extend(((p[0],rings[0][j],rings[0][i]),(p[-1],rings[-1][i],rings[-1][j])))
    return faces


def compile_scene(spec):
    """Return {glb: bytes, scene: normalized editable dict, manifest: dict}. No writes."""
    checked=validate_scene(spec); s=checked["scene"]
    doc={"asset":{"version":"2.0","generator":"OAA original SceneSpec compiler 1"},"scene":0,
         "scenes":[{"nodes":[],"extras":{"units":"m","axes":"right-handed-y-up","views":s["views"]}}],
         "nodes":[],"meshes":[],"materials":[],"accessors":[],"bufferViews":[],"buffers":[]}
    binary=bytearray(); geom={}; local_points={}
    def accessor(raw,component,count,kind,target,minimum=None,maximum=None):
        index=len(doc["bufferViews"]); offset=len(binary); binary.extend(raw)
        doc["bufferViews"].append({"buffer":0,"byteOffset":offset,"byteLength":len(raw),"target":target})
        a={"bufferView":index,"componentType":component,"count":count,"type":kind}
        if minimum is not None: a.update({"min":minimum,"max":maximum})
        doc["accessors"].append(a);return len(doc["accessors"])-1
    for g in s["geometries"]:
        faces=_triangles(g); positions=[]; normals=[]
        for a,b,c in faces:
            # Quantize before normals: reject geometry collapsed by float32 output.
            vertices=[list(struct.unpack("<3f",struct.pack("<3f",*p))) for p in (a,b,c)]
            normal=unit(cross(sub(vertices[1],vertices[0]),sub(vertices[2],vertices[0])))
            for p in vertices:
                positions.append(p); normals.append(normal)
        b=bounds(positions); local_points[g["id"]]=positions
        pos=accessor(b"".join(struct.pack("<3f",*p) for p in positions),5126,len(positions),"VEC3",34962,b["min"],b["max"])
        norm=accessor(b"".join(struct.pack("<3f",*p) for p in normals),5126,len(normals),"VEC3",34962)
        idx=accessor(b"".join(struct.pack("<I",i) for i in range(len(positions))),5125,len(positions),"SCALAR",34963)
        geom[g["id"]]={"attributes":{"POSITION":pos,"NORMAL":norm},"indices":idx,"mode":4}
    mids={m["id"]:i for i,m in enumerate(s["materials"])}
    for m in s["materials"]:
        doc["materials"].append({"name":m["id"],"pbrMetallicRoughness":{"baseColorFactor":m["base_color"],"metallicFactor":m["metallic"],"roughnessFactor":m["roughness"]}})
    mesh_ids={}; entity_map=[]; all_bounds=[]
    nids={e["id"]:i for i,e in enumerate(s["entities"])}
    for e in s["entities"]:
        pair=(e["geometry"],e["material"])
        if pair not in mesh_ids:
            mesh_ids[pair]=len(doc["meshes"])
            doc["meshes"].append({"primitives":[{**geom[e["geometry"]],"material":mids[e["material"]]}],"extras":{"geometry_id":e["geometry"]}})
        ni=nids[e["id"]]; mi=mesh_ids[pair]
        doc["nodes"].append({"name":e["label"],"mesh":mi,**e["transform"],"extras":{"entity_id":e["id"]}})
        world_points=[point(checked["world_matrices"][e["id"]],p) for p in local_points[e["geometry"]]]
        require(all(math.isfinite(v) and abs(v)<=LIMITS["coordinate"] for p in world_points for v in p),"world geometry exceeds bounds")
        b=bounds(world_points);all_bounds.extend([b["min"],b["max"]])
        entity_map.append({"id":e["id"],"node":ni,"mesh":mi,"geometry":e["geometry"],"material":e["material"],"bounds":b})
    for e in s["entities"]:
        if "parent" in e: doc["nodes"][nids[e["parent"]]].setdefault("children",[]).append(nids[e["id"]])
        else: doc["scenes"][0]["nodes"].append(nids[e["id"]])
    doc["buffers"]=[{"byteLength":len(binary)}]
    raw=json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode();raw+=b" "*((-len(raw))%4)
    blob=struct.pack("<III",0x46546c67,2,28+len(raw)+len(binary))+struct.pack("<II",len(raw),0x4e4f534a)+raw+struct.pack("<II",len(binary),0x004e4942)+binary
    require(len(blob)<=LIMITS["glb_bytes"],"GLB output budget exceeded")
    source=json.dumps(s,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
    manifest={"schema_version":1,"profile":PROFILE,"asset_sha256":hashlib.sha256(blob).hexdigest(),"asset_bytes":len(blob),
              "scene_sha256":hashlib.sha256(source).hexdigest(),"input_sha256":hashlib.sha256(bounded_json(spec)).hexdigest(),"units":"m","axes":"right-handed-y-up","counts":checked["cost"],
              "bounds":bounds(all_bounds),"entities":entity_map,"views":s["views"],
              "provenance":{"generator":"original-repository-source","textures":False,"imported_assets":False},
              "qualification":{"rendered":"not_assessed","native":"not_assessed","isolation":"not_established_by_compiler"}}
    return {"glb":bytes(blob),"scene":s,"manifest":manifest}
