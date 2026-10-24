/* Original Canvas2D recipes. No image/font downloads, DOM insertion, packages,
 * decoding or analytical values. Caller owns canvas/texture lifecycle. */
(function(scope){
  "use strict";
  function paint(supplied,canvas){
    if(!scope.OAANativeSceneContract)throw new Error("native_scene.contract_required");
    const {recipe:r}=scope.OAANativeSceneContract.textureInfo(supplied);
    if(!canvas||typeof canvas.getContext!=="function")throw new Error("native_scene.canvas_required");
    const ctx=canvas.getContext("2d");if(!ctx||typeof ctx.fillRect!=="function"||typeof ctx.fillText!=="function"||typeof ctx.save!=="function"||typeof ctx.restore!=="function")throw new Error("native_scene.canvas2d_required");
    canvas.width=r.size;canvas.height=r.size;const cell=r.size/r.repeat;
    ctx.save();try{ctx.globalAlpha=1;ctx.globalCompositeOperation="source-over";ctx.fillStyle=r.background;ctx.fillRect(0,0,r.size,r.size);ctx.fillStyle=r.foreground;
      if(r.kind==="stripes")for(let i=0;i<r.repeat;i++)ctx.fillRect(i*cell,0,cell/2,r.size);
      else if(r.kind==="grid"){const line=Math.max(1,Math.floor(cell/16));for(let i=0;i<r.repeat;i++){ctx.fillRect(i*cell,0,line,r.size);ctx.fillRect(0,i*cell,r.size,line);}}
      else if(r.kind==="panels"){const gap=Math.min(cell/4,Math.max(1,cell/12));for(let y=0;y<r.repeat;y++)for(let x=0;x<r.repeat;x++)ctx.fillRect(x*cell+gap,y*cell+gap,cell-2*gap,cell-2*gap);}
      else{ctx.textAlign="center";ctx.textBaseline="middle";ctx.font="600 "+Math.max(1,Math.floor(Math.min(cell*0.55,r.size/(r.label.length*0.7+2))))+"px sans-serif";
        for(let row=0;row<r.repeat;row++)ctx.fillText(r.label,r.size/2,(row+0.5)*cell,r.size*0.9);}
    }finally{ctx.restore();}return canvas;
  }
  scope.OAANativeSceneTextures=Object.freeze({paint});
})(globalThis);
