/* 团队管理页：部门、成员归属及单向授权。 */
(function () {
    const A=OrgAccess, e=A.esc;
    A.bindTeam(M);
    const section=document.createElement('section'); section.id='organizations'; section.className='card';
    section.innerHTML='<div class="card-header"><div><div class="card-title">部门管理</div><div class="card-subtitle">平行部门 · 一人一部门 · 资产按类型单向开放</div></div><button class="btn btn-primary btn-sm" id="oa-new-org">＋ 新建部门</button></div><div class="card-body"><div class="oa-note">部门共享资产默认在本部门内可见、可用。跨部门授权不包含私人资产，不授予编辑、删除、下载或发布权限。</div><div class="oa-orgs" id="oa-orgs"></div></div>';
    document.getElementById('members').before(section);
    const anchor=document.createElement('a'); anchor.className='anchor-item'; anchor.href='#organizations'; anchor.textContent='部门管理'; anchor.onclick=event=>{event.preventDefault();section.scrollIntoView({behavior:'smooth',block:'start'});};
    document.querySelector('.anchor-bar').insertBefore(anchor,document.querySelector('[data-anchor="members"]'));
    const orgField=document.createElement('div'); orgField.className='form-group'; orgField.innerHTML='<label class="form-label" for="oa-add-member-org">所属部门</label><select class="form-input" id="oa-add-member-org"></select>';
    document.querySelector('#modalInvite .modal-body').appendChild(orgField);
    const toolbar=document.querySelector('#members .toolbar');
    const filter=document.createElement('select');filter.className='oa-field';filter.setAttribute('aria-label','按所属部门筛选');toolbar.appendChild(filter);
    document.querySelector('#members thead tr').insertAdjacentHTML('afterbegin','<th>所属部门</th>');
    const dialog=document.createElement('dialog');dialog.className='oa-dialog';document.body.appendChild(dialog);
    function show(title,body,onSave,buttonText) {
        dialog.innerHTML='<form method="dialog"><h2>'+e(title)+'</h2>'+body+'<div class="oa-error" role="alert"></div><footer><button class="oa-btn" value="cancel">取消</button><button type="button" class="oa-btn primary" id="oa-dialog-save">'+e(buttonText||'保存')+'</button></footer></form>';
        dialog.querySelector('#oa-dialog-save').onclick=()=>{try{onSave();dialog.close();render();}catch(err){dialog.querySelector('.oa-error').textContent=err.message;}};
        dialog.showModal();
    }
    function editOrg(id) {
        if(!A.requireAdmin())return; const org=A.state.orgs.find(o=>o.id===id);
        show(org?'编辑部门':'新建部门','<label>部门名称<input class="oa-field" id="oa-org-name" maxlength="30" value="'+e(org?org.name:'')+'"></label><label>说明<textarea class="oa-field" id="oa-org-desc" maxlength="100">'+e(org?org.desc:'')+'</textarea></label>',()=>{
            if(!A.requireAdmin())throw Error('无管理权限');
            const name=dialog.querySelector('#oa-org-name').value.trim(),desc=dialog.querySelector('#oa-org-desc').value.trim();
            if(!name)throw Error('请输入部门名称');
            A.commit(s=>{if(s.orgs.some(o=>o.id!==id&&o.name===name))throw Error('部门名称已存在');if(org){const target=s.orgs.find(o=>o.id===id);target.name=name;target.desc=desc;}else{s.orgs.push({id:'org-'+Date.now(),name,desc});}});
        });
    }
    function grants(id) {
        if(!A.requireAdmin())return;
        const source=A.state.orgs.find(o=>o.id===id), current=A.state.grants[id]||{};
        show('允许「'+source.name+'」访问哪些部门的资产','<div class="oa-note">访问方：'+e(source.name)+'。勾选后，该部门所有成员可查看、使用来源部门此类共享资产（包含后续新增）；角色操作权限仍然生效，授权不会反向或传递。</div><div style="overflow:auto"><table><thead><tr><th>资产来源部门</th>'+Object.values(A.types).map(t=>'<th>'+t+'</th>').join('')+'</tr></thead><tbody>'+A.state.orgs.filter(o=>o.id!==id).map(o=>'<tr><td>'+e(o.name)+'</td>'+Object.keys(A.types).map(t=>'<td><input type="checkbox" aria-label="'+e(source.name+'访问'+o.name+A.types[t])+'" data-org="'+e(o.id)+'" data-type="'+t+'" '+((current[o.id]||[]).includes(t)?'checked':'')+'></td>').join('')+'</tr>').join('')+'</tbody></table></div><div class="oa-note" id="oa-grant-preview"></div>',()=>{
            if(!A.requireAdmin())throw Error('无管理权限');
            const next={};dialog.querySelectorAll('input:checked').forEach(c=>{(next[c.dataset.org]||(next[c.dataset.org]=[])).push(c.dataset.type);});
            A.commit(s=>{s.grants[id]=next;});
        });
        const preview=()=>{const selected=Array.from(dialog.querySelectorAll('input:checked')).map(c=>A.orgName(c.dataset.org)+'的'+A.types[c.dataset.type]);dialog.querySelector('#oa-grant-preview').textContent='生效预览：'+source.name+'可访问本部门共享资产'+(selected.length?'，以及'+selected.join('、'):'；其他部门资产均未开放')+'。仅自己资产不在授权范围内。';};
        dialog.querySelectorAll('input').forEach(c=>c.onchange=preview);preview();
    }
    function deleteOrg(id){
        if(!A.requireAdmin())return;
        const members=A.state.members.filter(m=>m.orgId===id).length,assets=A.list().filter(a=>a.orgId===id).length;
        if(members||assets){alert('该部门仍有 '+members+' 名成员、'+assets+' 项归属资产，暂不能删除。');return;}
        show('删除空部门','<p>确认删除「'+e(A.orgName(id))+'」？关联的跨部门授权也将清理。</p>',()=>{if(!A.requireAdmin())throw Error('无管理权限');A.commit(s=>{if(s.members.some(m=>m.orgId===id)||Object.values(s.assets).some(a=>a.orgId===id))throw Error('部门已被使用，请刷新后重试');s.orgs=s.orgs.filter(o=>o.id!==id);delete s.grants[id];Object.values(s.grants).forEach(g=>delete g[id]);});},'确认删除');
    }
    window.oaMoveMember=function(id){
        if(!A.requireAdmin())return;const m=M.members.find(x=>x.id===id);if(!m)return;
        show('变更成员部门','<p>'+e(m.name)+'的角色和积分额度保持不变，历史资产保留原归属。</p><label>新部门<select id="oa-target-org" class="oa-field">'+A.state.orgs.map(o=>'<option value="'+e(o.id)+'" '+(m.orgId===o.id?'selected':'')+'>'+e(o.name)+'</option>').join('')+'</select></label>',()=>{if(!A.requireAdmin())throw Error('无管理权限');m.orgId=dialog.querySelector('#oa-target-org').value;A.syncTeam(M);renderMemberTable();});
    };
    function render(){
        const admin=!!(A.user()&&A.user().admin);
        document.getElementById('oa-new-org').disabled=!admin;
        document.getElementById('oa-orgs').innerHTML=A.state.orgs.map(o=>{
            const rules=A.state.grants[o.id]||{};
            const summary=Object.keys(rules).filter(k=>rules[k].length).map(k=>A.orgName(k)+'：'+rules[k].map(t=>A.types[t]).join('、')).join('；');
            return '<article class="oa-org"><h3>'+e(o.name)+'</h3><p>'+e(o.desc||'暂无说明')+'</p><p>'+A.state.members.filter(m=>m.orgId===o.id).length+' 名成员</p><p>可访问其他部门：'+e(summary||'未配置')+'</p><footer><button class="oa-btn primary" data-grant="'+e(o.id)+'" '+(!admin?'disabled':'')+'>资产授权</button><button class="oa-btn" data-edit="'+e(o.id)+'" '+(!admin?'disabled':'')+'>编辑</button><button class="oa-btn danger" data-delete="'+e(o.id)+'" '+(!admin?'disabled':'')+'>删除</button></footer></article>';
        }).join('');
        const old=filter.value;filter.innerHTML='<option value="">全部部门</option>'+A.state.orgs.map(o=>'<option value="'+e(o.id)+'">'+e(o.name)+'</option>').join('');filter.value=old;
        const select=document.getElementById('oa-add-member-org'),selected=select.value;select.innerHTML='<option value="">请选择部门</option>'+A.state.orgs.map(o=>'<option value="'+e(o.id)+'">'+e(o.name)+'</option>').join('');select.value=selected;
        document.getElementById('tn-members').textContent=M.members.length;document.getElementById('tn-roles').textContent=M.roles.length;
        document.querySelectorAll('#members .card-header button,#roles .card-header button,.credit-card button').forEach(b=>b.disabled=!admin);
    }
    section.onclick=event=>{const b=event.target.closest('button');if(!b)return;if(b.id==='oa-new-org')editOrg();if(b.dataset.edit)editOrg(b.dataset.edit);if(b.dataset.grant)grants(b.dataset.grant);if(b.dataset.delete)deleteOrg(b.dataset.delete);};
    const oldRender=window.renderMemberTable;
    window.renderMemberTable=function(){
        oldRender();let count=0;
        document.querySelectorAll('#memberTbody tr').forEach(row=>{
            const button=row.querySelector('button');if(!button){row.querySelector('td').colSpan=7;return;}
            const match=button.getAttribute('onclick').match(/'([^']+)'/);const m=match&&M.members.find(m=>m.id===match[1]);if(!m)return;
            row.insertAdjacentHTML('afterbegin','<td>'+e(A.orgName(m.orgId))+'</td>');
            row.querySelector('.actions').insertAdjacentHTML('afterbegin','<button class="btn-text" onclick="oaMoveMember(\''+e(m.id)+'\')">变更部门</button>');
            if(filter.value&&m.orgId!==filter.value)row.hidden=true;else count++;
            if(!A.user()||!A.user().admin)row.querySelectorAll('button').forEach(b=>b.disabled=true);
        });
        document.getElementById('memberCount').textContent='共 '+count+' 人';A.syncTeam(M);render();
    };
    filter.onchange=renderMemberTable;
    ['addMember','confirmChangeRole','confirmAllocCredits','saveRole','deleteRole','submitRecharge','removeMember','openNewRoleModal','editRole','allocMemberCredits','changeRole'].forEach(name=>{
        const fn=window[name];window[name]=function(){
            if(!A.requireAdmin())return;
            if(name==='removeMember'&&A.state.members.find(m=>m.id===arguments[0]&&m.admin)){alert('租户管理员不能被移除。');return;}
            if(name==='addMember'&&!document.getElementById('oa-add-member-org').value){toast('请选择所属部门','error');return;}
            return fn.apply(this,arguments);
        };
    });
    render();init();
    window.addEventListener('org-access-change',()=>{A.bindTeam(M);oldRender();renderMemberTable();renderRoleCards();updateCreditOverview();});
})();
