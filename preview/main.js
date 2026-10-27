const labels=['待机','攻击','施法','防御','受击恼火','趴地','蓄力','胜利'];
const actor=document.querySelector('#actor'),body=document.querySelector('#body');
const controls=document.querySelector('#controls'),poses=document.querySelector('#poses'),cards=document.querySelector('#cards');
const canvas=document.querySelector('#fx'),ctx=canvas.getContext('2d');
const poseImage="url('../assets/sprites/offer-master-v0.8.5.png')";
const animationNames=['idle_loop','attack','cast','guard','hurt','death','channel','victory_loop'];
const motionLabels={idle_loop:'呼吸待机',attack:'直击',cast:'施法',guard:'防御',hurt:'受击',death:'倒下',channel:'蓄力',victory_loop:'胜利',idle_look_loop:'侧头观察',idle_ready_loop:'备战待机',idle_relax_loop:'放松摆尾',attack_sweep:'横挥',attack_double:'连击',attack_ranged:'远程出手',cast_arc:'弧线施法',cast_release:'蓄势释放',guard_brace:'撑持护盾',channel_release:'聚能释放',hurt_recover:'受击恢复',greeting:'入场致意',meditate_loop:'闭眼冥想',victory_wave_loop:'挥手庆祝'};
Object.assign(motionLabels,{idle_breathe_loop:'深呼吸',idle_hair_loop:'整理头发',idle_hand_loop:'活动手腕',idle_tail_loop:'轻摆鲸尾',idle_angry_loop:'恼火握拳',attack_jab:'短直拳',attack_cross:'交替交叉拳',attack_uppercut:'上挑拳',attack_triple:'三连拳',attack_palm:'送掌',attack_overhead:'上举重击',cast_dual:'双手施法',cast_point:'掌心引导',cast_circle:'转腕画弧',guard_raise:'抬臂格挡',guard_cross:'交叉防御',guard_push:'推开护盾',channel_gather:'双手聚能',channel_pulse:'脉冲蓄力',channel_overdrive:'过载释放',hurt_recoil:'短促后撤',hurt_stagger:'站稳回瞪',hurt_counter:'握拳恼火',greeting_wave:'入场挥手',greeting_bow:'入场鞠躬',victory_pose_loop:'举拳庆祝',rest_sleep_loop:'闭眼小憩',revive:'重新起身',death:'向前趴地'});
const families=[['idle_loop','idle_look_loop','idle_ready_loop','idle_relax_loop','idle_breathe_loop','idle_hair_loop','idle_hand_loop','idle_tail_loop'],Object.keys(RIG_DATA.animations).filter(n=>n==='attack'||n.startsWith('attack_')),Object.keys(RIG_DATA.animations).filter(n=>n==='cast'||n.startsWith('cast_')),Object.keys(RIG_DATA.animations).filter(n=>n==='guard'||n.startsWith('guard_')),Object.keys(RIG_DATA.animations).filter(n=>n==='hurt'||n.startsWith('hurt_')),['death'],Object.keys(RIG_DATA.animations).filter(n=>n==='channel'||n.startsWith('channel_')),['victory_loop','victory_wave_loop','victory_pose_loop']];
Object.assign(motionLabels,{attack:'踏步推掌',attack_jab:'短促推掌',attack_cross:'转身送掌',attack_uppercut:'抬手挑击',attack_triple:'三连击',guard_cross:'抬掌护身',idle_angry_loop:'恼火待机',hurt_counter:'抬手恼火',victory_pose_loop:'抬手庆祝'});
const familyCounts=Array(8).fill(0);
let rig,poseTimer,effect=null,angerAt=null;
try{rig=new RigPreview(document.querySelector('#rig'),RIG_DATA);actor.style.display='none'}
catch(error){document.querySelector('.note').textContent=error.message+' 下方保留原始姿态素材。'}
function pos(i,cols){return `${i%cols/(cols-1)*100}% ${Math.floor(i/cols)/(cols===4?1:3)*100}%`}
function showPose(i){
  showClip(families[i][familyCounts[i]++%families[i].length]);
  body.style.backgroundImage=poseImage;body.style.backgroundSize='contain';body.style.backgroundRepeat='no-repeat';body.style.backgroundPosition='center';
  if([1,2,3,6].includes(i))effect={t:performance.now(),color:'#67cfff',guard:i===3};
}
function showClip(name){
  clearTimeout(poseTimer);
  if(name.startsWith('hurt'))angerAt=performance.now();else if(name==='death')angerAt=null;
  const loop=name.endsWith('_loop');rig?.play(name,loop);
  controls.querySelectorAll('button').forEach((b,j)=>b.classList.toggle('active',name===animationNames[j]));
  document.querySelector('#animation-select').value=name;
  if(name==='idle_angry_loop')poseTimer=setTimeout(()=>showClip('idle_loop'),(rig?.duration(name)||3)*1000);
  if(!loop&&name!=='death'){
    const next=name.startsWith('hurt')?'idle_angry_loop':name.startsWith('attack')?'idle_ready_loop':name.startsWith('guard')?'idle_look_loop':'idle_relax_loop';
    poseTimer=setTimeout(()=>showClip(next),(rig?.duration(name)||.75)*1000);
  }
}
const motionSelect=document.querySelector('#animation-select');
for(const name of Object.keys(RIG_DATA.animations)){const option=document.createElement('option');option.value=name;option.textContent=motionLabels[name]||name;motionSelect.append(option)}
motionSelect.onchange=e=>showClip(e.target.value);
labels.forEach((label,i)=>{
  const b=document.createElement('button');b.textContent=label;b.onclick=()=>showPose(i);controls.append(b);
  const p=document.createElement('div');p.className='pose';const art=document.createElement('div');art.className='pose-art';
  art.style.backgroundPosition=pos(i,4);art.setAttribute('role','img');art.setAttribute('aria-label',label);p.append(art);
  const text=document.createElement('small');text.textContent=label;p.append(text);p.onclick=()=>showPose(i);poses.append(p);
});
['闪电','冰霜','黑暗','等离子','玻璃'].forEach((label,i)=>{
  const cell=document.createElement('div');cell.style.textAlign='center';const art=document.createElement('div');
  art.style.cssText=`aspect-ratio:1;background-image:url('../assets/effects/elemental-orbs.png');background-size:300% 200%;background-position:${i%3/2*100}% ${Math.floor(i/3)*100}%;`;
  art.setAttribute('role','img');art.setAttribute('aria-label',label+'卡通球');const caption=document.createElement('small');
  caption.textContent=label;cell.append(art,caption);document.querySelector('#elementals').append(cell);
});
const colors=[[/frost|ice|cold|chill|glacier|hail|coolant/,'#b9f2ff'],[/dark|shadow|null|consume/,'#ae89ff'],[/plasma|fusion|meteor|ignition|energy/,'#ffd982'],[/glass|refract|shatter/,'#81ffe2']];
function render(filter=''){
  cards.replaceChildren();let n=0;
  for(const[id,v]of Object.entries(CARD_INDEX)){
    if(!id.includes(filter.toLowerCase().replaceAll(' ','_')))continue;
    const card=document.createElement('article');card.className='card';const art=document.createElement('div');art.className='card-art';
    art.style.backgroundImage=`url('../assets/cards/${v.file||v.sheet_file||`cards-${String(v.sheet).padStart(2,'0')}.png`}')`;
    art.style.backgroundPosition=v.file?'center':pos(v.slot,5);if(v.file)art.style.backgroundSize='cover';art.setAttribute('role','img');art.setAttribute('aria-label',id.replaceAll('_',' '));
    const name=document.createElement('p');name.textContent=id.replaceAll('_',' ');card.append(art,name);
    card.onclick=()=>{showPose(/strike|punch|claw|beam|barrage|sunder/.test(id)?1:2);effect={t:performance.now(),color:colors.find(([re])=>re.test(id))?.[1]||'#67cfff',guard:/defend|buffer|glacier|shield/.test(id)}};
    cards.append(card);n++;
  }
  document.querySelector('#count').textContent=n+' 项';
}
document.querySelector('#search').oninput=e=>render(e.target.value);render();showPose(0);
function animate(t){
  rig?.draw(t);
  const box=canvas.getBoundingClientRect(),d=devicePixelRatio||1;
  if(canvas.width!==Math.round(box.width*d)||canvas.height!==Math.round(box.height*d)){
    canvas.width=Math.round(box.width*d);canvas.height=Math.round(box.height*d);
  }
  ctx.setTransform(d,0,0,d,0,0);ctx.clearRect(0,0,box.width,box.height);
  if(effect){
    const p=(t-effect.t)/650;
    if(p>1)effect=null;
    else{
      ctx.globalAlpha=1-p;ctx.strokeStyle=effect.color;ctx.lineWidth=2;
      const x=200,y=box.height-165,r=(effect.guard?68:36)*(.5+p*1.5);
      ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.stroke();
      if(!effect.guard){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+(box.width-x-60)*Math.min(1,p*1.8),y-18);ctx.stroke()}
      for(let i=0;i<6;i++){const a=i*Math.PI/3;ctx.fillStyle=effect.color;ctx.fillRect(x+Math.cos(a)*r*1.4,y+Math.sin(a)*r*1.4,3,3)}
      ctx.globalAlpha=1;
    }
  }
  if(angerAt&&rig?.view){
    const elapsed=(t-angerAt)/1000;
    if(elapsed>1.34)angerAt=null;
    else if(elapsed>.2){
      const[x,y,s]=rig.view,hp=rig.world?.[RIG_DATA.bones.findIndex(b=>b.name==='ref_head')]||[1,0,0,1,28,365];ctx.save();ctx.translate(x+(hp[4]+43)*s,y-(hp[5]+53)*s);ctx.scale(s,s);ctx.globalAlpha=Math.min(1,(elapsed-.2)/.09,(1.34-elapsed)/.22);ctx.lineCap='round';ctx.lineJoin='round';
      for(let i=0;i<4;i++){ctx.save();ctx.rotate(i*Math.PI/2);ctx.beginPath();ctx.moveTo(4,-3);ctx.lineTo(4,-11);ctx.lineTo(12,-11);ctx.strokeStyle='#fff2d9';ctx.lineWidth=7;ctx.stroke();ctx.strokeStyle='#ff5748';ctx.lineWidth=4;ctx.stroke();ctx.restore()}
      for(const sx of [-120,25]){ctx.beginPath();ctx.moveTo(sx,10);ctx.bezierCurveTo(sx-12,-4,sx+9,-16,sx,-26);ctx.strokeStyle='#fff3e3';ctx.lineWidth=3;ctx.stroke()}ctx.restore();
    }
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

