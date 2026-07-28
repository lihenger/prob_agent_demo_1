#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_visualization.py
=========================
读取「标准分布描述 JSON」，生成**自包含交互式 HTML 动画**文件。

功能面板：
  1. 概率密度/质量曲线动态绘制（连续描线 / 离散柱状，从左到右动画揭示）
  2. 分布函数（CDF）动态演示（由对 pdf 数值积分得到，扫过并填充面积）
  3. 参数敏感性：交互滑块实时重绘 + 右侧数字输入框可手动键入参数值
  4. 概率/分位数查询：输入 x 查 P(X≤x)、输入 p 查分位数 x_p、输入 α 画上侧临界域阴影
  5. 构造来源与抽样模拟：χ²/t/F 展示构造公式 + Box-Muller 抽样叠加经验直方图
  6. 退化告警（密度全 0 时提示）/ formula 模式归一化提示

公式渲染：KaTeX（CDN），离线/加载失败自动回退纯文本并显式提示。

用法：
  python generate_visualization.py dist.json --out normal.html
  python generate_visualization.py dist.json            # 默认输出 ./<type>_viz.html
  cat dist.json | python generate_visualization.py      # 从 stdin 读取
"""

import argparse
import json
import os
import re
import sys

import distributions_catalog as dc

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>概率分布可视化 · __TITLE__</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" crossorigin="anonymous" onerror="window.__katexFailed=true"></script>
<style>
  :root{
    --bg:#ffffff; --panel:#f7f9fc; --ink:#1f2933; --muted:#66748a;
    --line:#e2e8f0; --accent:#2563eb; --accent2:#0ea5a4; --warn:#b45309;
  }
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:var(--bg);color:var(--ink);line-height:1.55;padding:24px;}
  .wrap{max-width:980px;margin:0 auto;}
  h1{font-size:22px;margin:0 0 4px;}
  .sub{color:var(--muted);font-size:14px;margin-bottom:18px;}
  .formula-block{background:var(--panel);border:1px solid var(--line);border-radius:10px;
                 padding:12px 16px;margin:6px 0 18px;}
  .flabel{font-size:13px;color:var(--accent);font-weight:600;margin:10px 0 2px;}
  .flabel:first-child{margin-top:0;}
  .tex{font-size:17px;color:#0f172a;overflow-x:auto;padding:2px 0;}
  .cdf-note{color:var(--muted);font-size:13px;margin-top:4px;}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
  @media(max-width:760px){.grid{grid-template-columns:1fr;}}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;}
  .card h3{margin:0 0 8px;font-size:15px;color:var(--accent);}
  canvas{width:100%;height:240px;display:block;background:#fff;border-radius:8px;}
  .know{margin-top:18px;}
  .know table{width:100%;border-collapse:collapse;font-size:14px;}
  .know td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;}
  .know td.k{color:var(--muted);width:120px;white-space:nowrap;}
  .know .apps{color:var(--ink);}
  .controls{margin-top:16px;}
  .row{display:flex;align-items:center;gap:12px;margin:8px 0;flex-wrap:wrap;}
  .row label{width:64px;color:var(--muted);font-size:14px;}
  .row input[type=range]{flex:1;accent-color:var(--accent);min-width:120px;}
  .row .val{width:88px;text-align:right;font-family:monospace;font-size:14px;
            padding:4px 6px;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink);}
  button{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:8px 16px;
         font-size:14px;cursor:pointer;}
  button.sec{background:#fff;color:var(--accent);border:1px solid var(--accent);}
  .hint{color:var(--warn);font-size:13px;margin-top:10px;}
  .qrow{display:flex;align-items:center;gap:10px;margin:8px 0;flex-wrap:wrap;}
  .qrow label{width:80px;color:var(--muted);font-size:14px;}
  .qout{font-family:monospace;font-size:13px;color:var(--ink);}
  .badge{display:inline-block;background:#eef2ff;color:var(--accent);border-radius:6px;
         padding:2px 8px;font-size:12px;margin-left:8px;}
</style>
</head>
<body>
<div class="wrap">
  <h1>__TITLE__<span class="badge">__MODE__</span></h1>
  <div class="sub">概率论与数理统计 · 交互式可视化动画（公式由 KaTeX 渲染）</div>

  <div class="formula-block">
    <div class="flabel" id="pdfLabel"></div>
    <div class="tex" id="pdfTex"></div>
    <div class="flabel" id="cdfLabel"></div>
    <div class="tex" id="cdfTex"></div>
    <div class="cdf-note" id="cdfNote"></div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>① 概率密度 / 质量曲线（动态绘制）</h3>
      <canvas id="cvPdf"></canvas>
    </div>
    <div class="card">
      <h3>② 分布函数 F(x)=P(X≤x)（动态演示）</h3>
      <canvas id="cvCdf"></canvas>
    </div>
  </div>

  <div class="card controls">
    <h3>③ 参数敏感性（拖动滑块实时变形 · 或直接输入参数值）</h3>
    <div id="sliders"></div>
    <div class="row">
      <button id="reset" class="sec">重置参数</button>
      <span id="status" class="sub" style="margin:0;color:var(--muted)"></span>
    </div>
  </div>

  <div class="card" id="queryCard">
    <h3>④ 概率 / 分位数查询（x · p · α 三方联动 · 点击/拖动双图定位）</h3>
    <div class="hint" style="color:var(--muted);margin-top:0">提示：x、p、α 描述同一个点——在①密度图按 x 定位、在②分布函数图按 p 定位，或直接输入任一值，三框与双图同步更新；双击任一画布清除标记。</div>
    <div class="qrow">
      <label>查 x =</label>
      <input id="qx" type="number" class="val" style="width:120px;text-align:left" placeholder="如 1.96">
      <span class="qout" id="qxOut">P(X≤x) = —</span>
    </div>
    <div class="qrow">
      <label>查 p =</label>
      <input id="qp" type="number" class="val" style="width:120px;text-align:left" step="0.01" min="0" max="1" placeholder="如 0.95">
      <span class="qout" id="qpOut">分位数 x_p = —</span>
    </div>
    <div class="qrow">
      <label>上侧 α =</label>
      <input id="qa" type="number" class="val" style="width:120px;text-align:left" step="0.01" min="0" max="1" placeholder="如 0.05">
      <span class="qout" id="qaOut">临界值 x_{1−α} = —（PDF 画阴影）</span>
    </div>
  </div>

  <div class="card" id="simCard" style="display:none">
    <h3>⑤ 构造来源与抽样模拟（三大抽样分布）</h3>
    <div class="flabel">构造公式</div>
    <div class="tex" id="conTex"></div>
    <div class="qrow" style="margin-top:10px">
      <label>样本量 n =</label>
      <input id="simN" type="number" class="val" style="width:120px;text-align:left" value="3000" min="100" max="50000" step="100">
      <button id="simBtn">模拟抽样</button>
      <button id="simClear" class="sec">清除直方图</button>
    </div>
    <div class="hint" id="simNote">点击「模拟抽样」：从标准正态用 Box-Muller 生成样本，按构造公式构造统计量，经验直方图叠加在理论 PDF 上。</div>
  </div>

  <div class="card know" id="knowCard">
    <h3>⑥ 核心知识点</h3>
    <div id="knowBody"></div>
  </div>
</div>

<script>
/*__HELPERS__*/
var CONFIG = /*__CONFIG__*/;
var PDF = /*__PDF__*/;

(function(){
  var isD = CONFIG.is_discrete;
  var lo = CONFIG.domain[0], hi = CONFIG.domain[1];
  var p = JSON.parse(JSON.stringify(CONFIG.params));
  var N = isD ? (Math.floor(hi)-Math.floor(lo)+1) : 400;
  var xs = [], ks = [];
  if(isD){
    for(var k=Math.floor(lo);k<=Math.floor(hi);k++){ ks.push(k); }
    N = ks.length;
  } else {
    for(var i=0;i<N;i++){ xs.push(lo + (hi-lo)*i/(N-1)); }
  }
  var baseP = JSON.parse(JSON.stringify(CONFIG.params));
  var simHist=null, currentShade=null, simOutOfRange=0, clickX=null;

  function compute(){
    var pdf=[], area=0, dx = isD?1:((hi-lo)/(N-1));
    for(var i=0;i<N;i++){
      var x = isD?ks[i]:xs[i];
      var v = PDF(x,p); if(!isFinite(v)||v<0) v=0;
      pdf.push(v); area += v*dx;
    }
    var degenerate = (area<=0);
    if(area<=0) area=1;
    var cdf=[], cum=0;
    for(var j=0;j<N;j++){ cum += pdf[j]*dx; cdf.push(cum/area); }
    return {pdf:pdf, cdf:cdf, area:area, degenerate:degenerate};
  }
  var data = compute();

  // ---------- 画布 ----------
  var A, B;
  function setup(id){
    var cv=document.getElementById(id);
    var dpr=window.devicePixelRatio||1;
    var w=cv.clientWidth, h=cv.clientHeight;
    if(w<=0) w=600; if(h<=0) h=240;
    cv.width=w*dpr; cv.height=h*dpr;
    var ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
    return {cv:cv,ctx:ctx,w:w,h:h};
  }
  function resizeCanvases(){ A=setup('cvPdf'); B=setup('cvCdf'); }
  var PAD=28;
  function ax(ctx,w,h){
    ctx.strokeStyle='#cbd5e1'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(PAD,h-PAD); ctx.lineTo(w-PAD,h-PAD);
    ctx.lineTo(w-PAD,PAD-6); ctx.stroke();
  }
  function X(x,w){ return PAD + (x-lo)/(hi-lo)*(w-2*PAD); }
  function Y(v,maxv,h){ return h-PAD - v/(maxv||1)*(h-2*PAD); }

  function drawPdf(prog, shadeFromX){
    var ctx=A.ctx,w=A.w,h=A.h; ctx.clearRect(0,0,w,h); ax(ctx,w,h);
    // 抽样经验直方图：按绘图定义域分箱并转为密度，与理论 PDF 共用同一 y 尺度
    var hist=null;
    if(simHist && simHist.length){
      simOutOfRange=0;
      var hmin=lo, hmax=hi; if(hmax<=hmin) hmax=hmin+1;
      var nb=Math.min(40, Math.max(15, Math.floor(Math.sqrt(simHist.length))));
      var bw=(hmax-hmin)/nb, bins=[];
      for(var b=0;b<nb;b++) bins.push(0);
      for(var s=0;s<simHist.length;s++){
        var bi=Math.floor((simHist[s]-hmin)/bw);
        if(bi<0){ bi=0; }                          // 左界外：夹回最左 bin
        if(bi>=nb){ simOutOfRange++; continue; }   // 重尾超出绘图域：不计入密度直方图，避免最右柱被撑高
        bins[bi]++;
      }
      var dens=[], dmax=0;
      for(var b3=0;b3<nb;b3++){ var d=(bins[b3]/simHist.length)/bw; dens.push(d); if(d>dmax)dmax=d; }
      hist={hmin:hmin, bw:bw, nb:nb, dens:dens, dmax:dmax};
    }
    var maxv=Math.max.apply(null,data.pdf)||1;
    if(hist && hist.dmax>maxv) maxv=hist.dmax;
    // 画经验直方图（密度单位，与 PDF 同尺度叠加）
    if(hist){
      ctx.fillStyle='rgba(180,83,9,0.45)';
      for(var b2=0;b2<hist.nb;b2++){
        if(hist.dens[b2]<=0) continue;
        var bl=hist.hmin+b2*hist.bw, br=bl+hist.bw;
        var xpos=X(bl,w), xw=Math.max(1,(X(br,w)-X(bl,w))*0.92);
        var bh=hist.dens[b2]/maxv*(h-2*PAD);
        ctx.fillRect(xpos, (h-PAD)-bh, xw, bh);
      }
    }
    // 上侧 α 临界域阴影
    if(shadeFromX!=null && shadeFromX>lo && shadeFromX<hi){
      ctx.fillStyle='rgba(180,83,9,0.22)';
      ctx.beginPath();
      ctx.moveTo(X(shadeFromX,w), h-PAD);
      var firstI=N-1;
      for(var t=0;t<N;t++){ var xv=isD?ks[t]:xs[t]; if(xv>=shadeFromX){ firstI=t; break; } }
      for(var t2=firstI;t2<N;t2++){ ctx.lineTo(X(isD?ks[t2]:xs[t2],w), Y(data.pdf[t2],maxv,h)); }
      ctx.lineTo(X(isD?ks[N-1]:xs[N-1],w), h-PAD); ctx.closePath(); ctx.fill();
    }
    if(isD){
      var bwD=(w-2*PAD)/N*0.7;
      var upto=Math.max(1,Math.floor(prog*N));
      for(var i=0;i<upto;i++){
        var xpos=X(ks[i],w), yv=Y(data.pdf[i],maxv,h);
        ctx.fillStyle='rgba(37,99,235,0.78)';
        ctx.fillRect(xpos-bwD/2, yv, bwD, (h-PAD)-yv);
      }
      ctx.fillStyle='#475569'; ctx.font='11px sans-serif';
      for(var t=0;t<N;t+=Math.max(1,Math.floor(N/10))){ ctx.fillText(ks[t],X(ks[t],w)-6,h-PAD+14); }
    } else {
      ctx.beginPath();
      var n=Math.max(1,Math.floor(prog*N));
      for(var j=0;j<n;j++){
        var xx=X(xs[j],w), yy=Y(data.pdf[j],maxv,h);
        if(j===0) ctx.moveTo(xx,yy); else ctx.lineTo(xx,yy);
      }
      ctx.strokeStyle='#2563eb'; ctx.lineWidth=2.2; ctx.stroke();
      ctx.lineTo(X(xs[n-1],w),h-PAD); ctx.lineTo(X(xs[0],w),h-PAD); ctx.closePath();
      ctx.fillStyle='rgba(37,99,235,0.12)'; ctx.fill();
      ctx.fillStyle='#475569'; ctx.font='11px sans-serif';
      var step=Math.max(1,Math.floor(N/8));
      for(var s=0;s<N;s+=step){ ctx.fillText(xs[s].toFixed(1),X(xs[s],w)-10,h-PAD+14); }
    }
    // 交互查询点：点击/拖动画布定位 x，显示 P(X≤x)
    if(clickX!=null && clickX>=lo && clickX<=hi){
      var cx=X(clickX,w);
      ctx.strokeStyle='#0ea5a4'; ctx.lineWidth=1.5; ctx.setLineDash([4,3]);
      ctx.beginPath(); ctx.moveTo(cx, PAD-6); ctx.lineTo(cx, h-PAD); ctx.stroke();
      ctx.setLineDash([]);
      var yi=isD?Math.round(clickX-lo):Math.round((clickX-lo)/(hi-lo)*(N-1));
      if(yi<0)yi=0; if(yi>=N)yi=N-1;
      var py=Y(data.pdf[yi],maxv,h);
      ctx.fillStyle='#0ea5a4';
      ctx.beginPath(); ctx.arc(cx, py, 5, 0, 2*PI); ctx.fill();
      ctx.strokeStyle='#fff'; ctx.lineWidth=1.5; ctx.stroke();
      var prob=cdfAt(clickX);
      var lbl='x='+fmt(clickX)+'   P(X≤x)='+prob.toFixed(4);
      ctx.font='12px sans-serif';
      var tw=ctx.measureText(lbl).width+14;
      var lx=cx+10; if(lx+tw>w-PAD) lx=cx-tw-10;
      ctx.fillStyle='rgba(14,165,164,0.95)';
      ctx.fillRect(lx, PAD-2, tw, 20);
      ctx.fillStyle='#fff'; ctx.fillText(lbl, lx+7, PAD+12);
    }
  }

  function drawCdf(prog){
    var ctx=B.ctx,w=B.w,h=B.h; ctx.clearRect(0,0,w,h); ax(ctx,w,h);
    var n=Math.max(1,Math.floor(prog*N));
    ctx.beginPath(); ctx.moveTo(X(isD?ks[0]:xs[0],w),h-PAD);
    for(var i=0;i<n;i++){ var xx=X(isD?ks[i]:xs[i],w); var yy=Y(data.cdf[i],1,h); ctx.lineTo(xx,yy); }
    ctx.lineTo(X(isD?ks[n-1]:xs[n-1],w),h-PAD); ctx.closePath();
    ctx.fillStyle='rgba(14,165,164,0.14)'; ctx.fill();
    ctx.beginPath();
    for(var j=0;j<n;j++){
      var x2=X(isD?ks[j]:xs[j],w), y2=Y(data.cdf[j],1,h);
      if(j===0) ctx.moveTo(x2,y2); else ctx.lineTo(x2,y2);
    }
    ctx.strokeStyle='#0ea5a4'; ctx.lineWidth=2.2; ctx.stroke();
    ctx.fillStyle='#475569'; ctx.font='11px sans-serif';
    var st=Math.max(1,Math.floor(N/8));
    for(var s2=0;s2<N;s2+=st){ ctx.fillText((isD?ks[s2]:xs[s2]).toFixed(1),X(isD?ks[s2]:xs[s2],w)-10,h-PAD+14); }
    // 联动点：与 PDF 图同步，显示 (x, P(X≤x))
    if(clickX!=null && clickX>=lo && clickX<=hi){
      var cxd=X(clickX,w);
      var probd=cdfAt(clickX);
      var cyd=Y(probd,1,h);
      ctx.strokeStyle='#0ea5a4'; ctx.lineWidth=1.5; ctx.setLineDash([4,3]);
      ctx.beginPath(); ctx.moveTo(cxd, PAD-6); ctx.lineTo(cxd, h-PAD); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(PAD, cyd); ctx.lineTo(cxd, cyd); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle='#0ea5a4';
      ctx.beginPath(); ctx.arc(cxd, cyd, 5, 0, 2*PI); ctx.fill();
      ctx.strokeStyle='#fff'; ctx.lineWidth=1.5; ctx.stroke();
      var lbld='('+fmt(clickX)+', '+probd.toFixed(4)+')';
      ctx.font='12px sans-serif';
      var twd=ctx.measureText(lbld).width+14;
      var lxd=cxd+10; if(lxd+twd>w-PAD) lxd=cxd-twd-10;
      ctx.fillStyle='rgba(14,165,164,0.95)'; ctx.fillRect(lxd, PAD-2, twd, 20);
      ctx.fillStyle='#fff'; ctx.fillText(lbld, lxd+7, PAD+12);
    }
  }

  // ---------- 插值：x -> P(X<=x) / p -> x_p ----------
  function cdfAt(x){
    if(isD){
      if(x<ks[0]) return 0; if(x>=ks[N-1]) return 1;
      var idx=0; for(var i=0;i<N;i++){ if(ks[i]<=x) idx=i; else break; }
      return data.cdf[idx];
    } else {
      if(x<=lo) return 0; if(x>=hi) return 1;
      var t=(x-lo)/(hi-lo)*(N-1); var i=Math.floor(t); var f=t-i;
      if(i>=N-1) return data.cdf[N-1];
      if(i<0) return data.cdf[0];
      return data.cdf[i]*(1-f)+data.cdf[i+1]*f;
    }
  }
  function quantile(pq){
    if(pq<=0) return isD?ks[0]:lo;
    if(pq>=1) return isD?ks[N-1]:hi;
    for(var i=0;i<N-1;i++){
      var a=data.cdf[i], b=data.cdf[i+1];
      if(a<=pq && b>=pq){
        var span=b-a; var frac= span>0 ? (pq-a)/span : 0;
        return isD ? ks[i+1] : (xs[i]+frac*(xs[i+1]-xs[i]));
      }
    }
    return isD?ks[N-1]:hi;
  }

  // ---------- 抽样模拟（χ² / t / F）----------
  function randn(){ var u1=Math.random()||1e-9, u2=Math.random(); return Math.sqrt(-2*Math.log(u1))*Math.cos(2*PI*u2); }
  function sumSq(m){ var s=0; for(var i=0;i<m;i++){ var z=randn(); s+=z*z; } return s; }
  function sampleOnce(){
    var t=CONFIG.dist_type;
    if(t==='chi_square'){ return sumSq(Math.round(p.k)); }
    if(t==='student_t'){ return randn()/Math.sqrt(sumSq(Math.round(p.nu))/p.nu); }
    if(t==='f'){ return (sumSq(Math.round(p.d1))/p.d1)/(sumSq(Math.round(p.d2))/p.d2); }
    return null;
  }

  // ---------- 入场动画 ----------
  var animId=null;
  function runIntro(){
    var t0=null, dur=1100;
    function step(ts){
      if(t0===null)t0=ts; var prog=Math.min((ts-t0)/dur,1);
      drawPdf(prog, currentShade); drawCdf(prog);
      if(prog<1) animId=requestAnimationFrame(step);
    }
    animId=requestAnimationFrame(step);
  }

  // ---------- 公式 / 知识点（KaTeX 渲染，离线回退纯文本） ----------
  function hasCJK(s){ return /[一-鿿]/.test(s||''); }
  function renderTex(el, tex, plain, displayMode){
    var useTex = tex && !hasCJK(tex) && window.katex && !window.__katexFailed;
    if(useTex){
      try{ window.katex.render(tex, el, {throwOnError:false, displayMode: !!displayMode}); return; }
      catch(e){ /* 渲染失败则回退 */ }
    }
    el.textContent = ((tex && !hasCJK(tex)) ? tex : plain) || plain || '';
  }
  function renderAllTex(){
    if(window.__katexFailed || !window.katex){
      var kn=document.createElement('div'); kn.className='hint';
      kn.textContent='⚠ KaTeX 加载失败（可能离线），已显示纯文本公式。';
      var fb=document.querySelector('.formula-block');
      if(fb) fb.insertBefore(kn, fb.firstChild);
    }
    document.getElementById('pdfLabel').textContent = CONFIG.pdf_label;
    renderTex(document.getElementById('pdfTex'), CONFIG.pdf_latex, CONFIG.pdf_plain, true);
    document.getElementById('cdfLabel').textContent = CONFIG.cdf_label;
    if(CONFIG.cdf_latex){
      renderTex(document.getElementById('cdfTex'), CONFIG.cdf_latex, CONFIG.cdf_plain, true);
      document.getElementById('cdfNote').textContent='';
    } else {
      document.getElementById('cdfTex').textContent='';
      document.getElementById('cdfNote').textContent = CONFIG.cdf_note || '';
    }
    var nodes=document.querySelectorAll('#knowBody .tex');
    for(var i=0;i<nodes.length;i++){
      var el=nodes[i];
      renderTex(el, el.getAttribute('data-latex'), el.getAttribute('data-plain'), false);
    }
    if(CONFIG.construction){
      var sc=document.getElementById('simCard'); if(sc) sc.style.display='';
      renderTex(document.getElementById('conTex'), CONFIG.construction.latex, CONFIG.construction.text, true);
    }
  }

  // ---------- 知识点面板（DOM 构建，避免转义问题） ----------
  var kb=document.getElementById('knowBody');
  if(CONFIG.knowledge){
    var tbl=document.createElement('table');
    CONFIG.knowledge.forEach(function(r){
      var tr=document.createElement('tr');
      var td1=document.createElement('td'); td1.className='k'; td1.textContent=r[0];
      var td2=document.createElement('td');
      var sp=document.createElement('span'); sp.className='tex';
      sp.setAttribute('data-latex', r[2]||'');
      sp.setAttribute('data-plain', r[1]||'');
      td2.appendChild(sp); tr.appendChild(td1); tr.appendChild(td2); tbl.appendChild(tr);
    });
    kb.innerHTML=''; kb.appendChild(tbl);
  } else {
    kb.innerHTML='<div class="hint">自定义公式分布：本可视化仅绘制函数曲线。知识点请结合 IMA 知识库或本地知识库（references/distributions_knowledge.md）核对。</div>';
  }

  // ---------- 滑块 + 数字输入（双向绑定） ----------
  var specs=CONFIG.param_specs;
  var slBox=document.getElementById('sliders');
  var inputs={}, nums={};
  function fmt(v){ return (Math.round(v*1000)/1000).toString(); }
  function redrawAll(){
    data=compute(); drawPdf(1, currentShade); drawCdf(1); updateStatus(); updateQuery();
  }
  specs.forEach(function(sp){
    var row=document.createElement('div'); row.className='row';
    var lab=document.createElement('label'); lab.textContent=sp.label;
    var inp=document.createElement('input'); inp.type='range';
    inp.min=sp.min; inp.max=sp.max; inp.step=sp.step; inp.value=sp.value;
    var num=document.createElement('input'); num.type='number'; num.className='val';
    num.step=sp.step; num.value=sp.value;
    inp.addEventListener('input',function(){
      var v=parseFloat(inp.value);
      p[sp.name]=v; num.value=v;
      redrawAll();
    });
    num.addEventListener('input',function(){
      var v=parseFloat(num.value); if(isNaN(v)) return;
      // χ²/t/F 的自由度为正整数：键入非整数时对齐抽样所用的取整值，保证直方图与曲线一致
      if((CONFIG.dist_type==='chi_square'&&sp.name==='k')||
         (CONFIG.dist_type==='student_t'&&sp.name==='nu')||
         (CONFIG.dist_type==='f'&&(sp.name==='d1'||sp.name==='d2'))){
        v=Math.round(v);
      }
      p[sp.name]=v;
      inp.value=Math.min(Math.max(v, sp.min), sp.max);
      redrawAll();
    });
    row.appendChild(lab); row.appendChild(inp); row.appendChild(num);
    slBox.appendChild(row); inputs[sp.name]=inp; nums[sp.name]=num;
  });

  document.getElementById('reset').addEventListener('click',function(){
    p=JSON.parse(JSON.stringify(baseP));
    specs.forEach(function(sp){
      p[sp.name]=baseP[sp.name];
      if(inputs[sp.name]) inputs[sp.name].value=baseP[sp.name];
      if(nums[sp.name]) nums[sp.name].value=baseP[sp.name];
    });
    simHist=null; clickX=null; currentShade=null;
    redrawAll();
    document.getElementById('status').textContent='已重置为初始参数';
    setTimeout(updateStatus, 1200);
  });

  // ---------- 状态：退化告警 / formula 归一化提示 ----------
  function updateStatus(){
    var st=document.getElementById('status');
    if(data.degenerate){
      st.innerHTML='<span style="color:#b91c1c;font-weight:600">⚠ 当前参数下分布退化（密度全为 0，如均匀分布需 a &lt; b），请调整参数。</span>';
      return;
    }
    if(CONFIG.mode==='formula'){
      st.innerHTML='<span style="color:var(--warn)">⚠ 自定义公式未归一化：定义域上积分 ≈ '+data.area.toFixed(4)+'（CDF 已按面积归一化，仅作函数曲线演示，非合法密度）。</span>';
      return;
    }
    st.textContent='';
  }

  // ---------- 查询面板 ----------
  var qx=document.getElementById('qx'), qp=document.getElementById('qp'), qa=document.getElementById('qa');
  var qxO=document.getElementById('qxOut'), qpO=document.getElementById('qpOut'), qaO=document.getElementById('qaOut');
  // ---------- 三方联动：x / p / α 描述同一个点，clickX 为唯一状态源 ----------
  function syncFromPoint(src){
    if(clickX!=null && clickX>=lo && clickX<=hi){
      var prob=cdfAt(clickX), alpha=1-prob;
      if(src!=='x') qx.value=fmt(clickX);
      if(src!=='p') qp.value=fmt(prob);
      if(src!=='a') qa.value=fmt(alpha);
      qxO.textContent='P(X≤'+fmt(clickX)+') = '+prob.toFixed(4);
      qpO.textContent='分位数 x_'+fmt(prob)+' = '+fmt(clickX);
      qaO.textContent='上侧 α='+alpha.toFixed(4)+' → 临界 x='+fmt(clickX);
      currentShade=clickX;
    } else {
      clickX=null;
      if(src!=='x') qx.value='';
      if(src!=='p') qp.value='';
      if(src!=='a') qa.value='';
      qxO.textContent='P(X≤x) = —';
      qpO.textContent='分位数 x_p = —';
      qaO.textContent='上侧 α → 临界 x = —';
      currentShade=null;
    }
    drawPdf(1, currentShade); drawCdf(1);
  }
  function onInput(src){
    var v;
    if(src==='x'){ v=parseFloat(qx.value); clickX=(!isNaN(v)&&v>=lo&&v<=hi)?v:null; }
    else if(src==='p'){ v=parseFloat(qp.value); clickX=(!isNaN(v)&&v>0&&v<1)?quantile(v):null; }
    else if(src==='a'){ v=parseFloat(qa.value); clickX=(!isNaN(v)&&v>0&&v<1)?quantile(1-v):null; }
    syncFromPoint(src);
  }
  qx.addEventListener('input', function(){onInput('x');});
  qp.addEventListener('input', function(){onInput('p');});
  qa.addEventListener('input', function(){onInput('a');});

  // 画布交互：PDF 点击/拖动按 x 定位，CDF 点击/拖动按 p 定位；双击清除
  var cvPdf=document.getElementById('cvPdf'), cvCdf=document.getElementById('cvCdf');
  var dragging=false, dragTarget=null;
  cvPdf.style.cursor='crosshair'; cvCdf.style.cursor='crosshair';
  function xFromPdfEvent(ev){
    var rect=cvPdf.getBoundingClientRect();
    var px=ev.clientX-rect.left;
    return Math.max(lo, Math.min(hi, lo+(px-PAD)/(A.w-2*PAD)*(hi-lo)));
  }
  function pFromCdfEvent(ev){
    var rect=cvCdf.getBoundingClientRect();
    var py=ev.clientY-rect.top;
    return Math.max(0.0001, Math.min(0.9999, (B.h-PAD-py)/(B.h-2*PAD)));
  }
  function pdfDown(ev){ dragging=true; dragTarget='pdf'; clickX=xFromPdfEvent(ev); syncFromPoint(null); ev.preventDefault(); }
  function cdfDown(ev){ dragging=true; dragTarget='cdf'; clickX=quantile(pFromCdfEvent(ev)); syncFromPoint(null); ev.preventDefault(); }
  function moveHandler(ev){
    if(!dragging) return;
    if(dragTarget==='pdf'){ clickX=xFromPdfEvent(ev); }
    else { clickX=quantile(pFromCdfEvent(ev)); }
    syncFromPoint(null);
  }
  cvPdf.addEventListener('mousedown', pdfDown);
  cvCdf.addEventListener('mousedown', cdfDown);
  window.addEventListener('mousemove', moveHandler);
  window.addEventListener('mouseup', function(){ dragging=false; dragTarget=null; });
  cvPdf.addEventListener('dblclick', function(){ clickX=null; syncFromPoint(null); });
  cvCdf.addEventListener('dblclick', function(){ clickX=null; syncFromPoint(null); });
  cvPdf.addEventListener('touchstart', function(ev){ var t=ev.touches[0]; pdfDown({clientX:t.clientX,clientY:t.clientY,preventDefault:function(){ev.preventDefault();}}); }, {passive:false});
  cvCdf.addEventListener('touchstart', function(ev){ var t=ev.touches[0]; cdfDown({clientX:t.clientX,clientY:t.clientY,preventDefault:function(){ev.preventDefault();}}); }, {passive:false});
  window.addEventListener('touchmove', function(ev){ if(!dragging) return; var t=ev.touches[0]; moveHandler({clientX:t.clientX,clientY:t.clientY}); ev.preventDefault(); }, {passive:false});
  window.addEventListener('touchend', function(){ dragging=false; dragTarget=null; });

  // ---------- 抽样模拟按钮 ----------
  var simBtn=document.getElementById('simBtn'), simClear=document.getElementById('simClear'), simN=document.getElementById('simN'), simNote=document.getElementById('simNote');
  if(CONFIG.dist_type==='chi_square'||CONFIG.dist_type==='student_t'||CONFIG.dist_type==='f'){
    simBtn.addEventListener('click', function(){
      var n=parseInt(simN.value,10)||3000; if(n<100)n=100; if(n>50000)n=50000;
      var arr=[]; for(var i=0;i<n;i++){ var s=sampleOnce(); if(s!==null && isFinite(s)) arr.push(s); }
      simHist=arr; drawPdf(1, currentShade);
      var pct = arr.length ? (simOutOfRange/arr.length*100) : 0;
      var tail = pct>0.5 ? ' ⚠ 约 '+pct.toFixed(1)+'% 样本落在绘图域之外（重尾，长尾未显示，属正常现象）。' : '';
      simNote.textContent='已生成 '+arr.length+' 个样本（Box-Muller 构造），经验直方图叠加在理论 PDF 上。'+tail;
    });
    simClear.addEventListener('click', function(){ simHist=null; drawPdf(1, currentShade); simNote.textContent='已清除直方图。'; });
  }

  // ---------- resize 重绘 ----------
  var rt=null;
  window.addEventListener('resize', function(){
    clearTimeout(rt); rt=setTimeout(function(){ resizeCanvases(); drawPdf(1,currentShade); drawCdf(1); }, 150);
  });

  // ---------- 启动 ----------
  resizeCanvases();
  if(document.readyState==='loading'){
    window.addEventListener('DOMContentLoaded', function(){ renderAllTex(); runIntro(); });
  } else {
    renderAllTex(); runIntro();
  }
  updateStatus(); syncFromPoint(null);
})();
</script>
</body>
</html>
"""


def _rhs_to_latex(rhs):
    """把用户原始公式右侧转换为可给 KaTeX 渲染的 LaTeX（尽力而为）。"""
    if not rhs:
        return ""
    s = rhs
    for g, l in [("λ", r"\lambda "), ("μ", r"\mu "), ("σ", r"\sigma "),
                 ("α", r"\alpha "), ("β", r"\beta "), ("ν", r"\nu "),
                 ("θ", r"\theta "), ("π", r"\pi ")]:
        s = s.replace(g, l)
    s = re.sub(r"exp\s*\(", r"\\exp(", s)
    for a, b in [("sin(", r"\sin("), ("cos(", r"\cos("), ("tan(", r"\tan("),
                 ("ln(", r"\ln("), ("log(", r"\log("), ("sqrt(", r"\sqrt(")]:
        s = s.replace(a, b)
    s = s.replace("*", r"\cdot ")
    return s.strip()


def build_config(desc):
    mode = desc["mode"]
    is_discrete = desc["is_discrete"]
    domain = desc["domain"]
    params = desc["params"]
    if mode == "catalog":
        e = dc.CATALOG[desc["distribution_type"]]
        latex = dc.LATEX.get(desc["distribution_type"], {})
        display = e["display_name"]
        knowledge = [
            ["均值 E(X)", e["mean"], latex.get("mean", "")],
            ["方差 Var(X)", e["variance"], latex.get("variance", "")],
            ["特征函数 φ(t)", e["char_func"], latex.get("char_func", "")],
            ["矩母函数 M(t)", e["mgf"], latex.get("mgf", "")],
            ["典型应用", "、".join(e["applications"]), ""],
        ]
        if "construction" in e:
            knowledge.append(["构造来源", e["construction"]["text"], e["construction"]["latex"]])
        morph = e["morph_param"]
        specs = []
        for name, spec in e["params"].items():
            val = float(params.get(name, spec["default"]))
            mn, mx, step = spec["min"], spec["max"], spec["step"]
            pad = ((mx - mn) * 0.2) if (mx - mn) > 0 else 0.5
            if val < mn:
                mn = val - pad
            if val > mx:
                mx = val + pad
            specs.append({
                "name": name, "label": spec["label"],
                "min": round(mn, 3), "max": round(mx, 3), "step": step,
                "value": val,
            })
        pdf_label = "概率质量函数 P(X=k)" if is_discrete else "概率密度函数 f(x)"
        extra = {
            "pdf_label": pdf_label,
            "pdf_latex": latex.get("pdf", ""),
            "pdf_plain": e["formula"],
            "cdf_label": "分布函数 F(x)",
            "cdf_latex": latex.get("cdf", ""),
            "cdf_plain": "",
            "cdf_note": "",
        }
    else:
        display = desc.get("display_name", "自定义公式分布")
        knowledge = None
        morph = next(iter(params), None)
        specs = []
        for name, val in params.items():
            v = float(val)
            vmin = v * 0.3 if v > 0 else 0.1
            vmax = v * 3.0 if v > 0 else 3.0
            if vmax <= vmin:
                vmax = vmin + 3.0
            specs.append({
                "name": name, "label": name,
                "min": round(vmin, 3), "max": round(vmax, 3),
                "step": round((vmax - vmin) / 60, 4), "value": v,
            })
        disp = desc.get("display_formula", "") or desc.get("raw_formula", "")
        extra = {
            "pdf_label": "函数 f(x)",
            "pdf_latex": _rhs_to_latex(disp),
            "pdf_plain": disp,
            "cdf_label": "分布函数 F(x)",
            "cdf_latex": "",
            "cdf_plain": "",
            "cdf_note": "（分布函数 F(x) 由密度数值积分得到）",
        }
    cfg = {
        "is_discrete": is_discrete,
        "domain": [float(domain[0]), float(domain[1])],
        "params": {k: float(v) for k, v in params.items()},
        "display_name": display,
        "knowledge": knowledge,
        "morph_param": morph,
        "param_specs": specs,
    }
    cfg.update(extra)
    cfg["dist_type"] = desc["distribution_type"]
    cfg["mode"] = mode
    cfg["construction"] = dc.CATALOG[desc["distribution_type"]].get("construction") if (mode == "catalog") else None
    return cfg


def build_html(desc):
    cfg = build_config(desc)
    if desc["mode"] == "catalog":
        pdf_js = dc.CATALOG[desc["distribution_type"]]["pdf_js"]
        title = desc["display_name"]
        mode_label = "内置分布"
    else:
        pdf_js = "function(x,p){ var lam=p.lam, mu=p.mu, sigma=p.sigma, alpha=p.alpha, beta=p.beta, " \
                 "k=p.k, p_p=p.p, n=p.n, a=p.a, b=p.b, theta=p.theta, nu=p.nu, r=p.r, d1=p.d1, d2=p.d2; " \
                 "return (" + desc["raw_formula"] + "); }"
        title = "自定义公式分布"
        mode_label = "自定义公式"
    html = (HTML_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__MODE__", mode_label)
            .replace("/*__HELPERS__*/", dc.JS_HELPERS)
            .replace("/*__CONFIG__*/", json.dumps(cfg, ensure_ascii=False))
            .replace("/*__PDF__*/", pdf_js))
    return html


def main():
    ap = argparse.ArgumentParser(description="生成概率分布交互式 HTML 动画")
    ap.add_argument("desc", nargs="?", help="标准分布描述 JSON 文件路径或 JSON 字符串；省略则从 stdin 读取")
    ap.add_argument("--out", help="输出 HTML 路径（默认 ./<type>_viz.html）")
    args = ap.parse_args()

    raw = args.desc
    if raw is None:
        raw = sys.stdin.read()
    if raw.strip().startswith("{") or raw.strip().startswith("["):
        desc = json.loads(raw)
    else:
        with open(raw, "r", encoding="utf-8") as f:
            desc = json.load(f)

    html = build_html(desc)
    out = args.out
    if not out:
        base = desc.get("distribution_type", "custom")
        out = base + "_viz.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[ok] 已生成可视化：{out}  (mode={desc['mode']})", file=sys.stderr)


if __name__ == "__main__":
    main()
