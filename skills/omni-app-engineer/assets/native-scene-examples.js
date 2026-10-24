/* Original synthetic geometry fixtures, not prescribed App layouts or live data. */
(function(scope){
  "use strict";
  const material=(id,color,texture)=>({id,label:id,color,roughness:0.65,metalness:0.1,...(texture?{texture}:{})});
  const entity=(id,geometry,mat,position=[0,0,0],role="decorative",parent)=>({id,label:id.replace(/_/g," "),geometry,material:mat,
    position,rotation:[0,0,0],scale:[1,1,1],role,...(parent?{parent}:{})});
  const view=(id,position,target=[0,0,0])=>({id,label:id.replace(/_/g," "),position,target});
  const base=(source,kind="illustrative")=>({schema_version:"oaa-native-scene-v1",units:"m",axes:"right-handed-y-up",
    fidelity:{kind,source,notes:"Original synthetic fixture; no real site, customer data or brand assets."},
    materials:[],geometries:[],entities:[],views:[],render:{width:1280,height:720,dpr:1,shadows:false}});
  function venue(){
    const s=base("Fictional open-air venue brief; schematic proportions only.");
    s.materials=[material("stone","#637482"),material("surface","#172b33",{kind:"stripes",size:128,background:"#172b33",foreground:"#245464",repeat:8})];
    s.geometries=[{id:"stage",kind:"box",width:12,height:1,depth:8}];
    s.entities=[entity("stage","stage","surface")];
    // Open terraces use separate banks; circulation is kept empty and visible.
    for(let i=0;i<4;i++){
      s.geometries.push({id:`tier_${i}`,kind:"box",width:18+i*4,height:0.8,depth:2});
      s.entities.push(entity(`north_tier_${i}`,`tier_${i}`,"stone",[0,0.4+i*1.1,-8-i*2.2]));
      s.entities.push(entity(`south_tier_${i}`,`tier_${i}`,"stone",[0,0.4+i*1.1,8+i*2.2]));
    }
    s.views=[view("orientation",[30,24,32]),view("stage_view",[0,7,24],[0,1,0]),view("circulation",[24,9,0],[0,1,0])];
    return s;
  }
  function network(){
    const s=base("Synthetic branched utility network. Geometry is schematic; values are a separate governed contract.");
    s.materials=[material("pipe","#346c83"),material("junction","#b0bac0")];
    s.geometries=[{id:"node",kind:"cylinder",radiusTop:0.6,radiusBottom:0.6,height:0.8,radialSegments:24,capped:true},
      {id:"main",kind:"tube",path:[[-6,0,0],[0,0,0],[6,0,0]],radius:0.22,radialSegments:16,capped:true},
      {id:"branch",kind:"tube",path:[[0,0,0],[0,0,-5]],radius:0.22,radialSegments:16,capped:true}];
    s.entities=[entity("main_pipe","main","pipe"),entity("branch_pipe","branch","pipe"),
      entity("supply","node","junction",[-6,0,0],"analytical"),entity("junction_a","node","junction",[0,0,0],"analytical"),
      entity("consumer","node","junction",[6,0,0],"analytical"),entity("branch_end","node","junction",[0,0,-5],"analytical")];
    s.views=[view("network_overview",[12,14,12],[0,0,-1]),view("junction_inspection",[3,4,3])];return s;
  }
  function product(){
    const s=base("Supplied synthetic dimensions: body diameter 0.24m, height 0.4m, lid diameter 0.26m. Inspection tolerance 0.001m; not manufacturing certification.","reference-based");
    s.materials=[material("shell","#6c828d",{kind:"panels",size:128,background:"#6c828d",foreground:"#536875",repeat:6}),material("cap","#202d33")];
    s.geometries=[{id:"body",kind:"revolution",profile:[[0.12,0],[0.12,0.4]],radialSegments:64,capped:true},
      {id:"lid",kind:"cylinder",radiusTop:0.13,radiusBottom:0.13,height:0.03,radialSegments:64,capped:true}];
    s.entities=[entity("body","body","shell"),entity("lid","lid","cap",[0,0.415,0],"decorative","body")];
    s.views=[view("product_overview",[0.8,0.65,0.8],[0,0.2,0]),view("lid_detail",[0.3,0.7,0.3],[0,0.4,0])];return s;
  }
  scope.OAANativeSceneExamples=Object.freeze({venue,network,product});
})(typeof globalThis!=="undefined"?globalThis:this);
