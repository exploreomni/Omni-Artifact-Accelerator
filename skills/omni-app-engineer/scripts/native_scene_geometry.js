/* Original bounded procedural meshes in meters, right-handed Y-up. No loaders,
 * packages, renderer, worker or native APIs. Validate/count before typed arrays. */
(function(scope){
  "use strict";
  const add=(a,b)=>a.map((x,i)=>x+b[i]),sub=(a,b)=>a.map((x,i)=>x-b[i]),mul=(a,s)=>a.map(x=>x*s);
  const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const unit=a=>{const n=Math.hypot(...a);if(!(n>1e-12))throw new Error("native_scene.geometry_direction");return mul(a,1/n);};
  function build(supplied){
    if(!scope.OAANativeSceneContract)throw new Error("native_scene.contract_required");
    const {geometry:g,budget}=scope.OAANativeSceneContract.geometryInfo(supplied);
    const positions=new Float32Array(budget.vertices*3),normals=new Float32Array(budget.vertices*3),uvs=new Float32Array(budget.vertices*2),indices=new Uint32Array(budget.triangles*3);
    let vi=0,ii=0;
    function vertex(p,n,uv){const index=vi++;positions.set(p,index*3);normals.set(n,index*3);uvs.set(uv,index*2);return index;}
    function triangle(a,b,c){indices.set([a,b,c],ii);ii+=3;}
    if(g.kind==="box"){
      const x=g.width/2,y=g.height/2,z=g.depth/2;
      const faces=[[[x,0,0],[0,0,-z],[0,y,0],[1,0,0]],[[-x,0,0],[0,0,z],[0,y,0],[-1,0,0]],
        [[0,y,0],[x,0,0],[0,0,-z],[0,1,0]],[[0,-y,0],[x,0,0],[0,0,z],[0,-1,0]],
        [[0,0,z],[x,0,0],[0,y,0],[0,0,1]],[[0,0,-z],[-x,0,0],[0,y,0],[0,0,-1]]];
      for(const [center,u,v,n]of faces){const start=vi;for(const [a,b]of [[-1,-1],[1,-1],[1,1],[-1,1]])vertex(add(center,add(mul(u,a),mul(v,b))),n,[(a+1)/2,(b+1)/2]);triangle(start,start+1,start+2);triangle(start,start+2,start+3);}
    }else if(g.kind==="cylinder"||g.kind==="revolution"){
      const profile=g.kind==="cylinder"?[[g.radiusBottom,-g.height/2],[g.radiusTop,g.height/2]]:g.profile;
      const count=g.radialSegments,stride=count+1,span=profile.at(-1)[1]-profile[0][1];
      for(let row=0;row<profile.length;row++){
        const before=profile[Math.max(0,row-1)],after=profile[Math.min(profile.length-1,row+1)],dr=after[0]-before[0],dy=after[1]-before[1];
        for(let col=0;col<=count;col++){const theta=2*Math.PI*col/count,c=Math.cos(theta),s=Math.sin(theta);
          vertex([profile[row][0]*c,profile[row][1],profile[row][0]*s],unit([dy*c,-dr,dy*s]),[col/count,(profile[row][1]-profile[0][1])/span]);}
      }
      for(let row=0;row<profile.length-1;row++)for(let col=0;col<count;col++){
        const a=row*stride+col,b=(row+1)*stride+col;
        if(profile[row+1][0]>0)triangle(a,b,b+1);
        if(profile[row][0]>0)triangle(a,b+1,a+1);
      }
      if(g.capped)for(const [row,sign]of [[0,-1],[profile.length-1,1]]){
        const [r,y]=profile[row];if(r===0)continue;const center=vertex([0,y,0],[0,sign,0],[0.5,0.5]),ring=vi;
        for(let col=0;col<=count;col++){const theta=2*Math.PI*col/count,c=Math.cos(theta),s=Math.sin(theta);vertex([r*c,y,r*s],[0,sign,0],[(c+1)/2,(s+1)/2]);}
        for(let col=0;col<count;col++)sign>0?triangle(center,ring+col+1,ring+col):triangle(center,ring+col,ring+col+1);
      }
    }else if(g.kind==="extrusion"){
      const p=g.points,n=p.length,x0=Math.min(...p.map(q=>q[0])),x1=Math.max(...p.map(q=>q[0])),z0=Math.min(...p.map(q=>q[1])),z1=Math.max(...p.map(q=>q[1]));
      for(const [y,sign]of [[0,-1],[g.height,1]]){const start=vi;for(const q of p)vertex([q[0],y,q[1]],[0,sign,0],[(q[0]-x0)/(x1-x0),(q[1]-z0)/(z1-z0)]);
        for(let i=1;i<n-1;i++)sign>0?triangle(start,start+i+1,start+i):triangle(start,start+i,start+i+1);}
      const lengths=p.map((q,i)=>Math.hypot(p[(i+1)%n][0]-q[0],p[(i+1)%n][1]-q[1])),total=lengths.reduce((a,b)=>a+b,0);let along=0;
      for(let i=0;i<n;i++){const a=p[i],b=p[(i+1)%n],normal=unit([b[1]-a[1],0,a[0]-b[0]]),start=vi,u0=along/total,u1=(along+lengths[i])/total;
        vertex([a[0],0,a[1]],normal,[u0,0]);vertex([a[0],g.height,a[1]],normal,[u0,1]);vertex([b[0],g.height,b[1]],normal,[u1,1]);vertex([b[0],0,b[1]],normal,[u1,0]);
        triangle(start,start+1,start+2);triangle(start,start+2,start+3);along+=lengths[i];}
    }else if(g.kind==="tube"){
      const path=g.path,count=g.radialSegments,stride=count+1,dirs=[],dist=[0];
      for(let i=1;i<path.length;i++){const d=sub(path[i],path[i-1]);dirs.push(unit(d));dist.push(dist.at(-1)+Math.hypot(...d));}
      const tangents=path.map((_,i)=>i===0?dirs[0]:i===path.length-1?dirs.at(-1):unit(add(dirs[i-1],dirs[i]))),frames=[];
      let u=unit(cross(Math.abs(tangents[0][1])<0.9?[0,1,0]:[1,0,0],tangents[0]));
      for(let row=0;row<path.length;row++){
        const t=tangents[row];if(row){const axis=cross(tangents[row-1],t),s=Math.hypot(...axis),c=Math.max(-1,Math.min(1,dot(tangents[row-1],t)));
          if(s>1e-10){const k=mul(axis,1/s);u=add(add(mul(u,c),mul(cross(k,u),s)),mul(k,dot(k,u)*(1-c)));}
          u=unit(sub(u,mul(t,dot(t,u))));}
        const v=unit(cross(t,u));frames.push([u,v]);
        for(let col=0;col<=count;col++){const theta=2*Math.PI*col/count,n=add(mul(u,Math.cos(theta)),mul(v,Math.sin(theta)));
          vertex(add(path[row],mul(n,g.radius)),n,[col/count,dist[row]/dist.at(-1)]);}
      }
      for(let row=0;row<path.length-1;row++)for(let col=0;col<count;col++){const a=row*stride+col,b=(row+1)*stride+col;triangle(a,a+1,b+1);triangle(a,b+1,b);}
      if(g.capped)for(const [row,sign]of [[0,-1],[path.length-1,1]]){
        const normal=mul(tangents[row],sign),center=vertex(path[row],normal,[0.5,0.5]),ring=vi,[a,b]=frames[row];
        for(let col=0;col<=count;col++){const theta=2*Math.PI*col/count,c=Math.cos(theta),s=Math.sin(theta);vertex(add(path[row],mul(add(mul(a,c),mul(b,s)),g.radius)),normal,[(c+1)/2,(s+1)/2]);}
        for(let col=0;col<count;col++)sign>0?triangle(center,ring+col,ring+col+1):triangle(center,ring+col+1,ring+col);
      }
    }
    if(vi!==budget.vertices||ii!==budget.triangles*3)throw new Error("native_scene.geometry_count_mismatch");
    // Catch a quantized collapse or unsupported ring folding in actual output,
    // rather than returning a mesh whose normals disagree with its triangles.
    for(let i=0;i<indices.length;i+=3){const a=indices[i]*3,b=indices[i+1]*3,c=indices[i+2]*3;
      const x=positions[b]-positions[a],y=positions[b+1]-positions[a+1],z=positions[b+2]-positions[a+2],
        u=positions[c]-positions[a],v=positions[c+1]-positions[a+1],w=positions[c+2]-positions[a+2],
        nx=y*w-z*v,ny=z*u-x*w,nz=x*v-y*u;
      const agreement=nx*(normals[a]+normals[b]+normals[c])+ny*(normals[a+1]+normals[b+1]+normals[c+1])+nz*(normals[a+2]+normals[b+2]+normals[c+2]);
      if(!(agreement>0&&Number.isFinite(agreement)))throw new Error("native_scene.quantized_or_folded_triangle");}
    return Object.freeze({positions,normals,uvs,indices});
  }
  scope.OAANativeSceneGeometry=Object.freeze({build});
})(globalThis);
