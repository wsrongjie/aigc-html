/* 任务页面使用完整任务集写入，仅在展示处过滤，防止覆盖不可见任务。 */
(function(){
    const A=OrgAccess;
    function all(){return typeof loadTasks==='function'?loadTasks():typeof mockTasks!=='undefined'?mockTasks:[];}
    function asset(t){return t?A.register('video',Object.assign({},t,{id:'director:'+t.id,name:t.taskName})):null;}
    function visible(t){return A.can(asset(t),'view');}
    function selected(){const names=typeof selectedGroups!=='undefined'?selectedGroups:typeof selectedTaskNames!=='undefined'?selectedTaskNames:new Set();return all().filter(t=>names.has(t.taskName));}
    function rows(target){
        if(target===undefined||target===null)return selected();
        if(Array.isArray(target))return all().filter(t=>target.some(id=>String(id)===String(t.id)));
        return all().filter(t=>String(t.id)===String(target)||t.taskName===target);
    }
    function guard(action,target){
        A.fresh();const targets=rows(target);
        if(!targets.length){alert('没有可操作的任务，请先选择任务。');return false;}
        for(const t of targets){const a=asset(t);if(!A.can(a,action==='generate'?'edit':action)){alert('无权操作「'+t.taskName+'」。跨组织视频仅允许预览与复刻。');return false;}if(action==='generate'){const errors=A.validateRefs(t.refs||[]);if(!t.refs?.length)errors.push('历史任务缺少素材引用，请通过复刻同款重新选择素材');if(errors.length){alert(errors.join('\n'));return false;}}}
        return true;
    }
    function replicate(id){
        if(!guard('replicate',id))return;
        const t=rows(id)[0],a=asset(t);
        sessionStorage.setItem('oa-creation-preset',JSON.stringify({sourceVideoId:a.id,refs:t.refs||a.refs||[]}));
        location.href='简单模式-流程版.html';
    }
    function handoff(key,id){
        const t=rows(id)[0];if(!t)return;let d;try{d=JSON.parse(localStorage.getItem(key)||'null');}catch(err){return;}if(!d)return;
        Object.assign(d,{creatorId:asset(t).creatorId,orgId:asset(t).orgId,refs:t.refs||[],sourceAssetId:'director:'+t.id});localStorage.setItem(key,JSON.stringify(d));
    }
    window.OrgTask={all,asset,visible,rows,guard,replicate,handoff};
})();
