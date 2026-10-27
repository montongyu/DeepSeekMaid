// Lightweight WebGL preview of our authored weighted mesh. The game uses native Spine.
class RigPreview {
  constructor(canvas,data) {
    this.canvas=canvas;this.data=data;this.gl=canvas.getContext('webgl2',{alpha:true,antialias:true});
    if(!this.gl)throw new Error('预览需要支持 WebGL 2 的浏览器。');
    const gl=this.gl;
    const vertex=`#version 300 es
      in vec2 a_position; in vec2 a_uv; in vec4 a_indices; in vec4 a_weights;
      uniform mat3 u_bones[${data.bones.length}]; uniform vec2 u_resolution; uniform vec3 u_view;
      out vec2 v_uv;
      void main(){vec3 p=vec3(a_position,1.0);
        vec3 v=(u_bones[int(a_indices.x)]*p)*a_weights.x
          +(u_bones[int(a_indices.y)]*p)*a_weights.y
          +(u_bones[int(a_indices.z)]*p)*a_weights.z
          +(u_bones[int(a_indices.w)]*p)*a_weights.w;
        vec2 screen=vec2(u_view.x+v.x*u_view.z,u_view.y-v.y*u_view.z);
        gl_Position=vec4(screen.x/u_resolution.x*2.0-1.0,1.0-screen.y/u_resolution.y*2.0,0,1);
        v_uv=a_uv;
      }`;
    const fragment=`#version 300 es
      precision mediump float; in vec2 v_uv; uniform sampler2D u_texture; out vec4 outColor;
      void main(){outColor=texture(u_texture,v_uv);}`;
    const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s};
    this.program=gl.createProgram();gl.attachShader(this.program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(this.program);
    if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(this.program));
    gl.useProgram(this.program);
    const mesh=data.skins[0].attachments.character.maid,values=[];let cursor=0;
    for(let i=0;i<mesh.uvs.length;i+=2){
      const n=mesh.vertices[cursor++],indices=[0,0,0,0],weights=[0,0,0,0];
      for(let j=0;j<n;j++){indices[j]=mesh.vertices[cursor];weights[j]=mesh.vertices[cursor+3];cursor+=4}
      const u=mesh.uvs[i],v=mesh.uvs[i+1];
      values.push(u*443-221.5,(1-v)*443,u*443/1774,v*443/887,...indices,...weights);
    }
    this.vao=gl.createVertexArray();gl.bindVertexArray(this.vao);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);
    for(const[name,size,offset]of [['a_position',2,0],['a_uv',2,8],['a_indices',4,16],['a_weights',4,32]]){
      const loc=gl.getAttribLocation(this.program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,48,offset);
    }
    const elements=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,elements);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(mesh.triangles),gl.STATIC_DRAW);this.count=mesh.triangles.length;
    this.locations={bones:gl.getUniformLocation(this.program,'u_bones[0]'),resolution:gl.getUniformLocation(this.program,'u_resolution'),view:gl.getUniformLocation(this.program,'u_view')};
    this.texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.enable(gl.BLEND);gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
    this.ready=false;const image=new Image();image.onload=()=>{gl.bindTexture(gl.TEXTURE_2D,this.texture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);this.ready=true};image.src=RIG_TEXTURE;
    this.bind=[];this.parents=data.bones.map(b=>data.bones.findIndex(p=>p.name===b.parent));
    data.bones.forEach((b,i)=>{const p=this.parents[i]>=0?this.bind[this.parents[i]]:[0,0];this.bind.push([p[0]+(b.x||0),p[1]+(b.y||0)])});
    this.name='idle_loop';this.started=performance.now();this.loop=true;this.from=null;
    this.durations=Object.fromEntries(Object.entries(data.animations).map(([name,clip])=>[name,Math.max(...Object.values(clip.bones).flatMap(tracks=>Object.values(tracks).map(keys=>keys.at(-1).time)))]));
    this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  value(keys,t,neutral){
    if(!keys)return neutral;
    if(t<=keys[0].time)return keys[0].value;
    let i=0;while(i+1<keys.length&&keys[i+1].time<t)i++;
    if(i===keys.length-1)return keys[i].value;
    const a=keys[i],b=keys[i+1];
    if(!a.curve)return a.value+(b.value-a.value)*(t-a.time)/(b.time-a.time);
    const bez=(p0,p1,p2,p3,s)=>{const r=1-s;return r*r*r*p0+3*r*r*s*p1+3*r*s*s*p2+s*s*s*p3};
    let lo=0,hi=1;for(let j=0;j<16;j++){const s=(lo+hi)/2;if(bez(a.time,a.curve[0],a.curve[2],b.time,s)<t)lo=s;else hi=s}
    return bez(a.value,a.curve[1],a.curve[3],b.value,(lo+hi)/2);
  }
  duration(name){return this.durations[name]}
  sample(now){
    const duration=this.duration(this.name);let t=Math.max(0,(now-this.started)/1000);
    if(this.loop)t%=duration;else t=Math.min(duration,t);
    if(this.reduced&&this.name==='idle_loop')t=0;
    const channels=this.data.animations[this.name].bones;
    const result=this.data.bones.map(b=>{
      const tracks=channels[b.name]||{};
      return [this.value(tracks.translatex,t,0),this.value(tracks.translatey,t,0),this.value(tracks.rotate,t,0),this.value(tracks.scalex,t,1),this.value(tracks.scaley,t,1)];
    });
    if(this.from){let p=Math.min(1,(now-this.started)/100);p=p*p*(3-2*p);for(let i=0;i<result.length;i++)for(let j=0;j<5;j++)result[i][j]=this.from[i][j]+(result[i][j]-this.from[i][j])*p;if(p>=1)this.from=null}
    return result;
  }
  play(name,loop){const now=performance.now();this.from=this.sample(now);this.name=name;this.started=now;this.loop=loop}
  draw(now){
    if(!this.ready)return;
    const gl=this.gl,rect=this.canvas.getBoundingClientRect(),ratio=devicePixelRatio||1;
    const width=Math.round(rect.width*ratio),height=Math.round(rect.height*ratio);
    if(this.canvas.width!==width||this.canvas.height!==height){this.canvas.width=width;this.canvas.height=height}
    gl.viewport(0,0,width,height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(this.program);gl.bindVertexArray(this.vao);gl.bindTexture(gl.TEXTURE_2D,this.texture);
    const local=this.sample(now),world=[],packed=[];
    this.data.bones.forEach((bone,i)=>{
      const [x,y,degrees,sx,sy]=local[i],r=degrees*Math.PI/180,c=Math.cos(r),s=Math.sin(r);
      const m=[c*sx,s*sx,-s*sy,c*sy,(bone.x||0)+x,(bone.y||0)+y];
      const p=this.parents[i]>=0?world[this.parents[i]]:[1,0,0,1,0,0];
      const w=[p[0]*m[0]+p[2]*m[1],p[1]*m[0]+p[3]*m[1],p[0]*m[2]+p[2]*m[3],p[1]*m[2]+p[3]*m[3],p[0]*m[4]+p[2]*m[5]+p[4],p[1]*m[4]+p[3]*m[5]+p[5]];world.push(w);
      const [bx,by]=this.bind[i];packed.push(w[0],w[1],0,w[2],w[3],0,w[4]-w[0]*bx-w[2]*by,w[5]-w[1]*bx-w[3]*by,1);
    });
    gl.uniformMatrix3fv(this.locations.bones,false,new Float32Array(packed));gl.uniform2f(this.locations.resolution,rect.width,rect.height);gl.uniform3f(this.locations.view,Math.min(255,rect.width*.45),rect.height-49,Math.min(370,rect.height-85)/443);
    gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_SHORT,0);
  }
}
