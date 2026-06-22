/* Shockwave site — theme, reveals, hero blast map */
(function(){
  // ---- theme ----
  const KEY = 'shockwave-theme';
  const root = document.documentElement;
  function set(t){ root.setAttribute('data-theme', t); try{ localStorage.setItem(KEY,t); }catch(e){} }
  const saved = (()=>{ try{ return localStorage.getItem(KEY); }catch(e){ return null; } })();
  set(saved || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));
  window.toggleTheme = ()=> set(root.getAttribute('data-theme')==='light' ? 'dark' : 'light');
  document.addEventListener('click', e=>{ if(e.target.closest('#themeBtn')) toggleTheme(); });

  // ---- scroll reveals ----
  const io = new IntersectionObserver((es)=>es.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } }), {threshold:.14});
  addEventListener('DOMContentLoaded', ()=> document.querySelectorAll('.rv').forEach(el=>io.observe(el)));
})();

/* hero blast map — baked sample so it's always alive (no backend needed) */
function shockwaveHero(elId){
  if(!window.d3) return;
  const svg = d3.select('#'+elId); if(svg.empty()) return;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DC = ['#FFE6A0','#FF6F5E','#E0479E','#7C84F2'];
  const nodes=[{id:'c',d:0,role:'epi'}]; let k=0;
  const ring=(depth,count,role)=>{ for(let i=0;i<count;i++) nodes.push({id:'n'+(k++),d:depth,role:role||'n'}); };
  ring(1,7); ring(2,9); ring(3,6);
  nodes.push({id:'e1',d:1,role:'entry'},{id:'e2',d:2,role:'entry'});
  for(let i=0;i<10;i++) nodes.push({id:'t'+i,d:3,role:'test'});
  const links=[], byDepth={};
  nodes.forEach(n=>{(byDepth[n.d]=byDepth[n.d]||[]).push(n);});
  nodes.forEach(n=>{ if(n.d===0) return; const up=byDepth[n.d-1]||byDepth[0]; const t=up[(n.id.length*7+n.d*3)%up.length]; links.push({source:n.id,target:t.id}); });
  let sim;
  function draw(){
    svg.selectAll('*').remove();
    const W=svg.node().clientWidth||640, H=380, cx=W/2, cy=H/2, maxD=3, gap=Math.min(W,H)/2.5/maxD;
    const g=svg.append('g');
    for(let i=1;i<=maxD;i++) g.append('circle').attr('cx',cx).attr('cy',cy).attr('r',i*gap).attr('fill','none').attr('stroke','#16203a');
    const link=g.append('g').selectAll('line').data(links).join('line').attr('stroke','#212C49').attr('stroke-width',1);
    const node=g.append('g').selectAll('circle').data(nodes).join('circle')
      .attr('r',n=>n.role==='epi'?11:(n.role==='entry'?6:(n.role==='test'?3:4.5)))
      .attr('fill',n=>n.role==='test'?'#39B98A':(n.role==='entry'?'#2FE6D6':DC[Math.min(n.d,3)]))
      .attr('opacity',n=>n.role==='test'?.5:1)
      .attr('stroke',n=>n.role==='entry'?'#2FE6D6':'rgba(0,0,0,.35)')
      .attr('stroke-width',n=>n.role==='entry'?2:1)
      .style('filter',n=>n.role==='entry'?'drop-shadow(0 0 6px #2FE6D6)':(n.role==='epi'?'drop-shadow(0 0 12px #FFE6A0)':'none'));
    const epi=nodes[0]; epi.fx=cx; epi.fy=cy;
    sim && sim.stop();
    sim=d3.forceSimulation(nodes)
      .force('link',d3.forceLink(links).id(n=>n.id).distance(gap*.8).strength(.12))
      .force('charge',d3.forceManyBody().strength(-70))
      .force('radial',d3.forceRadial(n=>n.d*gap,cx,cy).strength(.95))
      .force('collide',d3.forceCollide(8))
      .on('tick',()=>{ link.attr('x1',l=>l.source.x).attr('y1',l=>l.source.y).attr('x2',l=>l.target.x).attr('y2',l=>l.target.y);
        node.attr('cx',n=>n.x).attr('cy',n=>n.y); });
    if(reduce){ sim.tick(140); sim.stop(); return; }
    const pulse=()=>{ const p=svg.insert('circle',':first-child').attr('cx',cx).attr('cy',cy).attr('r',8)
      .attr('fill','none').attr('stroke','#FFE6A0').attr('stroke-width',2).attr('opacity',.5);
      p.transition().duration(1600).ease(d3.easeCubicOut).attr('r',maxD*gap+24).attr('opacity',0).remove(); };
    pulse(); clearInterval(window.__hp); window.__hp=setInterval(pulse,4200);
  }
  draw(); addEventListener('resize',()=>{ clearTimeout(window.__hr); window.__hr=setTimeout(draw,200); });
}
