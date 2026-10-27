// Preview of the same layered weighted meshes. Runtime playback uses native Spine.
class RigPreview {
  constructor(canvas,data){
    this.canvas=canvas;this.data=data;const gl=this.gl=canvas.getContext('webgl2',{alpha:true,antialias:true});
    if(!gl)throw new Error('预览需要 WebGL 2');
    const vertex=`#version 300 es
    in vec2 a_p0;in vec2 a_p1;in vec2 a_p2;in vec2 a_p3;in vec2 a_uv;in vec4 a_indices;in vec4 a_weights;
    uniform mat3 u_bones[${data.bones.length}];uniform vec2 u_resolution;uniform vec3 u_view;out vec2 v_uv;
    void main(){vec3 v=(u_bones[int(a_indices.x)]*vec3(a_p0,1))*a_weights.x+(u_bones[int(a_indices.y)]*vec3(a_p1,1))*a_weights.y+(u_bones[int(a_indices.z)]*vec3(a_p2,1))*a_weights.z+(u_bones[int(a_indices.w)]*vec3(a_p3,1))*a_weights.w;
    vec2 s=vec2(u_view.x+v.x*u_view.z,u_view.y-v.y*u_view.z);gl_Position=vec4(s.x/u_resolution.x*2.-1.,1.-s.y/u_resolution.y*2.,0,1);v_uv=a_uv;}`;
    const fragment=`#version 300 es
    precision mediump float;in vec2 v_uv;uniform sampler2D u_texture;uniform float u_alpha;out vec4 outColor;
    void main(){vec4 c=texture(u_texture,v_uv);outColor=vec4(c.rgb,c.a*u_alpha);}`;
    const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s};
    this.program=gl.createProgram();gl.attachShader(this.program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(this.program);
    if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(this.program));gl.useProgram(this.program);
    this.loc=Object.fromEntries(['bones[0]','resolution','view','alpha'].map(n=>[n,gl.getUniformLocation(this.program,'u_'+n)]));
    this.parents=data.bones.map(b=>data.bones.findIndex(p=>p.name===b.parent));this.bind=[];
    data.bones.forEach((b,i)=>{const p=this.parents[i]>=0?this.bind[this.parents[i]]:[0,0];this.bind.push([p[0]+(b.x||0),p[1]+(b.y||0)])});
    this.textures={};this.pageSizes={};this.meshes={};this.ready=false;
    Promise.all(Object.entries(RIG_TEXTURES).map(([name,url])=>new Promise(resolve=>{
      const im=new Image();im.onload=()=>{const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);this.textures[name]=t;this.pageSizes[name]=[im.width,im.height];resolve()};im.onerror=()=>{document.querySelector('.note').textContent='贴图读取失败：'+name};im.src=url;
    }))).then(()=>{this.buildMeshes();this.ready=true});
    gl.enable(gl.BLEND);gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
    this.name='idle_loop';this.started=performance.now();this.loop=true;this.from=null;
    this.durations=Object.fromEntries(Object.entries(data.animations).map(([n,c])=>[n,Math.max(...Object.values(c.bones).flatMap(t=>Object.values(t).map(k=>k.at(-1).time)))]));
    this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  buildMeshes(){
    const gl=this.gl;
    for(const[slot,parts]of Object.entries(this.data.skins[0].attachments))for(const[name,m]of Object.entries(parts)){
      const region=this.data.preview_regions[m.path],[rx,ry,rw,rh]=region.rect,[pw,ph]=this.pageSizes[region.page],values=[];let cursor=0;
      for(let i=0;i<m.uvs.length;i+=2){
        const n=m.vertices[cursor++],indices=[0,0,0,0],weights=[0,0,0,0],positions=Array(8).fill(0);
        for(let j=0;j<n;j++){indices[j]=m.vertices[cursor];positions[j*2]=m.vertices[cursor+1];positions[j*2+1]=m.vertices[cursor+2];weights[j]=m.vertices[cursor+3];cursor+=4}
        values.push(...positions,(rx+m.uvs[i]*rw)/pw,(ry+m.uvs[i+1]*rh)/ph,...indices,...weights);
      }
      const vao=gl.createVertexArray();gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);
      for(const[n,size,offset]of [['a_p0',2,0],['a_p1',2,8],['a_p2',2,16],['a_p3',2,24],['a_uv',2,32],['a_indices',4,40],['a_weights',4,56]]){const l=gl.getAttribLocation(this.program,n);gl.enableVertexAttribArray(l);gl.vertexAttribPointer(l,size,gl.FLOAT,false,72,offset)}
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(m.triangles),gl.STATIC_DRAW);
      this.meshes[slot+'/'+name]={vao,page:region.page,count:m.triangles.length};
    }
  }
  value(keys,t,neutral){
    if(!keys)return neutral;if(t<=keys[0].time)return keys[0].value;
    let i=0;while(i+1<keys.length&&keys[i+1].time<t)i++;if(i===keys.length-1)return keys[i].value;
    const a=keys[i],b=keys[i+1];if(a.curve==='stepped')return a.value;if(!a.curve)return a.value+(b.value-a.value)*(t-a.time)/(b.time-a.time);
    const bez=(a,b,c,d,s)=>{const r=1-s;return r*r*r*a+3*r*r*s*b+3*r*s*s*c+s*s*s*d};let lo=0,hi=1;
    for(let j=0;j<16;j++){const s=(lo+hi)/2;if(bez(a.time,a.curve[0],a.curve[2],b.time,s)<t)lo=s;else hi=s}
    return bez(a.value,a.curve[1],a.curve[3],b.value,(lo+hi)/2);
  }
  duration(name){return this.durations[name]}
  time(now){const t=Math.max(0,(now-this.started)/1000),d=this.duration(this.name);return this.loop?(this.reduced?0:t%d):Math.min(t,d)}
  sample(now){
    const clip=this.data.animations[this.name],t=this.time(now);
    const result=this.data.bones.map(b=>{const k=clip.bones[b.name]||{};return [this.value(k.translatex,t,0),this.value(k.translatey,t,0),this.value(k.rotate,t,0),this.value(k.scalex,t,1),this.value(k.scaley,t,1)]});
    if(this.from){const p=Math.min(1,(now-this.started)/100);for(let i=0;i<result.length;i++)for(let j=0;j<5;j++)result[i][j]=this.from[i][j]+(result[i][j]-this.from[i][j])*p;if(p>=1)this.from=null}return result;
  }
  play(name,loop){const now=performance.now();this.from=this.sample(now);this.name=name;this.started=now;this.loop=loop}
  draw(now){
    if(!this.ready)return;
    const gl=this.gl,r=this.canvas.getBoundingClientRect(),d=devicePixelRatio||1,w=Math.round(r.width*d),h=Math.round(r.height*d);
    if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h}
    gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(this.program);
    const local=this.sample(now),world=[],packed=[];
    this.data.bones.forEach((bone,i)=>{const[x,y,degrees,sx,sy]=local[i],a=(degrees+(bone.rotation||0))*Math.PI/180,c=Math.cos(a),s=Math.sin(a),xs=sx*(bone.scaleX??1),ys=sy*(bone.scaleY??1),m=[c*xs,s*xs,-s*ys,c*ys,(bone.x||0)+x,(bone.y||0)+y],p=this.parents[i]>=0?world[this.parents[i]]:[1,0,0,1,0,0];
      const tx=p[0]*m[4]+p[2]*m[5]+p[4],ty=p[1]*m[4]+p[3]*m[5]+p[5];
      let v;if(bone.inherit==='noScale'){const ax=p[0]*c+p[2]*s,ay=p[1]*c+p[3]*s,r=Math.hypot(ax,ay)||1;v=[ax/r*xs,ay/r*xs,-ay/r*ys,ax/r*ys,tx,ty]}
      else v=[p[0]*m[0]+p[2]*m[1],p[1]*m[0]+p[3]*m[1],p[0]*m[2]+p[2]*m[3],p[1]*m[2]+p[3]*m[3],tx,ty];
      world.push(v);packed.push(v[0],v[1],0,v[2],v[3],0,v[4],v[5],1);

    });
    this.world=world;
    this.view=[r.width*.48,r.height-36,Math.min(r.width/570,(r.height-75)/443)];
    gl.uniformMatrix3fv(this.loc['bones[0]'],false,new Float32Array(packed));gl.uniform2f(this.loc.resolution,r.width,r.height);gl.uniform3f(this.loc.view,...this.view);
    const clip=this.data.animations[this.name],t=this.time(now);
    for(const slot of this.data.slots){
      const k=clip.slots[slot.name];let name=slot.attachment;for(const key of k?.attachment||[])if(key.time<=t)name=key.name;
      if(!name)continue;const m=this.meshes[slot.name+'/'+name];if(!m)continue;
      const alphaKeys=k?.rgba?.map(v=>({time:v.time,value:parseInt(v.color.slice(6,8),16)/255,curve:v.curve}));const alpha=this.value(alphaKeys,t,1);if(alpha<.001)continue;
      gl.uniform1f(this.loc.alpha,alpha);gl.bindTexture(gl.TEXTURE_2D,this.textures[m.page]);gl.bindVertexArray(m.vao);gl.drawElements(gl.TRIANGLES,m.count,gl.UNSIGNED_SHORT,0);
    }
  }
}
