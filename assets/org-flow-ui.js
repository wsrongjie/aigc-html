/* 创作链路共用素材引用。每次实际生成重新检查权限，保留失权草稿以便替换。 */
(function(){
    const A=OrgAccess,e=A.esc,page=decodeURIComponent(location.pathname).split('/').pop();
    const CONTEXT='xingzao_creation_context_v1';
    const getJSON=(key,storage=sessionStorage)=>{try{return JSON.parse(storage.getItem(key)||'null');}catch(err){return null;}};
    function check(refs){const errors=A.validateRefs(refs);if(!refs||!refs.some(r=>r.type==='role')||!refs.some(r=>r.type==='scene'))errors.push('请选择人物角色和场景');if(errors.length){alert(errors.join('\n'));return false;}return true;}
    function context(){const c=getJSON(CONTEXT);return c&&c.creatorId===A.user()?.id?c:null;}
    function remember(refs){const u=A.user();const c={creatorId:u.id,orgId:u.orgId,refs};sessionStorage.setItem(CONTEXT,JSON.stringify(c));return c;}
    function wrap(name,checkFn,after){const fn=window[name];if(typeof fn!=='function')return;window[name]=function(){if(checkFn&&!checkFn.apply(this,arguments))return;const result=fn.apply(this,arguments);if(after)after.apply(this,arguments);return result;};}
    function record(refs,title,visibility){
        if(!check(refs))return null;
        return A.create('video',{id:Date.now(),name:title||'组织协作成片',title:title||'组织协作成片',refs,visibility:visibility||'private',desc:'组织权限联动 · 模拟生成结果',status:'completed',duration:'00:15'});
    }
    window.OrgFlow={check,context,remember,record};
    let selectedRefs=context()?.refs||[];
    function selectionPanel(){
        const host=document.querySelector('.content-area,.page-wrap,.main-content,.content,main')||document.body;
        const box=document.createElement('section');box.className='oa-note';box.id='oa-flow-materials';
        box.innerHTML='<strong>本次生成素材</strong><div class="oa-toolbar">'+['role','voice','scene'].map(t=>'<label>'+A.types[t]+' <select class="oa-field" aria-label="本次生成'+A.types[t]+'" data-oa-type="'+t+'"></select></label>').join('')+'</div><span>素材按当前成员权限加载。复刻同款仍需分别获得原素材使用权。</span><div class="oa-error" id="oa-flow-errors"></div>';
        host.prepend(box);
        function refresh(){
            A.fresh();box.querySelectorAll('select').forEach(select=>{const t=select.dataset.oaType,old=selectedRefs.find(r=>r.type===t)?.id||select.value;const available=A.list(t).filter(a=>A.can(a,'use'));select.innerHTML='<option value="">请选择'+A.types[t]+'</option>'+available.map(a=>'<option value="'+e(a.id)+'">'+e(a.name+' · '+(a.system?'平台内置':A.orgName(a.orgId)))+'</option>').join('');if(available.some(a=>a.id===old))select.value=old;else if(old){const lost=new Option('原素材已失权，请替换',old);lost.disabled=true;select.add(lost);select.value=old;}});
            box.querySelector('#oa-flow-errors').textContent=selectedRefs.length?A.validateRefs(selectedRefs).join('；'):'';
        }
        box.onchange=ev=>{
            if(ev.target.dataset.oaType==='role'){
                const role=A.lookup('role',ev.target.value),voiceSelect=box.querySelector('[data-oa-type="voice"]');
                if(role?.voiceId&&A.can(A.lookup('voice',role.voiceId),'use'))voiceSelect.value=role.voiceId;
            }
            selectedRefs=Array.from(box.querySelectorAll('select')).filter(s=>s.value).map(s=>({type:s.dataset.oaType,id:s.value}));
            remember(selectedRefs);box.querySelector('#oa-flow-errors').textContent=A.validateRefs(selectedRefs).join('；');
        };
        refresh();window.addEventListener('org-access-change',refresh);return box;
    }
    if(page==='简单模式-流程版.html'||page==='简单模式-流程版-模板版.html'){
        // 固定示例素材是平台内置，用户资产则使用稳定 ID，不依赖名称识别。
        avList.forEach(a=>A.register('role',{id:'builtin-role-'+a.key,name:a.name+' · '+a.key,system:true,visibility:'team',tag:a.tag}));
        Object.keys(bgM).forEach(name=>A.register('scene',{id:'builtin-scene-'+name,name,system:true,visibility:'team',gradient:bgM[name]}));
        const voiceBar=document.createElement('div');voiceBar.className='oa-toolbar';voiceBar.innerHTML='<label>本次使用音色 <select class="oa-field" id="oa-flow-voice" aria-label="本次使用音色"></select></label><span id="oa-fast-warning"></span>';
        document.getElementById('avatar-grid').before(voiceBar);
        function roles(){return A.list('role').filter(a=>A.can(a,'use'));}
        function scenes(){return A.list('scene').filter(a=>A.can(a,'use'));}
        function renderVoices(){const select=document.getElementById('oa-flow-voice');const old=S.oaVoiceId||'';select.innerHTML='<option value="">跟随角色音色</option>'+A.list('voice').filter(a=>A.can(a,'use')).map(a=>'<option value="'+e(a.id)+'">'+e(a.name+' · '+(a.system?'平台内置':A.orgName(a.orgId)))+'</option>').join('');if(old){if(!Array.from(select.options).some(o=>o.value===old)){const lost=new Option('原音色已失权，请替换',old);lost.disabled=true;select.add(lost);}select.value=old;}}
        document.getElementById('oa-flow-voice').onchange=ev=>{S.oaVoiceId=ev.target.value;saveDraft();};
        window.getAvatarMeta=key=>{const a=A.lookup('role',key);return a?{key:a.id,name:a.name,tag:a.system?'平台内置':A.orgName(a.orgId)}:{key,name:'原角色不可用',tag:'请替换'};};
        window.renderAvatarList=function(keyword){
            const grid=document.getElementById('avatar-grid');grid.innerHTML='';const list=roles().filter(a=>!keyword||a.name.includes(keyword));
            list.forEach(a=>{const b=document.createElement('div');b.className='av-item-compact'+(S.avatar===a.id?' sel':'');b.tabIndex=0;b.setAttribute('role','button');b.innerHTML='<div class="av-cb-compact">✓</div><div class="av-face-compact">👤</div><div class="av-nm-compact">'+e(a.name)+'</div><div class="av-tg-compact">'+e(a.system?'平台内置':A.orgName(a.orgId))+'</div>';b.onclick=()=>selAvatar(a.id);b.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();b.click();}};grid.appendChild(b);});if(!list.length)grid.innerHTML='<div class="oa-empty">暂无有权使用的角色</div>';
        };
        const oldSelAvatar=selAvatar;window.selAvatar=function(key){if(!A.requireAsset('role',key,'use'))return;oldSelAvatar(key);const a=A.lookup('role',key);S.oaVoiceId=a?.voiceId||'';renderVoices();saveDraft();};
        window.renderBgList=function(keyword){const grid=document.getElementById('bg-grid-preset');if(!grid)return;grid.innerHTML='';scenes().filter(a=>!keyword||a.name.includes(keyword)).forEach(a=>{bgM[a.id]=a.gradient||'linear-gradient(135deg,#45658a,#94abc6)';const b=document.createElement('div');b.className='bg-card-compact'+(S.bgMulti.includes(a.id)?' sel':'');b.tabIndex=0;b.setAttribute('role','button');b.innerHTML='<div class="bg-cb-compact">✓</div><div class="bg-thumb-compact" style="background:'+e(bgM[a.id])+'"></div><div class="bg-lb-compact">'+e(a.name)+'</div><span class="oa-badge">'+e(a.system?'平台内置':A.orgName(a.orgId))+'</span>';b.onclick=()=>selBg(a.id);b.onkeydown=ev=>{if(ev.key==='Enter'){b.click();}};grid.appendChild(b);});};
        wrap('selBg',key=>A.requireAsset('scene',key,'use'));
        function refs(){const r=[];if(S.avatar)r.push({type:'role',id:S.avatar});const role=A.lookup('role',S.avatar);if(S.oaVoiceId||role?.voiceId)r.push({type:'voice',id:S.oaVoiceId||role.voiceId});S.bgMulti.forEach(id=>r.push({type:'scene',id}));return r;}
        function valid(){const r=refs();if(!check(r))return false;remember(r);return true;}
        const preset=getJSON('oa-creation-preset');
        if(preset){
            if(preset.sourceVideoId&&!A.requireAsset('video',preset.sourceVideoId,'replicate'))sessionStorage.removeItem('oa-creation-preset');
            else {const pr=preset.refs||[];S.avatar=pr.find(r=>r.type==='role')?.id||S.avatar;S.bgMulti=pr.filter(r=>r.type==='scene').map(r=>r.id);S.oaVoiceId=preset.voiceId||pr.find(r=>r.type==='voice')?.id||'';const src=A.lookup('video',preset.sourceVideoId);if(src){S.taskName='复刻 · '+src.name;document.getElementById('task-name-input').value=S.taskName;if(S.cards[0])S.cards[0].content=src.script||'各位投资者朋友大家好，今天为大家带来市场观察。';}sessionStorage.removeItem('oa-creation-preset');}
        }
        if(S.avatar&&!A.lookup('role',S.avatar))S.avatar='builtin-role-'+S.avatar;
        S.bgMulti=S.bgMulti.map(id=>A.lookup('scene',id)?id:'builtin-scene-'+id);
        const d=getJSON('aigc_draft_task',localStorage);if(d?.oaVoiceId&&!preset)S.oaVoiceId=d.oaVoiceId;
        wrap('saveDraft',null,()=>{const d=getJSON('aigc_draft_task',localStorage);if(d){d.creatorId=A.user()?.id;d.orgId=A.user()?.orgId;d.refs=refs();d.oaVoiceId=S.oaVoiceId||'';localStorage.setItem('aigc_draft_task',JSON.stringify(d));}});
        ['resynthOne','resynthAll','regenFrame','regenAllFrames','confirmGen','startGeneration'].forEach(name=>wrap(name,valid,name==='confirmGen'?()=>{
            const data=getJSON('newTaskFromFlow',localStorage);if(!data)return;const u=A.user();Object.assign(data,{creatorId:u.id,orgId:u.orgId,visibility:S.visibility,refs:refs()});data.rows.forEach(row=>Object.assign(row,{creatorId:u.id,orgId:u.orgId,visibility:S.visibility,refs:refs()}));localStorage.setItem('newTaskFromFlow',JSON.stringify(data));record(refs(),getTaskName(),S.visibility);
        }:null));
        renderAvatarList('');renderBgList('');renderVoices();if(typeof renderCards==='function')renderCards();if(typeof updateSidebar==='function')updateSidebar();
        function warn(){A.fresh();document.getElementById('oa-fast-warning').textContent=refs().length?A.validateRefs(refs()).join('；'):'';renderAvatarList('');renderBgList('');renderVoices();}
        window.addEventListener('org-access-change',warn);warn();
        window.OrgFlow.currentRefs=refs;
        return;
    }
    const creationPages=['index.html','step2-主体管理首页（一级主体联动版）.html','step3-常规分镜管理.html','step3-通灵xz模型.html','step4-成片合成.html','画布工作流.html'];
    if(creationPages.includes(page)){
        const incoming=page==='画布工作流.html'?getJSON('sameStyleIncomingTask',localStorage):null;
        if(incoming?.refs)selectedRefs=incoming.refs;
        const box=selectionPanel();
        function valid(){selectedRefs=Array.from(box.querySelectorAll('select')).filter(s=>s.value).map(s=>({type:s.dataset.oaType,id:s.value}));if(!check(selectedRefs))return false;remember(selectedRefs);return true;}
        if(page==='index.html'){
            // 同款弹窗也使用组织目录，防止模板内置的角色选择覆盖已选素材。
            wrap('openSameModal',null,()=>{const modal=document.getElementById('sameRole')?.closest('.modal,.modal-panel,.same-modal');if(modal&&!modal.contains(box))modal.prepend(box);});
            wrap('confirmSameTemplate',valid,()=>record(selectedRefs,'同款 · 组织协作视频','private'));
            wrap('previewSameVoice',()=>{const id=box.querySelector('[data-oa-type="voice"]').value;return id&&A.requireAsset('voice',id,'view');});
        }
        ['startCompositeGeneration','generateAudio','batchGenerateAudio','confirmAudioResynth','generateVideo','batchGenerateVideo','startFilmCompose','confirmGenerate','startComposing'].forEach(name=>wrap(name,valid));
        if(page==='step2-主体管理首页（一级主体联动版）.html')document.getElementById('nextBtn')?.addEventListener('click',ev=>{if(!valid()){ev.stopImmediatePropagation();ev.preventDefault();}},true);
        if(page==='画布工作流.html')wrap('generateVideo',null,()=>record(selectedRefs,'复刻同款 · 组织协作成片','private'));
        if(page==='step4-成片合成.html')wrap('startComposing',null,()=>{const a=record(selectedRefs,'导演台 · 组织协作成片','private');if(a)sessionStorage.setItem('oa-last-result',a.id);});
        wrap('startExport',()=>{const id=sessionStorage.getItem('oa-last-result');return id&&A.requireAsset('video',id,'download');});
    }
})();
