"""Original geometry and hostile-structure checks. Python standard library only."""
import copy
import json
import math
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

# Explicit repository-owned imports; safe with python -I -S (no site packages).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness import model_core as core
from harness.asset_checks import AssetError, validate_glb


def simple(geometry=None):
    return {"schema_version":1,"units":"m","axes":"right-handed-y-up",
            "materials":[{"id":"neutral","base_color":[.3,.4,.5,1],"metallic":0,"roughness":.7}],
            "geometries":[geometry or {"id":"shape","type":"box","size":[2,4,6]}],
            "entities":[{"id":"object","label":"Original object","geometry":"shape","material":"neutral"}],
            "views":[{"id":"front","label":"Front","position":[0,4,10],"target":[0,0,0],"up":[0,1,0]}]}


def unpack(blob):
    length=struct.unpack_from('<I',blob,12)[0]
    return json.loads(blob[20:20+length]),bytes(blob[28+length:])


def repack(document,binary):
    raw=json.dumps(document,separators=(',',':'),allow_nan=False).encode();raw+=b' '*((-len(raw))%4)
    return struct.pack('<III',0x46546c67,2,28+len(raw)+len(binary))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary


def volume(blob):
    d,b=unpack(blob);p=d['meshes'][0]['primitives'][0];a=d['accessors'][p['attributes']['POSITION']];v=d['bufferViews'][a['bufferView']]
    points=list(struct.iter_unpack('<3f',b[v['byteOffset']:v['byteOffset']+v['byteLength']]))
    return sum(core.dot(points[i],core.cross(points[i+1],points[i+2]))/6 for i in range(0,len(points),3))


class SpatialCoreTests(unittest.TestCase):
    def test_real_glb_deterministic_roundtrip_dimensions_and_hierarchy(self):
        s=simple();s['entities'][0]['transform']={'translation':[10,0,0],'rotation':[0,0,math.sqrt(.5),math.sqrt(.5)],'scale':[3,1,1]}
        result=core.compile_scene(s);self.assertEqual(result['glb'][:4],b'glTF')
        self.assertEqual(result['glb'],core.compile_scene(s)['glb'])
        inspected=validate_glb(result['glb'])
        self.assertEqual(inspected['entities'],result['manifest']['entities'])
        self.assertEqual(inspected['counts'],result['manifest']['counts'])
        self.assertEqual(inspected['asset_sha256'],result['manifest']['asset_sha256'])
        for got,want in zip(inspected['bounds']['min'],[8,-3,-3]):self.assertAlmostEqual(got,want)
        for got,want in zip(inspected['bounds']['max'],[12,3,3]):self.assertAlmostEqual(got,want)
        self.assertEqual(inspected['counts']['triangles'],12)
        self.assertAlmostEqual(volume(core.compile_scene(simple())['glb']),48)

    def test_original_operations_have_independent_counts_and_volumes(self):
        geometries=[({'id':'shape','type':'cylinder','radius':1,'height':3,'segments':12},48,18*math.sin(math.pi/6)),
                    ({'id':'shape','type':'extrusion','outline':[[0,0],[3,0],[3,1],[1,1],[1,3],[0,3]],'height':2},20,10),
                    ({'id':'shape','type':'tube','path':[[0,0,0],[0,3,0]],'radius':1,'segments':12},48,18*math.sin(math.pi/6)),
                    ({'id':'shape','type':'revolution','profile':[[1,0],[2,3]],'segments':12},48,42*math.sin(math.pi/6))]
        for geometry,count,expected in geometries:
            with self.subTest(kind=geometry['type']):
                r=core.compile_scene(simple(geometry));a=validate_glb(r['glb'])
                self.assertEqual(a['counts']['triangles'],count)
                self.assertAlmostEqual(volume(r['glb']),expected,places=5)

    def test_three_original_fixtures_and_stable_instance_mapping(self):
        for path in sorted((ROOT/'harness/fixtures').glob('*.json')):
            with self.subTest(fixture=path.name):
                s=json.loads(path.read_text());r=core.compile_scene(s);a=validate_glb(r['glb'])
                self.assertEqual(a['entities'],r['manifest']['entities']);self.assertEqual(a['views'],r['scene']['views'])
                self.assertEqual(r['glb'],core.compile_scene(r['scene'])['glb'])
                s['entities'].reverse();s['materials'].reverse();s['geometries'].reverse();s['views'].reverse()
                if 'instance_sets' in s:s['instance_sets'][0]['instances'].reverse()
                self.assertEqual(r['glb'],core.compile_scene(s)['glb'])
                before=[e['id'] for e in r['manifest']['entities']]
                s['entities'][0].setdefault('transform',{})['translation']=[1,1,1]
                revised=core.compile_scene(s)
                self.assertEqual(before,[e['id'] for e in revised['manifest']['entities']])
                self.assertNotEqual(r['manifest']['asset_sha256'],revised['manifest']['asset_sha256'])

    def test_invalid_and_expanding_scenes_reject_before_mesh_allocation(self):
        cases=[]
        s=simple();s['entities'].append(copy.deepcopy(s['entities'][0]));cases.append(s)
        s=simple();s['geometries'][0]['size'][0]=float('nan');cases.append(s)
        s=simple();s['geometries'][0]['size'][0]=10**1000;cases.append(s)
        s=simple();s['script']='print(1)';cases.append(s)
        s=simple();s['geometries'][0]['uri']='file:///private/canary';cases.append(s)
        s=simple();s['entities'][0]['transform']={'scale':[10000,10000,10000],'translation':[10000,10000,10000]};s['geometries'][0]['size']=[10000]*3;cases.append(s)
        s=simple({'id':'shape','type':'cylinder','radius':1,'height':1,'segments':64});s['entities']=[];s['instance_sets']=[{'geometry':'shape','material':'neutral','instances':[{'id':f'e{i}','label':'Instance'} for i in range(1024)]}];cases.append(s)
        s=simple();s['entities']=[{'id':f'e{i:02}','label':'Nested','geometry':'shape','material':'neutral',**({'parent':f'e{i-1:02}'} if i else {})} for i in range(33)];cases.append(s)
        s=simple();s['entities'][0]['parent']='object';cases.append(s)
        s=simple();s['views'][0]['up']=[0,0,0];cases.append(s)
        s=simple({'id':'shape','type':'extrusion','outline':[[0,0],[2,2],[0,2],[2,0]],'height':1});cases.append(s)
        s=simple({'id':'shape','type':'tube','path':[[0,0,0],[0,3,0],[0,0,0]],'radius':.1,'segments':12});cases.append(s)
        s=simple();s['materials'][0]['base_color'][3]=.5;cases.append(s)
        for s in cases:
            with self.subTest(spec=s),patch.object(core,'_triangles',side_effect=AssertionError('geometry was allocated')) as geometry:
                with self.assertRaises(core.SceneError):core.compile_scene(s)
                geometry.assert_not_called()

    def test_hostile_glb_uris_extensions_ranges_identity_and_numbers_rejected(self):
        blob=core.compile_scene(simple())['glb'];original,binary=unpack(blob)
        def uri(d):d['buffers'][0]['uri']='https://invalid.example/asset.bin'
        def image(d):d['images']=[{'uri':'file:///private/canary'}]
        def extension(d):d['extensionsUsed']=['KHR_draco_mesh_compression']
        def span(d):d['bufferViews'][0]['byteLength']+=4
        def count(d):d['accessors'][0]['count']=100000000
        def metadata(d):d['accessors'][0]['max'][0]+=1
        def duplicate(d):d['nodes'].append(copy.deepcopy(d['nodes'][0]));d['scenes'][0]['nodes'].append(1)
        def cycle(d):d['nodes'][0]['children']=[0]
        def sparse(d):d['accessors'][0]['sparse']={'count':1}
        for mutation in [uri,image,extension,span,count,metadata,duplicate,cycle,sparse]:
            d=copy.deepcopy(original);mutation(d)
            with self.subTest(mutation=mutation.__name__),self.assertRaises(AssetError):validate_glb(repack(d,binary))
        bad=bytearray(binary);struct.pack_into('<f',bad,0,float('nan'))
        with self.assertRaises(AssetError):validate_glb(repack(original,bad))
        bad=bytearray(binary);view=original['bufferViews'][2];struct.pack_into('<I',bad,view['byteOffset'],999999)
        with self.assertRaises(AssetError):validate_glb(repack(original,bad))
        for bad in [blob[:-1],blob+b'junk',b'{"glb":true}',struct.pack('<III',0x46546c67,3,len(blob))+blob[12:]]:
            with self.assertRaises(AssetError):validate_glb(bad)

    def test_invalid_structure_rejects_before_vertex_decode(self):
        blob=core.compile_scene(simple())['glb'];document,binary=unpack(blob)
        document['nodes'][0]['extras']['uri']='https://invalid.example/model'
        bad=repack(document,binary)
        with patch('harness.asset_checks.struct.iter_unpack',side_effect=AssertionError('decoded before admission')) as decode:
            with self.assertRaises(AssetError):validate_glb(bad)
            decode.assert_not_called()

    def test_duplicate_json_keys_nested_bombs_and_unknown_chunks_rejected(self):
        blob=core.compile_scene(simple())['glb'];d,b=unpack(blob)
        raw=b'{"scene":0,"scene":0}';raw+=b' '*((-len(raw))%4)
        duplicate=struct.pack('<III',0x46546c67,2,28+len(raw)+len(b))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(b),0x004e4942)+b
        with self.assertRaisesRegex(AssetError,'duplicate'):validate_glb(duplicate)
        raw=b'['*20+b'0'+b']'*20;raw+=b' '*((-len(raw))%4)
        nested=struct.pack('<III',0x46546c67,2,28+len(raw)+len(b))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(b),0x004e4942)+b
        with self.assertRaisesRegex(AssetError,'nesting'):validate_glb(nested)
        bad=bytearray(blob);struct.pack_into('<I',bad,16,0x44444444)
        with self.assertRaises(AssetError):validate_glb(bytes(bad))
        s=simple();s['entities'][0]['transform']={};s['entities'][0]['transform']['translation']=s
        with self.assertRaises(core.SceneError):core.validate_scene(s)


if __name__=='__main__':
    unittest.main()
