/* 组织资产权限原型：仅用于同源浏览器演示，不替代服务端鉴权。 */
(function () {
    'use strict';
    const KEY = 'xingzao_org_access_v1';
    const types = { voice: '音色', role: '角色', scene: '场景', video: '视频' };
    const copy = value => JSON.parse(JSON.stringify(value));
    const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const allPages={assetSubject:['create','edit','delete','publish'],assetAudio:['upload','clone','audit','edit','delete'],assetVideo:['upload','preview','download','edit','delete'],director:['create','generate','export','template'],tools:['use','batch','download','manage'],team:['invite','role','credit','remove'],billing:['view','export','recharge','invoice']};
    const defaultRoles=[
        {id:'r1',name:'投顾管理员',permissions:{pages:Object.keys(allPages),actions:allPages}},
        {id:'r2',name:'高级投顾',permissions:{pages:['assetSubject','assetAudio','assetVideo','director','tools','billing'],actions:{assetSubject:['create','edit','publish'],assetAudio:['upload','clone','edit'],assetVideo:['preview','download','edit'],director:['create','generate','export','template'],tools:['use','download'],billing:['view']}}},
        {id:'r3',name:'内容审核员',permissions:{pages:['assetAudio','assetVideo','director','billing'],actions:{assetAudio:['audit'],assetVideo:['preview'],director:['generate'],billing:['view']}}}
    ];
    const initial = {
        version: 1, currentId: 'm1',
        orgs: [{id:'org-a',name:'投顾一组',desc:'日常投顾内容创作'}, {id:'org-b',name:'投顾二组',desc:'专业解读与素材协作'}, {id:'org-c',name:'品牌内容组',desc:'品牌内容与场景制作'}],
        members: [
            {id:'m1',name:'王晓明',orgId:'org-a',roleId:'r1',admin:true},
            {id:'m2',name:'李建国',orgId:'org-b',roleId:'r1',admin:false},
            {id:'m3',name:'张伟',orgId:'org-a',roleId:'r2',admin:false},
            {id:'m4',name:'陈静',orgId:'org-b',roleId:'r2',admin:false},
            {id:'m5',name:'赵六',orgId:'org-c',roleId:'r3',admin:false}
        ],
        grants: {'org-a': {'org-b':['voice','role','scene','video']}}, assets: {}, deleted: {}, team: null, roles: defaultRoles
    };
    function read() {
        try { const raw = localStorage.getItem(KEY); if (raw) { const s = JSON.parse(raw); if (s.version === 1 && Array.isArray(s.orgs) && Array.isArray(s.members)) return s; } }
        catch (e) { console.warn('组织演示数据读取失败', e); }
        return copy(initial);
    }
    let state = read();
    if(!state.roles.length)state.roles=copy(defaultRoles);
    state.deleted=state.deleted||{};
    function save() {
        try { localStorage.setItem(KEY, JSON.stringify(state)); }
        catch(e) { throw new Error('组织数据保存失败，请检查浏览器存储空间。'); }
    }
    function fresh() { state = read(); return state; }
    function user() { return state.members.find(m => m.id === state.currentId) || null; }
    function orgName(id) { const org = state.orgs.find(o => o.id === id); return org ? org.name : '原组织'; }
    function memberName(id) { const m = state.members.find(m => m.id === id); return m ? m.name : '已移除成员'; }
    function privateScope(value) { return !['team','团队共享','团队可见','组织共享'].includes(value); }
    function assetKey(type,id) { return type + ':' + id; }
    function register(type, source, options) {
        options = options || {};
        const id = String(source.id);
        const key = assetKey(type,id);
        if((state.deleted||{})[key])return Object.assign({},source,{id,type,deleted:true});
        let record = state.assets[key];
        if (!record) {
            record = Object.assign({}, source, {
                id, type, name: source.name || source.title || source.taskName || id,
                creatorId: source.creatorId || options.creatorId || 'm1',
                orgId: source.orgId || options.orgId || 'org-a',
                visibility: privateScope(source.visibility || source.scope) ? 'private' : 'team'
            });
            state.assets[key] = record;
            save();
        }
        return Object.assign({}, source, record);
    }
    function lookup(type,id) { return state.assets[assetKey(type,String(id))] || null; }
    function list(type) { return Object.values(state.assets).filter(a => !type || a.type === type); }
    function hasAction(page, action) {
        const u = user(); if (!u) return false;
        if (u.admin) return true;
        const role = state.roles.find(r => r.id === u.roleId);
        if (!role) return false;
        const p = role.permissions || {};
        return (p.pages || []).includes(page) && (!action || ((p.actions || {})[page] || []).includes(action));
    }
    function pageOf(a) { return a.type === 'voice' ? 'assetAudio' : a.type === 'video' ? 'assetVideo' : 'assetSubject'; }
    function can(a, action) {
        const u = user(); if (!u || !a || a.deleted) return false;
        if (!hasAction(pageOf(a))) return false;
        const mine = a.creatorId === u.id;
        const local = a.orgId === u.orgId;
        const publicAsset = a.system === true;
        const shared = a.visibility === 'team' && (local || (((state.grants[u.orgId] || {})[a.orgId] || []).includes(a.type)));
        if (!(mine || publicAsset || shared)) return false;
        if (!action || action === 'view') return a.type !== 'video' || hasAction('assetVideo','preview');
        if (action === 'use') return hasAction('director','generate');
        if (action === 'replicate') return a.type === 'video' && hasAction('director','generate');
        if (publicAsset || (!mine && !local)) return false;
        if (action === 'download') return hasAction(pageOf(a),'download');
        if (action === 'publish') return hasAction('assetVideo','download');
        if (!mine && !u.admin) return false;
        return hasAction(pageOf(a), action === 'share' ? 'edit' : action);
    }
    function requireAsset(type,id,action) {
        fresh(); const a = lookup(type,id);
        if (!can(a,action)) { alert('当前账号无权' + ({view:'查看',use:'使用',edit:'编辑',delete:'删除',download:'下载',publish:'发布',replicate:'复刻',share:'修改共享范围'}[action] || '操作') + '该资产。'); return false; }
        return true;
    }
    function requireAdmin() { fresh(); if (user() && user().admin) return true; alert('仅租户管理员可以管理组织、成员及授权。'); return false; }
    function badge(a) { return orgName(a.orgId) + ' · ' + memberName(a.creatorId) + ' · ' + (a.visibility === 'private' ? '仅自己' : '组织共享'); }
    function matches(a, filter) {
        if (!can(a,'view')) return false;
        const u = user();
        return !filter || filter === 'all' || (filter === 'mine' && a.creatorId === u.id) || (filter === 'local' && a.orgId === u.orgId && a.visibility === 'team') || (filter === 'other' && a.orgId !== u.orgId && a.visibility === 'team');
    }
    function create(type, data) {
        fresh(); const u = user();
        const page = type === 'voice' ? 'assetAudio' : type === 'video' ? 'director' : 'assetSubject';
        const action = type === 'voice' ? 'clone' : type === 'video' ? 'generate' : 'create';
        if (!u || !hasAction(page,action)) throw new Error('当前角色没有创建此类资产的权限。');
        const a = Object.assign({},data,{id:String(data.id || ('created-' + Date.now() + '-' + Math.random().toString(36).slice(2,7))),type,creatorId:u.id,orgId:u.orgId,visibility:privateScope(data.visibility || data.scope) ? 'private':'team'});
        a.name = a.name || a.title || '未命名资产';
        state.assets[assetKey(type,a.id)] = a; save(); return copy(a);
    }
    function update(type,data) {
        fresh(); const a = lookup(type,data.id);
        if (!can(a,'edit')) throw new Error('无权编辑该资产。');
        const next = Object.assign({},a,data,{id:a.id,type:a.type,orgId:a.orgId,creatorId:a.creatorId});
        next.visibility = privateScope(data.visibility || a.visibility) ? 'private':'team';
        state.assets[assetKey(type,a.id)] = next; save(); return copy(next);
    }
    function remove(type,id) {
        fresh(); const a = lookup(type,id);
        if (!can(a,'delete')) throw new Error('无权删除该资产。');
        state.deleted=state.deleted||{};state.deleted[assetKey(type,id)]=true;
        delete state.assets[assetKey(type,id)]; save();
    }
    function validateRefs(refs) {
        fresh();
        if (!hasAction('director','generate')) return ['当前角色没有视频生成权限'];
        const errors = [];
        (refs || []).forEach(ref => {
            const a = lookup(ref.type,ref.id);
            if (!can(a,'use')) errors.push((a ? a.name : '缺失的' + (types[ref.type] || '素材')) + '：请替换为有权使用的素材');
            if (a && a.type === 'role' && a.voiceId && !(refs||[]).some(r=>r.type==='voice') && !can(lookup('voice',a.voiceId),'use')) errors.push(a.name + '关联音色不可用，请更换音色');
        });
        return Array.from(new Set(errors));
    }
    function seed() {
        if (state.seeded) return;
        ['a','b','c'].forEach((letter,i) => {
            const owner = ['m3','m4','m5'][i], org = 'org-' + letter, prefix = ['一组','二组','品牌组'][i];
            Object.keys(types).forEach(type => {
                const id = type === 'video' ? String(9101+i) : 'orgdemo-' + type + '-' + letter;
                if (lookup(type,id)) return;
                state.assets[assetKey(type,id)] = {id,type,name:prefix + ' · ' + ({voice:'专业播报音色',role:'投顾主持人',scene:'财经演播室',video:'市场观察成片'}[type]),creatorId:owner,orgId:org,visibility:'team',demo:true,
                    voiceId:type === 'role' ? 'orgdemo-voice-' + letter : undefined,
                    refs:type === 'video' ? [{type:'role',id:'orgdemo-role-' + letter},{type:'voice',id:'orgdemo-voice-' + letter},{type:'scene',id:'orgdemo-scene-' + letter}] : undefined,
                    desc:'用于组织授权演示的' + types[type],img:type === 'role' ? './assets/role-2.png' : undefined, tags:['组织演示'],status:'可用'};
            });
            const id = 'orgdemo-private-' + letter;
            if (!lookup('voice',id)) state.assets[assetKey('voice',id)] = {id,type:'voice',name:prefix + ' · 私人试验音色',creatorId:owner,orgId:org,visibility:'private',demo:true};
        });
        state.seeded=true; save();
    }
    seed();
    function notify() { window.dispatchEvent(new CustomEvent('org-access-change')); }
    function commit(change) { fresh(); change(state); save(); notify(); }
    function syncTeam(M) {
        fresh(); if (!user() || !user().admin) return;
        state.team = copy(M); state.roles = copy(M.roles);
        state.members = M.members.map(m => { const old = state.members.find(x => x.id === m.id); return Object.assign({},old || {},{id:m.id,name:m.name,roleId:m.roleId,orgId:m.orgId || (old && old.orgId) || 'org-a',admin:!!(old && old.admin)}); });
        save();
    }
    function bindTeam(M) {
        fresh(); if (state.team) Object.assign(M,copy(state.team));
        M.members.forEach(m => { const member = state.members.find(u => u.id === m.id); m.orgId = member ? member.orgId : 'org-a'; });
        if (!state.roles.length) { state.roles = copy(M.roles); save(); }
    }
    window.OrgAccess = {KEY,types,esc,fresh,get state(){return state;},user,orgName,memberName,register,lookup,list,can,hasAction,requireAsset,requireAdmin,badge,matches,create,update,remove,validateRefs,commit,syncTeam,bindTeam,notify};
    window.addEventListener('storage', e => { if (e.key === KEY) { fresh(); notify(); } });
    window.addEventListener('focus', () => { fresh(); notify(); });
    document.addEventListener('DOMContentLoaded', () => {
        const link = document.createElement('link'); link.rel='stylesheet'; link.href='assets/org-access-ui.css'; document.head.appendChild(link);
        const panel = document.createElement('details'); panel.className='oa-identity';
        panel.innerHTML='<summary>原型演示身份</summary><label>当前成员<select aria-label="切换演示成员"></select></label><p></p><a href="团队管理.html#organizations">配置组织授权 →</a>';
        document.body.appendChild(panel);
        function renderIdentity() {
            panel.querySelector('select').innerHTML=state.members.map(m => '<option value="'+esc(m.id)+'"'+(m.id===state.currentId?' selected':'')+'>'+esc(m.name+' · '+orgName(m.orgId)+(m.admin?' · 管理员':''))+'</option>').join('');
            panel.querySelector('p').textContent='仅用于原型演示；私人资产不对管理员开放。';
        }
        panel.querySelector('select').onchange=e => { commit(s=>{s.currentId=e.target.value;}); location.reload(); };
        renderIdentity(); window.addEventListener('org-access-change',renderIdentity);
    });
})();
