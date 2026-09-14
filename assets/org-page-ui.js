/* 各资产页面适配；同一权限判断同时用于列表、详情与操作处理器。 */
(function(){
    const A=OrgAccess,e=A.esc,page=decodeURIComponent(location.pathname).split('/').pop();
    function toolbar(target,refresh){
        const bar=document.createElement('div');bar.className='oa-toolbar';bar.innerHTML='<label>资产范围 <select aria-label="资产范围"><option value="all">全部可访问</option><option value="mine">我的资产</option><option value="local">本部门共享</option><option value="other">其他部门共享</option></select></label><span>当前部门：'+e(A.orgName(A.user()?.orgId))+'</span>';
        target.before(bar);bar.querySelector('select').onchange=ev=>{window.oaAssetFilter=ev.target.value;refresh();};
    }
    function wrap(name,check,after){const fn=window[name];if(typeof fn!=='function')return;window[name]=function(){if(check&&!check.apply(this,arguments))return;const result=fn.apply(this,arguments);if(after)after.apply(this,arguments);return result;};}
    function voiceOptions(select){
        if(!select)return;const old=select.value;
        Array.from(select.options).filter(o=>o.value&&!o.dataset.voiceId).forEach(o=>{
            const known=A.list('voice').find(a=>a.name===o.value);
            const builtin=['经典解说男-青年 / 中文','专业女主播 / 中文','经典解说男-青年','专业女主播','知性女声','沉稳男声'];
            if(known){o.dataset.voiceId=known.id;}
            else if(builtin.includes(o.value)){const a=A.register('voice',{id:'builtin-voice-'+o.value,name:o.textContent,system:true,visibility:'team'});o.dataset.voiceId=a.id;}
            else{o.disabled=true;o.textContent+='（来源待确认，请替换）';}
        });
        A.list('voice').filter(a=>!a.system&&A.can(a,'use')).forEach(a=>{if(Array.from(select.options).some(o=>o.dataset.voiceId===a.id))return;const option=new Option(a.name+' · '+A.orgName(a.orgId),a.name);option.dataset.voiceId=a.id;select.add(option);});
        Array.from(select.options).forEach(o=>{if(o.dataset.voiceId&&!A.can(A.lookup('voice',o.dataset.voiceId),'use'))o.remove();});
        if(Array.from(select.options).some(o=>o.value===old))select.value=old;
        const newId=new URLSearchParams(location.search).get('newVoiceId');if(newId){const option=Array.from(select.options).find(o=>o.dataset.voiceId===newId);if(option)select.value=option.value;}
    }
    document.querySelectorAll('#visibilitySelect,#visibility,#task-visibility').forEach(select=>{
        const note=document.createElement('div');note.className='oa-badge';note.textContent='归属：'+A.orgName(A.user()?.orgId)+'。个人仅创建者可见；本部门对本部门及获授权部门开放。';select.after(note);
    });
    if(page==='主体管理-首页.html'){
        toolbar(document.getElementById('assetGrid'),render);
        window.addEventListener('org-access-change',()=>{closeDetail();render();});
        document.querySelectorAll('[data-create]').forEach(b=>b.disabled=!A.hasAction('assetSubject','create'));
    }
    if(page==='主体管理-创建主体.html'){
        // 原库数据先固定归属，再判断深链接是否可以编辑。
        try{JSON.parse(localStorage.getItem('subjectLibraryItems')||'[]').forEach(s=>A.register(s.type,s));}catch(err){console.warn('读取原主体库失败',err);}
        const params=new URLSearchParams(location.search),id=params.get('id');
        if(params.get('mode')==='edit'&&id&&!A.can(A.lookup(params.get('type')||'role',id),'edit')){
            document.querySelectorAll('main input,main textarea,main select,main button,.footer button').forEach(el=>el.disabled=true);
            const note=document.createElement('div');note.className='oa-note';note.textContent='此资产不可编辑：跨部门共享只允许查看、使用，私人资产仅创建者可访问。';document.querySelector('main')?.prepend(note);
            // 不展示通过地址直接进入的私人资产内容。
            if(!A.can(A.lookup(params.get('type')||'role',id),'view'))document.querySelector('main').replaceChildren(note);
        }else voiceOptions(document.getElementById('subjectVoice'));
        wrap('previewSelectedVoice',()=>{const id=document.getElementById('subjectVoice')?.selectedOptions[0]?.dataset.voiceId;return id?A.requireAsset('voice',id,'view'):false;});
        window.addEventListener('org-access-change',()=>voiceOptions(document.getElementById('subjectVoice')));
    }
    if(page==='语音首页.html'){
        const grid=document.getElementById('models-grid');
        grid.querySelectorAll('.model-card:not(.create-card)').forEach((card,i)=>A.register('voice',{id:'legacy-voice-'+i,name:card.dataset.name,visibility:card.dataset.scope,gender:card.dataset.gender,tags:card.dataset.tags}));
        let activeVoice=null;
        function renderVoices(){
            const voices=A.list('voice').filter(a=>!a.system&&A.matches(a,window.oaAssetFilter||'all'));
            grid.innerHTML=voices.map(a=>'<article class="model-card" data-id="'+e(a.id)+'" data-name="'+e(a.name)+'" data-scope="'+e(a.visibility)+'" data-gender="'+e(a.gender||'all')+'" data-tags="'+e(a.tags||'')+'"><div class="model-card-header"><div class="model-icon" style="background:#e8efff">🎙</div><div class="model-name">'+e(a.name)+'</div></div><div class="oa-badge">'+e(A.badge(a))+'</div><div class="model-actions"><button class="btn btn-secondary btn-sm" data-view="'+e(a.id)+'">试听 / 详情</button>'+(A.can(a,'use')?'<button class="btn btn-primary btn-sm" data-use="'+e(a.id)+'">用于生成</button>':'')+(A.can(a,'edit')?'<button class="btn btn-secondary btn-sm" data-edit="'+e(a.id)+'">编辑</button>':'')+(A.can(a,'delete')?'<button class="btn btn-secondary btn-sm" data-delete="'+e(a.id)+'">删除</button>':'')+'</div></article>').join('')+(A.hasAction('assetAudio','clone')?'<a class="model-card create-card" href="新建语音模型.html"><div class="model-name">＋ 新建复刻音色</div></a>':'');
            applyFilters();
        }
        toolbar(grid,renderVoices);
        window.showWizard=()=>{if(A.hasAction('assetAudio','clone'))location.href='新建语音模型.html';else alert('当前角色没有复刻音色权限');};
        window.showDetail=function(id){
            const a=A.lookup('voice',id)||A.list('voice').find(a=>a.name===id);if(!a||!A.requireAsset('voice',a.id,'view'))return;
            activeVoice=a;showPage('detail');document.getElementById('detail-name').textContent=a.name;
            document.querySelector('#page-detail .detail-info').textContent=A.badge(a);
            const actions=document.querySelector('#page-detail .detail-header > div:last-child');actions.innerHTML='<button class="btn btn-secondary btn-sm" id="oa-listen-voice">▶ 试听</button>';
            actions.querySelector('button').onclick=()=>{if(A.requireAsset('voice',a.id,'view'))showToast('试听演示：'+a.name+'（未连接真实音频服务）');};
            const usage=document.querySelector('#page-detail .usage-list');usage.innerHTML='<div class="usage-list-header">可查看的引用记录</div>'+A.list('video').filter(v=>A.can(v,'view')&&(v.refs||[]).some(r=>r.type==='voice'&&r.id===a.id)).map(v=>'<div class="usage-item">'+e(v.name)+'</div>').join('');
        };
        grid.onclick=ev=>{const b=ev.target.closest('button');if(!b)return;const id=b.dataset.view||b.dataset.use||b.dataset.edit||b.dataset.delete;const a=A.lookup('voice',id);if(!a)return;
            if(b.dataset.view)showDetail(id);
            if(b.dataset.use&&A.requireAsset('voice',id,'use')){sessionStorage.setItem('oa-creation-preset',JSON.stringify({voiceId:id}));location.href='简单模式-流程版.html';}
            if(b.dataset.delete&&A.requireAsset('voice',id,'delete')&&confirm('确认删除音色「'+a.name+'」？已生成视频不受影响。')){A.remove('voice',id);renderVoices();}
            if(b.dataset.edit&&A.requireAsset('voice',id,'edit')){
                const d=document.createElement('dialog');d.className='oa-dialog';d.innerHTML='<h2>编辑音色</h2><label>名称<input class="oa-field" value="'+e(a.name)+'" maxlength="40"></label><label>可见范围<select class="oa-field"><option value="private">个人</option><option value="team">本部门</option></select></label><footer><button class="oa-btn">取消</button><button class="oa-btn primary">保存</button></footer>';document.body.appendChild(d);d.querySelector('select').value=a.visibility;d.querySelectorAll('button')[0].onclick=()=>d.close();d.querySelectorAll('button')[1].onclick=()=>{const name=d.querySelector('input').value.trim();if(!name){alert('请输入名称');return;}try{A.update('voice',{id,name,visibility:d.querySelector('select').value});d.close();renderVoices();}catch(err){alert(err.message);}};d.onclose=()=>d.remove();d.showModal();
            }
        };
        renderVoices();showPage('voice');window.addEventListener('org-access-change',()=>{if(activeVoice&&!A.can(A.lookup('voice',activeVoice.id),'view'))showPage('voice');renderVoices();});
    }
    if(page==='视频资产.html'){
        videoData.forEach(v=>A.register('video',v));
        A.list('video').forEach(a=>{if(videoData.some(v=>String(v.id)===a.id)||!/^\d+$/.test(a.id))return;videoData.push(Object.assign({title:a.name,desc:a.desc||'部门协作生成的成片',duration:'00:15',scope:a.visibility,gradient:'linear-gradient(135deg,#274976,#6389b5)',coverThumb:'finance-chart',creator:A.memberName(a.creatorId),date:new Date().toISOString().slice(0,10),character:'部门共享角色',scene:'财经演播室',hasWatermark:false,hasSubtitle:false},a,{id:Number(a.id)}));});
        const grid=document.getElementById('video-grid')||document.querySelector('.video-grid');if(grid)toolbar(grid,renderVideos);
        const byId=(id,action)=>A.requireAsset('video',id,action);
        ['doDownload','downloadDetailVideo','batchDownload'].forEach(name=>wrap(name,function(id){const ids=name==='batchDownload'?selectedIds:name==='downloadDetailVideo'?[detailVideo?.id]:[id];return ids.length>0&&ids.every(id=>byId(id,'download'));}));
        ['requestDelete','batchDelete','doDelete'].forEach(name=>wrap(name,function(id){const ids=name==='requestDelete'?[id]:name==='batchDelete'||deleteTargetId==='batch'?selectedIds:[deleteTargetId];return ids.length>0&&ids.every(id=>byId(id,'delete'));}));
        ['openWmEditor','syncDetailWm','setDetailSubPos','resetDetailWm','applyDetailWm','openCoverEditor','simulateUploadCover','resetCoverConfig','applyCoverConfig'].forEach(name=>wrap(name,()=>detailVideo&&byId(detailVideo.id,'edit')));
        ['openDistModal','retryDistPublish','reopenDouyinQr','viewPerformance','openWorkBinding'].forEach(name=>wrap(name,id=>byId(id,'publish')));
        wrap('openBatchDistModal',()=>selectedIds.length>0&&selectedIds.every(id=>byId(id,'publish')));
        ['confirmDist','confirmDouyinQrPublished'].forEach(name=>wrap(name,()=>typeof distVideoIds!=='undefined'&&distVideoIds.length>0&&distVideoIds.every(id=>byId(id,'publish'))));
        window.oaReplicate=function(id){if(!byId(id,'replicate'))return;const a=A.lookup('video',id);sessionStorage.setItem('oa-creation-preset',JSON.stringify({sourceVideoId:a.id,refs:a.refs||[]}));location.href='简单模式-流程版.html';};
        function decorate(){
            document.querySelectorAll('.video-card[data-id]').forEach(card=>{
                const id=card.dataset.id,a=A.lookup('video',id);if(!a)return;
                const old=card.querySelector('.oa-badge');if(old)old.remove();const badge=document.createElement('span');badge.className='oa-badge';badge.textContent=A.badge(a);card.querySelector('.video-info')?.appendChild(badge);
                card.querySelectorAll('button[onclick]').forEach(b=>{const s=b.getAttribute('onclick');let action=/doDownload/.test(s)?'download':/requestDelete/.test(s)?'delete':/openDistModal|viewPerformance/.test(s)?'publish':null;if(action&&!A.can(a,action))b.hidden=true;});
                const menu=card.querySelector('.dropdown-menu');if(menu&&!menu.querySelector('[data-oa-replicate]')&&A.can(a,'replicate')){const b=document.createElement('button');b.className='dropdown-item';b.dataset.oaReplicate='1';b.textContent='复刻同款';b.onclick=ev=>{ev.stopPropagation();oaReplicate(id);};menu.prepend(b);}
            });
        }
        wrap('renderVideos',null,decorate);
        wrap('openDetail',null,()=>{if(!detailVideo)return;const a=A.lookup('video',detailVideo.id);document.getElementById('d-scope').textContent=A.badge(a);document.querySelectorAll('#detail-ov button[onclick],#detail-panel button[onclick]').forEach(b=>{if(/openWmEditor|openCoverEditor/.test(b.getAttribute('onclick')))b.hidden=!A.can(a,'edit');});const download=document.getElementById('detailDownloadBtn');if(download&&!A.can(a,'download')){download.disabled=true;download.title='跨部门视频仅允许预览与复刻';}});
        renderVideos();window.addEventListener('org-access-change',()=>{selectedIds=selectedIds.filter(id=>A.can(A.lookup('video',id),'view'));if(detailVideo&&!A.can(A.lookup('video',detailVideo.id),'view'))closeDetail();renderVideos();});
    }
})();
