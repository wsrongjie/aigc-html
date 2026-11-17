/* ===================== 违规列表 V1（销售违规记录，客户维度） ===================== */
var FDE_VIO_NOW = '2026-11-14 18:00:00';
var FDE_VIO_TYPES = ['承诺收益','违规荐股','代客操作','返佣飞单','夸大宣传','泄露信息','不当言辞','未揭示风险'];
var FDE_VIO_PRESETS = ['全部','待认定','整改中','待验收','已闭环','申诉中','逾期','重复违规'];
var FDE_VIO_SUP = {'服务一部':'赵敏','高净值一部':'孙倩','服务二部':'李强','服务三部':'王海','高净值二部':'陈静','线上运营部':'周岚'};

function fdeVioPad(n){ n = String(n); return n.length < 2 ? '0' + n : n; }
function fdeVioTs(s){
  s = String(s || '');
  var m = s.match(/(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/);
  if(m) return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)).getTime();
  m = s.match(/(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})/);
  if(m) return new Date(2026, +m[1] - 1, +m[2], +m[3], +m[4], 0).getTime();
  return 0;
}
function fdeVioFmt(ts){
  var d = new Date(ts);
  return d.getFullYear() + '-' + fdeVioPad(d.getMonth() + 1) + '-' + fdeVioPad(d.getDate()) + ' ' + fdeVioPad(d.getHours()) + ':' + fdeVioPad(d.getMinutes()) + ':' + fdeVioPad(d.getSeconds());
}
function fdeVioShift(base, hours){ return fdeVioFmt(fdeVioTs(base) + hours * 3600000); }
function fdeVioNowShort(){ return FDE_VIO_NOW.slice(5, 16); }
var FDE_VIO_NOW_TS = fdeVioTs(FDE_VIO_NOW);

var FDE_VIO = {mode:'list', id:null, preset:'全部', type:'全部类型', level:'全部', time:'全部时间', from:'', to:'', keyword:'', onlyRepeat:false};

/* ---------- 证据话术模板（命中行由每条记录自己的 quote 替换） ---------- */
var FDE_VIO_SCRIPTS = {
  '承诺收益':[
    {who:'client', text:'老师，这个产品风险大吗？我之前亏过。'},
    {who:'sales', text:'这个产品保本保收益，年化至少 15%，亏了我兜着。', hit:true},
    {who:'client', text:'真的不会亏吗？'},
    {who:'sales', text:'我们做了这么多年，从来没让客户亏过，你大胆买。'}
  ],
  '违规荐股':[
    {who:'client', text:'最近有什么能买的票吗？'},
    {who:'sales', text:'明天这只票必涨停，我内部有消息，跟上就行。', hit:true},
    {who:'client', text:'要不要设个止损？'},
    {who:'sales', text:'不用，听我的，满仓进。'}
  ],
  '代客操作':[
    {who:'client', text:'我平时上班没时间看盘。'},
    {who:'sales', text:'你把账号密码给我，我帮你操作，保证赚回来。', hit:true},
    {who:'client', text:'这样合规吗？'},
    {who:'sales', text:'没事，我们都这么干，别跟别人说。'}
  ],
  '返佣飞单':[
    {who:'client', text:'服务费有点高。'},
    {who:'sales', text:'服务费我私下返你 30%，别走公司合同。', hit:true},
    {who:'client', text:'那合同怎么签？'},
    {who:'sales', text:'签个基础版就行，剩下的转我微信。'}
  ],
  '夸大宣传':[
    {who:'client', text:'跟着你们真能赚钱吗？'},
    {who:'sales', text:'跟着老师做，三个月翻倍，从来没亏过。', hit:true},
    {who:'client', text:'这么厉害？'},
    {who:'sales', text:'我们客户平均收益 40%，你随便问。'}
  ],
  '泄露信息':[
    {who:'client', text:'你们都谁买了这个产品？'},
    {who:'sales', text:'刘女士刚买了 50 万，张先生也加了 30 万，你跟着买准没错。', hit:true},
    {who:'client', text:'他们把仓位都告诉你啦？'},
    {who:'sales', text:'那当然，客户都信我。'}
  ],
  '不当言辞':[
    {who:'client', text:'我想再考虑一下。'},
    {who:'sales', text:'隔壁那家就是骗子，只有我们靠谱，你别被他们忽悠。', hit:true},
    {who:'client', text:'你们这样说别人不好吧。'},
    {who:'sales', text:'我说的是事实，爱信不信。'}
  ],
  '未揭示风险':[
    {who:'client', text:'这个产品有什么风险吗？'},
    {who:'sales', text:'没风险，放心买，收益稳得很。', hit:true},
    {who:'client', text:'不用做风险测评吗？'},
    {who:'sales', text:'不用，走个形式就行，别耽误时间。'}
  ]
};

function fdeVioDefaultReqs(type){
  var map = {
    '承诺收益':['立即停止收益承诺并撤回已发送内容','完成合规专项培训并提交签到记录','向客户补充风险揭示并留存沟通记录'],
    '违规荐股':['立即停止推荐具体标的','提交后续客户沟通整改说明','完成投顾合规专项培训'],
    '代客操作':['立即交还客户账户并停止代客操作','提交账户操作明细与客户确认书','完成合规专项培训'],
    '返佣飞单':['停止私下收费并退还相关款项','提交收费明细与退款凭证','完成廉洁合规培训'],
    '夸大宣传':['撤回夸大宣传内容','提交更正后的宣传口径','完成宣传合规培训'],
    '泄露信息':['停止向第三方披露客户信息','提交信息泄露范围说明','完成客户信息保护培训'],
    '不当言辞':['停止贬损同业与不当表述','提交书面检讨','完成服务规范培训'],
    '未揭示风险':['补充完整风险揭示','重新完成风险测评与双录','提交整改说明']
  };
  return map[type] || map['承诺收益'];
}

function fdeVioBuildLogs(v){
  var logs = [v.time.slice(5, 16) + ' ' + v.source + '命中「' + v.type + '」，置信度 ' + v.conf + '%'];
  if(v.status !== '待认定'){
    logs.push(fdeVioShift(v.time, 2).slice(5, 16) + ' 合规认定：' + v.level + '级违规' + (v.due ? '，整改期限 ' + v.due.slice(5, 16) : ''));
  }
  if(v.status === '待验收' || v.status === '已闭环'){
    logs.push(fdeVioShift(v.time, 26).slice(5, 16) + ' 销售提交整改材料，进入待验收');
  }
  if(v.status === '已闭环'){
    logs.push(fdeVioShift(v.time, 30).slice(5, 16) + ' 风控验收通过，已闭环' + (v.punish ? '（' + v.punish + '）' : ''));
  }
  if(v.status === '申诉中'){
    logs.push(fdeVioShift(v.time, 8).slice(5, 16) + ' 销售提交申诉：' + (v.appeal || '对认定结论有异议'));
  }
  if(v.status === '误报'){
    logs.push(fdeVioShift(v.time, 6).slice(5, 16) + ' 合规复核判定误报：' + (v.falseReason || '证据不足'));
  }
  return logs;
}

function fdeVioSeed(){
  var rows = [
    {id:'VIO-1114-001', time:'2026-11-14 10:12:00', sales:'王蕊', team:'服务一部', client:'陈先生', cid:'K-2031', channel:'企微会话', source:'合规抽检', type:'承诺收益', level:'高', quote:'这个产品保本保收益，年化至少 15%，亏了我兜着。', conf:96, status:'待认定', due:'2026-11-15 10:12:00', prev:0, eid:'EV-1023-011'},
    {id:'VIO-1114-002', time:'2026-11-14 09:35:00', sales:'刘杉', team:'高净值一部', client:'刘女士', cid:'K-0912', channel:'企微会话', source:'客户举报', type:'违规荐股', level:'高', quote:'明天这只票必涨停，我内部有消息，跟上就行。', conf:97, status:'待认定', due:'2026-11-15 09:35:00', prev:0, eid:'EV-1021-007'},
    {id:'VIO-1114-003', time:'2026-11-14 08:50:00', sales:'何静', team:'服务一部', client:'卢先生', cid:'K-1215', channel:'企微会话', source:'系统抽检', type:'夸大宣传', level:'中', quote:'跟着老师做，三个月翻倍，从来没亏过。', conf:91, status:'待认定', due:'2026-11-16 08:50:00', prev:0, eid:'EV-1114-003', room:'2412', session:'11-14 07:30-09:30'},
    {id:'VIO-1113-004', time:'2026-11-13 20:41:00', sales:'周洋', team:'服务三部', client:'姜先生', cid:'K-1231', channel:'企微会话', source:'系统抽检', type:'不当言辞', level:'低', quote:'隔壁那家就是骗子，只有我们靠谱。', conf:86, status:'待认定', due:'2026-11-16 20:41:00', prev:0, eid:'EV-1114-004', room:'3106', session:'11-13 19:30-21:30'},
    {id:'VIO-1113-005', time:'2026-11-13 16:20:00', sales:'孙浩', team:'服务二部', client:'罗女士', cid:'K-1210', channel:'客户群', source:'客户举报', type:'返佣飞单', level:'高', quote:'服务费我私下返你 30%，别走公司合同。', conf:94, status:'待认定', due:'2026-11-14 16:20:00', prev:0, eid:'EV-1113-001'},
    {id:'VIO-1113-006', time:'2026-11-13 11:05:00', sales:'唐悦', team:'线上运营部', client:'曾女士', cid:'K-1212', channel:'企微会话', source:'合规抽检', type:'未揭示风险', level:'低', quote:'没风险，放心买，收益稳得很。', conf:84, status:'待认定', due:'2026-11-16 11:05:00', prev:0, eid:'EV-1103-001', room:'2057', session:'11-13 20:00-22:00'},

    {id:'VIO-1113-007', time:'2026-11-13 10:30:00', sales:'沈璐', team:'高净值二部', client:'谢先生', cid:'K-1209', channel:'企微会话', source:'系统抽检', type:'代客操作', level:'高', quote:'你把账号密码给我，我帮你操作，保证赚回来。', conf:98, status:'整改中', due:'2026-11-16 10:30:00', prev:1, eid:'EV-1113-002'},
    {id:'VIO-1112-008', time:'2026-11-12 19:20:00', sales:'李珊', team:'高净值一部', client:'周女士', cid:'K-1201', channel:'企微会话', source:'主管巡场', type:'承诺收益', level:'中', quote:'年化 12% 保底，亏了算我的。', conf:90, status:'整改中', due:'2026-11-17 19:20:00', prev:0, eid:'EV-1114-005'},
    {id:'VIO-1112-009', time:'2026-11-12 15:30:00', sales:'陈玥', team:'服务三部', client:'潘女士', cid:'K-1216', channel:'电话录音', source:'合规抽检', type:'泄露信息', level:'中', quote:'刘女士刚买了 50 万，你也跟着买准没错。', conf:92, status:'整改中', due:'2026-11-16 15:30:00', prev:0, eid:'EV-1112-003'},
    {id:'VIO-1112-010', time:'2026-11-12 10:10:00', sales:'赵启', team:'服务二部', client:'赵先生', cid:'K-1302', channel:'企微会话', source:'系统抽检', type:'违规荐股', level:'中', quote:'这只票我盯了三个月，下周必翻倍。', conf:89, status:'整改中', due:'2026-11-17 10:10:00', prev:0, eid:'EV-1025-003'},
    {id:'VIO-1111-011', time:'2026-11-11 17:45:00', sales:'王蕊', team:'服务一部', client:'郑先生', cid:'K-1202', channel:'企微会话', source:'合规抽检', type:'承诺收益', level:'高', quote:'我们产品是保本的，合同里不写但实际兜底。', conf:95, status:'整改中', due:'2026-11-14 17:45:00', prev:0, eid:'EV-1113-005'},

    {id:'VIO-1111-012', time:'2026-11-11 11:20:00', sales:'何静', team:'服务一部', client:'曹女士', cid:'K-1206', channel:'企微会话', source:'系统抽检', type:'夸大宣传', level:'低', quote:'我们客户平均收益 40%，你随便问。', conf:83, status:'待验收', due:'2026-11-12 11:20:00', prev:0, eid:'EV-1111-001'},
    {id:'VIO-1110-013', time:'2026-11-10 20:15:00', sales:'孙浩', team:'服务二部', client:'韩先生', cid:'K-1219', channel:'文字直播间', source:'系统抽检', type:'不当言辞', level:'中', quote:'爱信不信，反正亏的不是我的钱。', conf:88, status:'待验收', due:'2026-11-17 20:15:00', prev:1, eid:'EV-1110-002', room:'2183', session:'11-10 19:30-21:30'},
    {id:'VIO-1110-014', time:'2026-11-10 14:30:00', sales:'沈璐', team:'高净值二部', client:'谢先生', cid:'K-1209', channel:'客户群', source:'客户举报', type:'返佣飞单', level:'高', quote:'签个基础版就行，剩下的转我微信。', conf:93, status:'待验收', due:'2026-11-13 14:30:00', prev:2, eid:'EV-1113-002'},
    {id:'VIO-1109-015', time:'2026-11-09 16:40:00', sales:'刘杉', team:'高净值一部', client:'林先生', cid:'K-1205', channel:'企微会话', source:'合规抽检', type:'未揭示风险', level:'中', quote:'不用做风险测评，走个形式就行。', conf:87, status:'待验收', due:'2026-11-16 16:40:00', prev:0, eid:'EV-1114-001'},

    {id:'VIO-1109-016', time:'2026-11-09 10:12:00', sales:'陈玥', team:'服务三部', client:'石女士', cid:'K-1222', channel:'企微会话', source:'系统抽检', type:'代客操作', level:'高', quote:'手机给我，我帮你把仓位调一下。', conf:96, status:'已闭环', due:'', prev:0, eid:'EV-1110-001', punish:'暂停展业'},
    {id:'VIO-1108-017', time:'2026-11-08 15:05:00', sales:'唐悦', team:'线上运营部', client:'汤女士', cid:'K-1226', channel:'文字直播间', source:'系统抽检', type:'夸大宣传', level:'中', quote:'跟着我做的客户，没有一个不赚钱的。', conf:90, status:'已闭环', due:'', prev:0, eid:'EV-1112-002', room:'2581', session:'11-08 20:00-22:00', punish:'合规培训'},
    {id:'VIO-1107-018', time:'2026-11-07 11:30:00', sales:'王蕊', team:'服务一部', client:'严先生', cid:'K-1233', channel:'企微会话', source:'合规抽检', type:'返佣飞单', level:'高', quote:'这单我私下给你返点，别让公司知道。', conf:97, status:'已闭环', due:'', prev:0, eid:'EV-1113-003', punish:'扣分'},
    {id:'VIO-1106-019', time:'2026-11-06 18:20:00', sales:'何静', team:'服务一部', client:'何先生', cid:'K-1550', channel:'电话录音', source:'客户举报', type:'承诺收益', level:'中', quote:'保本保息，年化 10%，比存款强多了。', conf:92, status:'已闭环', due:'', prev:0, eid:'EV-1026-103', punish:'警告'},
    {id:'VIO-1105-020', time:'2026-11-05 09:40:00', sales:'李珊', team:'高净值一部', client:'姚女士', cid:'K-1218', channel:'企微会话', source:'系统抽检', type:'违规荐股', level:'中', quote:'别买基金了，跟我买这只票，稳赚。', conf:89, status:'已闭环', due:'', prev:1, eid:'EV-1113-004', punish:'合规培训'},
    {id:'VIO-1104-021', time:'2026-11-04 14:15:00', sales:'周洋', team:'服务三部', client:'姜先生', cid:'K-1231', channel:'客户群', source:'系统抽检', type:'不当言辞', level:'低', quote:'那家公司就是割韭菜的，我们才是正规军。', conf:82, status:'已闭环', due:'', prev:0, eid:'EV-1114-004', punish:'警告'},

    {id:'VIO-1112-022', time:'2026-11-12 09:05:00', sales:'赵启', team:'服务二部', client:'赵先生', cid:'K-1302', channel:'企微会话', source:'合规抽检', type:'泄露信息', level:'高', quote:'张先生的持仓我发你看看，跟他买没错。', conf:95, status:'申诉中', due:'', prev:0, eid:'EV-1025-003', prevStatus:'整改中', appeal:'客户资料由客户本人转发，非本人主动提供'},
    {id:'VIO-1110-023', time:'2026-11-10 11:50:00', sales:'孙浩', team:'服务二部', client:'袁女士', cid:'K-1230', channel:'企微会话', source:'系统抽检', type:'未揭示风险', level:'低', quote:'风险提示不用讲，客户不爱听。', conf:81, status:'申诉中', due:'', prev:0, eid:'EV-1022-002', prevStatus:'整改中', appeal:'已在签约时口头提示风险，客户可作证'},

    {id:'VIO-1111-024', time:'2026-11-11 13:10:00', sales:'陈玥', team:'服务三部', client:'潘女士', cid:'K-1216', channel:'文字直播间', source:'合规抽检', type:'不当言辞', level:'低', quote:'你这种客户我见多了，不差你一个。', conf:80, status:'误报', due:'', prev:0, eid:'EV-1112-003', room:'2412', session:'11-11 19:30-21:30', falseReason:'语境为转述他人评价，非本人贬损'},
    {id:'VIO-1108-025', time:'2026-11-08 20:00:00', sales:'沈璐', team:'高净值二部', client:'施女士', cid:'K-1228', channel:'企微会话', source:'系统抽检', type:'承诺收益', level:'中', quote:'亏了公司补给你，放心吧。', conf:85, status:'误报', due:'', prev:0, eid:'EV-1103-002', falseReason:'原文为客户转述，销售已明确否认'},
    {id:'VIO-1105-026', time:'2026-11-05 16:30:00', sales:'王蕊', team:'服务一部', client:'陈先生', cid:'K-2031', channel:'企微会话', source:'合规抽检', type:'夸大宣传', level:'低', quote:'我们从来没有客户投诉，满意度 100%。', conf:79, status:'误报', due:'', prev:0, eid:'EV-1023-011', falseReason:'内容为历史业绩陈述并已附风险提示'}
  ];
  rows.forEach(function(v){
    if(!v.supervisor) v.supervisor = FDE_VIO_SUP[v.team] || '';
    if(!v.reqs) v.reqs = fdeVioDefaultReqs(v.type);
    if(!v.files) v.files = [];
    if(v.urge == null) v.urge = 0;
    if(v.round == null) v.round = 0;
    if(v.prev == null) v.prev = 0;
    if(!v.logs) v.logs = fdeVioBuildLogs(v);
  });
  return rows;
}

function fdeVioInit(){
  if(!Array.isArray(state.violations) || !state.violations.length){
    state.violations = fdeVioSeed();
    try{ localStorage.setItem('jianwei-v1', JSON.stringify(state)); }catch(e){}
  }
  state.violations.forEach(function(v){
    if(!v.supervisor) v.supervisor = FDE_VIO_SUP[v.team] || '';
    if(!v.reqs || !v.reqs.length) v.reqs = fdeVioDefaultReqs(v.type);
    if(!v.files) v.files = [];
    if(v.urge == null) v.urge = 0;
    if(v.round == null) v.round = 0;
    if(v.prev == null) v.prev = 0;
    if(v.status === '申诉中' && v.prevStatus === '待验收') v.prevStatus = '整改中';
    if(!v.logs || !v.logs.length) v.logs = fdeVioBuildLogs(v);
  });
  return state.violations;
}
function fdeVioById(id){ return fdeVioInit().filter(function(v){ return v.id === id; })[0] || null; }
function fdeVioLog(v, text){ if(!v.logs) v.logs = []; v.logs.push(fdeVioNowShort() + ' ' + text); }

/* ---------- 派生口径 ---------- */
function fdeVioRepeat(v){
  var n = Number(v.prev || 0), t = fdeVioTs(v.time);
  (state.violations || []).forEach(function(x){
    if(x.id === v.id) return;
    if(x.sales !== v.sales || x.type !== v.type) return;
    var xt = fdeVioTs(x.time);
    if(xt && xt <= t && t - xt <= 30 * 86400000) n++;
  });
  return n + 1;
}
function fdeVioStage(v){
  if(v.status === '待认定') return 1;
  if(v.status === '整改中') return 2;
  if(v.status === '待验收') return 3;
  if(v.status === '已闭环' || v.status === '误报') return 4;
  if(v.status === '申诉中') return v.prevStatus === '待验收' ? 3 : 2;
  return 1;
}
function fdeVioLevelColor(l){ return l === '高' ? 'red' : l === '中' ? 'orange' : 'blue'; }
function fdeVioStatusColor(s){
  if(s === '已闭环') return 'green';
  if(s === '待认定') return 'orange';
  if(s === '申诉中') return 'orange';
  if(s === '整改中' || s === '待验收') return 'blue';
  return '';
}
function fdeVioDue(v){
  if(v.status === '已闭环' || v.status === '误报') return {text:'已结束', cls:''};
  if(v.status === '申诉中') return {text:'申诉复核中', cls:''};
  if(!v.due) return {text:'未设置', cls:''};
  var left = fdeVioTs(v.due) - FDE_VIO_NOW_TS;
  if(left < 0){
    var h = Math.abs(left) / 3600000;
    return {text:'已逾期 ' + (h >= 24 ? (h / 24).toFixed(1) + ' 天' : Math.max(1, Math.round(h)) + ' 小时'), cls:'is-over'};
  }
  var hh = left / 3600000;
  return {text:'剩余 ' + (hh >= 24 ? (hh / 24).toFixed(1) + ' 天' : Math.max(1, Math.round(hh)) + ' 小时'), cls:hh < 24 ? 'is-soon' : ''};
}

/* ---------- 证据渲染 ---------- */
function fdeVioMsgs(v){
  var base = FDE_VIO_SCRIPTS[v.type] || FDE_VIO_SCRIPTS['承诺收益'];
  var n = base.length, t = fdeVioTs(v.time);
  return base.map(function(m, i){
    var d = new Date(t - (n - i) * 120000);
    return {who:m.who, text:m.hit ? (v.quote || m.text) : m.text, hit:!!m.hit, time:fdeVioPad(d.getHours()) + ':' + fdeVioPad(d.getMinutes())};
  });
}
function fdeVioMark(text, quote){
  var t = fdeTxt(text);
  if(!quote) return t;
  var q = fdeTxt(quote);
  return t.split(q).join('<mark>' + q + '</mark>');
}
function fdeVioChat(v){
  var msgs = fdeVioMsgs(v);
  var out = '<div class="wx-chat"><div class="wx-head"><span>' + fdeTxt(v.channel) + ' · ' + fdeTxt(v.source) + '</span><span>证据快照 ' + fdeTxt(v.time) + '</span></div>';
  msgs.forEach(function(m){
    var isOut = m.who === 'sales';
    var who = isOut ? v.sales : v.client;
    out += '<div class="wx-row' + (isOut ? ' is-out' : '') + (m.hit ? ' is-hit' : '') + '">';
    out += '<div class="wx-ava' + (isOut ? ' is-out' : '') + '">' + fdeTxt(String(who).slice(0, 1)) + '</div>';
    out += '<div class="wx-main"><div class="wx-meta"><span class="wx-name">' + fdeTxt(who) + '</span><span class="wx-role' + (isOut ? ' is-out' : '') + '">' + (isOut ? '销售' : '客户') + '</span><span class="wx-time">' + m.time + '</span>' + (m.hit ? '<span class="wx-hit-tag">违规话术命中</span>' : '') + '</div>';
    out += '<div class="wx-bubble">' + fdeVioMark(m.text, m.hit ? v.quote : '') + '</div></div></div>';
  });
  out += '<div class="wx-foot">' + (v.channel === '客户群' ? '客户群 · 群成员 12 人 · ' : '') + '保留原始消息顺序与发送人身份 · 识别快照不随最新状态覆盖</div></div>';
  return out;
}
function fdeVioLive(v){
  var msgs = fdeVioMsgs(v);
  var out = '<div class="vio-live"><div class="vio-live-head"><div><b>直播间 ' + fdeTxt(v.room || '2412') + '</b><small>场次 ' + fdeTxt(v.session || '') + '</small></div><span class="vio-tag">文字直播评论归档</span></div>';
  msgs.forEach(function(m){
    var isHost = m.who === 'sales';
    out += '<div class="vio-live-row' + (m.hit ? ' is-hit' : '') + '"><span class="vio-live-t">' + m.time + '</span><b>' + fdeTxt(isHost ? v.sales : v.client) + '</b><span class="vio-live-role">' + (isHost ? '主播' : '观众') + '</span><div class="vio-live-text">' + fdeVioMark(m.text, m.hit ? v.quote : '') + (m.hit ? ' <span class="wx-hit-tag">命中</span>' : '') + '</div></div>';
  });
  out += '<div class="vio-live-foot">直播评论实时归档 · 命中评论进入违规核查</div></div>';
  return out;
}
function fdeVioAudio(v){
  var msgs = fdeVioMsgs(v);
  var out = '<div class="vio-audio"><div class="vio-audio-bar"><span class="vio-audio-ic">☎</span><b>通话录音</b><span class="vio-audio-dur">03:48</span><span class="vio-tag">ASR 转写</span></div><div class="vio-tr">';
  msgs.forEach(function(m){
    var isOut = m.who === 'sales';
    out += '<div class="vio-tr-row' + (m.hit ? ' is-hit' : '') + '"><span class="vio-tr-t">' + m.time + '</span><b>' + fdeTxt(isOut ? v.sales : v.client) + '</b><span class="vio-tr-role">' + (isOut ? '销售' : '客户') + '</span><p>' + fdeVioMark(m.text, m.hit ? v.quote : '') + (m.hit ? ' <span class="wx-hit-tag">命中</span>' : '') + '</p></div>';
  });
  out += '</div><div class="vio-audio-foot">录音与转写同步归档 · 时间戳与说话人已校验</div></div>';
  return out;
}
function fdeVioEvidence(v){
  if(v.channel === '文字直播间') return fdeVioLive(v);
  if(v.channel === '电话录音') return fdeVioAudio(v);
  return fdeVioChat(v);
}

/* ---------- 列表 ---------- */
function fdeVioKv(k, val){
  return '<div class="vio-kv-item"><small>' + fdeTxt(k) + '</small><b>' + fdeTxt(val) + '</b></div>';
}
function fdeVioFiltered(){
  var f = FDE_VIO, kw = String(f.keyword || '').trim().toLowerCase();
  var list = (state.violations || []).filter(function(v){
    if(kw){
      var hay = [v.id, v.client, v.cid, v.sales, v.team, v.type, v.quote, v.source, v.channel].join(' ').toLowerCase();
      if(hay.indexOf(kw) < 0) return false;
    }
    if(f.type !== '全部类型' && v.type !== f.type) return false;
    if(f.level !== '全部' && v.level !== f.level) return false;
    var rng = fdeVioTimeRange();
    if(rng){
      var t = fdeVioTs(v.time);
      if(rng.from && t < rng.from) return false;
      if(rng.to && t > rng.to) return false;
    }
    if(f.onlyRepeat && fdeVioRepeat(v) < 2) return false;
    if(f.preset === '待认定' || f.preset === '整改中' || f.preset === '待验收' || f.preset === '已闭环' || f.preset === '申诉中'){
      if(v.status !== f.preset) return false;
    }else if(f.preset === '逾期'){
      if(['已闭环', '误报', '申诉中'].indexOf(v.status) >= 0) return false;
      if(!v.due || fdeVioTs(v.due) >= FDE_VIO_NOW_TS) return false;
    }else if(f.preset === '重复违规'){
      if(fdeVioRepeat(v) < 2) return false;
    }
    return true;
  });
  return list.sort(function(a, b){ return fdeVioTs(b.time) - fdeVioTs(a.time) || (b.id > a.id ? 1 : -1); });
}
function fdeVioTimeRange(){
  var f = FDE_VIO;
  if(f.time === '全部时间') return null;
  if(f.time === '自定义'){
    var from = f.from ? fdeVioTs(f.from + ' 00:00:00') : 0;
    var to = f.to ? fdeVioTs(f.to + ' 23:59:59') : 0;
    return (from || to) ? {from:from, to:to} : null;
  }
  var days = {'近1天':1, '近3天':3, '近7天':7, '近30天':30}[f.time];
  if(!days) return null;
  return {from:FDE_VIO_NOW_TS - days * 86400000, to:FDE_VIO_NOW_TS + 86400000};
}
function fdeVioSet(key, val){
  FDE_VIO[key] = val;
  if(key === 'time' && val !== '自定义'){ FDE_VIO.from = ''; FDE_VIO.to = ''; }
  render();
}
function fdeVioSetFrom(v){ FDE_VIO.from = v; render(); }
function fdeVioSetTo(v){ FDE_VIO.to = v; render(); }
function fdeVioSetRepeat(v){ FDE_VIO.onlyRepeat = !!v; render(); }
function fdeVioSetPreset(p){ FDE_VIO.preset = p; FDE_VIO.mode = 'list'; render(); }
function fdeVioSearch(v){
  FDE_VIO.keyword = v || '';
  var box = $('#fdeVioRows');
  if(box) box.innerHTML = fdeVioTable();
  var c = $('#fdeVioCount');
  if(c) c.innerText = '共 ' + fdeVioFiltered().length + ' 条';
}
function fdeVioReset(){
  FDE_VIO.preset = '全部'; FDE_VIO.type = '全部类型'; FDE_VIO.level = '全部'; FDE_VIO.time = '全部时间';
  FDE_VIO.from = ''; FDE_VIO.to = ''; FDE_VIO.keyword = ''; FDE_VIO.onlyRepeat = false;
  render();
}
function fdeVioSelect(id, options, current, handler){
  return '<select id="' + id + '" onchange="' + handler + '">' + options.map(function(o){
    return '<option value="' + fdeTxt(o) + '"' + (o === current ? ' selected' : '') + '>' + fdeTxt(o) + '</option>';
  }).join('') + '</select>';
}
function fdeVioStats(){
  var all = state.violations || [];
  var pending = all.filter(function(v){ return v.status === '待认定'; }).length;
  var rect = all.filter(function(v){ return v.status === '整改中'; }).length;
  var accept = all.filter(function(v){ return v.status === '待验收'; }).length;
  var seen = {}, clients = 0, high = 0;
  all.forEach(function(v){ if(!seen[v.cid]){ seen[v.cid] = 1; clients++; } if(v.level === '高') high++; });
  return '<div class="stats">'
    + stat('待认定', String(pending), '抽检/举报线索，等待合规认定')
    + stat('整改中', String(rect), '销售整改，主管督办')
    + stat('待验收', String(accept), '整改材料待核验')
    + stat('涉及客户', String(clients), '去重客户 · 其中红线 ' + high + ' 条')
    + '</div>';
}
function fdeVioTable(){
  var list = fdeVioFiltered();
  var heads = ['违规编号 / 来源','违规时间','销售人员','客户','违规类型','违规等级','违规话术摘要','处置阶段','重复情况','整改时限','操作'];
  var rows = list.map(function(v){
    var rep = fdeVioRepeat(v), due = fdeVioDue(v);
    var idCell = '<b>' + fdeTxt(v.id) + '</b><small>' + fdeTxt(v.source) + ' · ' + fdeTxt(v.channel) + '</small>';
    var salesCell = '<b>' + fdeTxt(v.sales) + '</b><small>' + fdeTxt(v.team) + ' · 主管 ' + fdeTxt(v.supervisor || '—') + '</small>';
    var clientCell = '<b>' + fdeTxt(v.client) + '</b><small>' + fdeTxt(v.cid) + '</small>';
    var typeCell = '<span class="etype">' + fdeTxt(v.type) + '</span>';
    var levelCell = badge(v.level, fdeVioLevelColor(v.level)) + (rep > 1 ? '<span class="vio-repeat">第 ' + rep + ' 次</span>' : '');
    var quoteCell = '<div class="fde-wo-analysis"><span>' + fdeTxt(v.quote) + '</span><small>置信度 ' + v.conf + '% · 命中片段</small></div>';
    var stageCell = badge(v.status, fdeVioStatusColor(v.status)) + '<small>' + (v.round ? '第 ' + v.round + ' 轮整改' : (v.status === '已闭环' ? '闭环' : '首次整改')) + (v.urge ? ' · 已催办 ' + v.urge + ' 次' : '') + '</small>';
    var histCell = '<span class="vio-hist-main">销售 ' + (rep > 1 ? '第 ' + rep + ' 次' : '首次') + '</span><small>30 天窗口 · 同类型</small>';
    var dueCell = '<span class="vio-due ' + due.cls + '">' + due.text + '</span><small>' + fdeTxt(v.due ? v.due.slice(5, 16) : '—') + '</small>';
    var acts = fdeClick('详情', "fdeVioOpen('" + v.id + "')", 'link');
    if(v.status === '待认定') acts += fdeClick('认定', "fdeVioGoReview('" + v.id + "')", 'link');
    if(v.status === '整改中') acts += fdeClick('催办', "fdeVioUrge('" + v.id + "')", 'link');
    if(v.status === '待验收') acts += fdeClick('验收', "fdeVioAcceptOpen('" + v.id + "')", 'link');
    if(v.status === '申诉中') acts += fdeClick('复核', "fdeVioGoReview('" + v.id + "')", 'link');
    return [idCell, '<span style="white-space:nowrap">' + fdeTxt(v.time) + '</span>', salesCell, clientCell, typeCell, levelCell, quoteCell, stageCell, histCell, dueCell, acts];
  });
  return table(heads, rows);
}
function fdeVioListView(){
  fdeVioInit();
  var tabs = '<div class="fde-wo-tabs">' + FDE_VIO_PRESETS.map(function(p){
    return '<button class="' + (FDE_VIO.preset === p ? 'active' : '') + '" onclick="fdeVioSetPreset(\'' + p + '\')">' + p + '</button>';
  }).join('') + '</div>';
  var toolbar = '<div class="toolbar">'
    + '<input class="search" id="fdeVioQ" placeholder="搜索客户姓名/编号、销售、违规编号或话术" value="' + fdeTxt(FDE_VIO.keyword) + '" oninput="fdeVioSearch(this.value)">'
    + fdeVioSelect('fdeVioType', ['全部类型'].concat(FDE_VIO_TYPES), FDE_VIO.type, "fdeVioSet('type',this.value)")
    + fdeVioSelect('fdeVioLevel', ['全部','高','中','低'], FDE_VIO.level, "fdeVioSet('level',this.value)")
    + fdeVioSelect('fdeVioTime', ['全部时间','近1天','近3天','近7天','近30天','自定义'], FDE_VIO.time, "fdeVioSet('time',this.value)")
    + '<label class="vio-check"><input type="checkbox" onchange="fdeVioSetRepeat(this.checked)"' + (FDE_VIO.onlyRepeat ? ' checked' : '') + '> 只看重复违规</label>'
    + btn('重置筛选','fdeVioReset()')
    + '</div>';
  if(FDE_VIO.time === '自定义'){
    toolbar += '<div class="vio-daterange"><span class="muted">时间范围</span><input type="date" value="' + fdeTxt(FDE_VIO.from) + '" onchange="fdeVioSetFrom(this.value)"><span class="muted">至</span><input type="date" value="' + fdeTxt(FDE_VIO.to) + '" onchange="fdeVioSetTo(this.value)"></div>';
  }
  var body = fdeVioStats()
    + card('违规记录', toolbar + tabs + '<div id="fdeVioRows">' + fdeVioTable() + '</div>', '<span class="vio-count" id="fdeVioCount">共 ' + fdeVioFiltered().length + ' 条</span>');
  return head('违规列表','记录销售在客户沟通、文字直播、电话录音等场景的违规话术与整改闭环；每条记录可追溯到具体客户，与客诉处置分开管理，不建客户工单。　·　演示时钟 2026-11-14 18:00',btn('导出违规记录','fdeVioExport()'))+body;
}
function fdeVioOpen(id){ fdeVioInit(); FDE_VIO.id = id; FDE_VIO.mode = 'detail'; closeModal(); render(); window.scrollTo(0, 0); }
function fdeVioOpenSales(name){ FDE_VIO.mode = 'list'; FDE_VIO.id = null; FDE_VIO.keyword = name; FDE_VIO.preset = '全部'; FDE_VIO.type = '全部类型'; FDE_VIO.level = '全部'; FDE_VIO.time = '全部时间'; FDE_VIO.from = ''; FDE_VIO.to = ''; FDE_VIO.onlyRepeat = false; closeModal(); render(); window.scrollTo(0, 0); }

function fdeVioGoReview(id){
  var v = fdeVioById(id);
  if(!v) return;
  var inTab = (v.channel === '企微会话' || v.channel === '客户群');
  if(!inTab){
    if(v.status === '待认定') return fdeVioConfirmOpen(id);
    if(v.status === '申诉中') return fdeVioAppealReviewOpen(id);
    return;
  }
  try{
    reviewChannelFilter = '企微会话';
    reviewTypeFilter = '全部';
    reviewLevelFilter = '全部';
    reviewTimeFilter = '全部时间';
    reviewFrom = '';
    reviewTo = '';
  }catch(e){}
  FDE_RV_KIND.kind = '销售违规';
  FDE_RV_VIO.id = id;
  FDE_RV_VIO.tab = 'details';
  closeModal();
  navigate('alerts');
  window.scrollTo(0, 0);
}
function fdeVioBack(){ FDE_VIO.mode = 'list'; FDE_VIO.id = null; closeModal(); render(); window.scrollTo(0, 0); }

/* ---------- 详情 ---------- */
function fdeVioActions(v){
  var out = '';
  if(v.status === '待认定'){
    out += fdeClick('认定违规', "fdeVioGoReview('" + v.id + "')", 'fde-active-btn');
    out += fdeClick('判定误报', "fdeVioFalseOpen('" + v.id + "')");
  }else if(v.status === '整改中'){
    out += fdeClick('催办销售主管', "fdeVioUrge('" + v.id + "')");
  }else if(v.status === '待验收'){
    out += fdeClick('验收 / 退回', "fdeVioAcceptOpen('" + v.id + "')", 'fde-active-btn');
  }else if(v.status === '申诉中'){
    out += fdeClick('合规复核', "fdeVioGoReview('" + v.id + "')", 'fde-active-btn');
  }else if(v.status === '已闭环'){
    out += fdeClick('查看整改档案', "toast('整改档案已归档（演示）')", 'fde-btn');
  }
  return out;
}
function fdeVioDetailView(){
  fdeVioInit();
  var v = fdeVioById(FDE_VIO.id);
  if(!v){ FDE_VIO.mode = 'list'; return fdeVioListView(); }
  var rep = fdeVioRepeat(v), stage = fdeVioStage(v);
  var stages = ['待认定','整改中','待验收','已闭环'];
  var bar = '<div class="toolbar">' + stages.map(function(s, i){
    var n = i + 1;
    return fdePill(n + ' ' + s, n < stage ? 'is-good' : n === stage ? 'is-blue' : '');
  }).join('') + (v.status === '申诉中' ? fdePill('申诉复核中','is-danger') : '') + (v.status === '误报' ? fdePill('误报结案','is-danger') : '')
    + '<span class="muted">当前：' + fdeTxt(v.status) + ' · 整改轮次 ' + (v.round || 0) + ' · 催办 ' + (v.urge || 0) + ' 次</span></div>';
  var tags = '<div class="toolbar">' + badge(v.level, fdeVioLevelColor(v.level)) + (rep > 1 ? '<span class="vio-repeat">第 ' + rep + ' 次触发</span>' : '')
    + '<span class="muted">' + fdeTxt(v.cid) + ' · ' + fdeTxt(v.team) + ' · ' + fdeTxt(v.channel) + '</span></div>';

  var sec1 = card('① 违规事实与证据',
    '<div class="grid equal"><div>'
    + '<h3>结构化命中</h3>'
    + '<div class="vio-kv">'
    + fdeVioKv('违规编号', v.id)
    + fdeVioKv('来源 / 渠道', v.source + ' · ' + v.channel)
    + fdeVioKv('违规时间', v.time)
    + fdeVioKv('销售人员', v.sales + ' · ' + v.team)
    + fdeVioKv('涉及客户', v.client)
    + fdeVioKv('客户编号', v.cid)
    + fdeVioKv('责任主管', v.supervisor || '—')
    + fdeVioKv('违规类型', v.type)
    + fdeVioKv('违规等级', v.level + ' 级' + (rep > 1 ? ' · 第 ' + rep + ' 次' : ''))
    + fdeVioKv('当前阶段', v.status)
    + fdeVioKv('AI 置信度', v.conf + '%')
    + fdeVioKv('命中规则', '销售话术合规（抽检口径）')
    + '</div>'
    + '<h3 style="margin-top:20px">定位原文</h3>'
    + '<div class="vio-quote">' + fdeVioMark(v.quote, v.quote) + '</div>'
    + '<div class="vio-quote-foot">原始话术已锁定，等级修正与整改结论不影响证据原文</div>'
    + '</div><div>'
    + '<h3>原始记录</h3>' + fdeVioEvidence(v)
    + '</div></div>'
  );

  var others = (state.violations || []).filter(function(x){ return x.id !== v.id && x.sales === v.sales; })
    .sort(function(a, b){ return fdeVioTs(b.time) - fdeVioTs(a.time); });
  var hist90 = others.filter(function(x){ return fdeVioTs(x.time) >= FDE_VIO_NOW_TS - 90 * 86400000; }).length;
  var histHigh = others.filter(function(x){ return x.level === '高'; }).length;
  var histCust = {}, histCustN = 0;
  others.forEach(function(x){ if(!histCust[x.cid]){ histCust[x.cid] = 1; histCustN++; } });
  var sameTypeN = (state.violations || []).filter(function(x){ return x.sales === v.sales && x.type === v.type; }).length;
  var histTable = others.length ? table(['时间','客户','违规类型','等级','处置阶段','操作'], others.slice(0, 8).map(function(x){
    var xrep = fdeVioRepeat(x);
    return [
      '<span style="white-space:nowrap">' + fdeTxt(x.time) + '</span>',
      '<b>' + fdeTxt(x.client) + '</b><small>' + fdeTxt(x.cid) + '</small>',
      '<span class="etype">' + fdeTxt(x.type) + '</span>',
      badge(x.level, fdeVioLevelColor(x.level)) + (xrep > 1 ? '<span class="vio-repeat">第 ' + xrep + ' 次</span>' : ''),
      badge(x.status, fdeVioStatusColor(x.status)),
      fdeClick('查看', "fdeVioOpen('" + x.id + "')", 'link')
    ];
  })) : '<div class="muted">该销售暂无其他违规记录</div>';
  var secHist = card('② 销售历史违规',
    '<div class="vio-hsum">'
    + '<div><small>近 90 天其他违规</small><b>' + hist90 + ' 条</b></div>'
    + '<div><small>其中红线</small><b>' + histHigh + ' 条</b></div>'
    + '<div><small>涉及客户</small><b>' + histCustN + ' 位</b></div>'
    + '<div><small>同类型累计（含本次）</small><b>' + v.type + ' ' + sameTypeN + ' 次</b></div>'
    + '</div>'
    + histTable
    + (others.length > 8 ? '<div class="vio-quiet">仅展示最近 8 条，共 ' + others.length + ' 条　' + fdeClick('查看该销售全部记录', "fdeVioOpenSales('" + v.sales + "')", 'link') + '</div>' : ''),
    '<span class="muted">共 ' + others.length + ' 条</span>'
  );


  var sec3 = card('③ 认定与整改轨迹',
    '<div class="timeline">' + (v.logs || []).map(function(l){ return '<div>' + fdeTxt(l) + '</div>'; }).join('') + '</div>'
  );

  var reqState = v.status === '已闭环' ? '已通过' : v.status === '待验收' ? '待核验' : v.status === '待认定' ? '未生效' : '待提交';
  var reqCls = v.status === '已闭环' ? 'is-ok' : v.status === '待验收' ? 'is-wait' : 'is-todo';
  var reqs = (v.reqs || []).map(function(r, i){
    return '<div class="vio-req ' + reqCls + '"><span class="vio-req-no">' + (i + 1) + '</span><span class="vio-req-text">' + fdeTxt(r) + '</span><span class="vio-req-state">' + reqState + '</span></div>';
  }).join('');
  var rec = '';
  if(v.submitNote) rec += '<div class="vio-note"><b>销售整改说明</b><p>' + fdeTxt(v.submitNote) + '</p><small>' + fdeTxt(v.submitAt || '') + '</small></div>';
  if(v.files && v.files.length) rec += '<div class="vio-files">附件：' + v.files.map(fdeTxt).join('、') + '</div>';
  if(v.acceptNote) rec += '<div class="vio-note"><b>风控验收说明</b><p>' + fdeTxt(v.acceptNote) + '</p><small>' + fdeTxt(v.acceptAt || '') + '</small></div>';
  if(!rec) rec = '<div class="muted">暂无提交与验收记录</div>';
  var sec4 = card('④ 整改与验收',
    '<h3>整改要求（认定时冻结）</h3><div class="vio-reqs">' + reqs + '</div>'
    + '<h3 style="margin-top:20px">提交与验收记录</h3>' + rec
    + '<h3 style="margin-top:20px">处罚建议</h3>' + (v.punish ? badge(v.punish, 'orange') : '<span class="muted">验收时填写</span>')
    + '<div class="toolbar" style="margin-top:18px">' + fdeVioActions(v) + '</div>'
  );

  return head('违规详情','违规 ' + fdeTxt(v.id) + ' · ' + fdeTxt(v.type) + ' · ' + fdeTxt(v.client) + '（' + fdeTxt(v.cid) + '）',
      fdeClick('返回列表','fdeVioBack()','fde-active-btn')
      + fdeClick('查看客户会话', "fdeVioClientChat('" + v.cid + "')"))
    + bar + tags + sec1 + secHist + sec3 + sec4;
}

/* ---------- 处置动作 ---------- */
function fdeVioLevelSelect(id, cur){
  return '<select id="' + id + '" onchange="fdeVioSlaByLevel(this.value)">' + ['高','中','低'].map(function(x){
    return '<option' + (x === cur ? ' selected' : '') + '>' + x + '</option>';
  }).join('') + '</select>';
}
function fdeVioSlaByLevel(l){
  var el = $('#vioSla');
  if(el) el.value = l === '高' ? '3' : l === '中' ? '5' : '7';
}
function fdeVioSlaSelect(id, cur){
  var opts = [['3','3 天（高）'],['5','5 天（中）'],['7','7 天（低）']];
  return '<select id="' + id + '">' + opts.map(function(o){
    return '<option value="' + o[0] + '"' + (o[0] === String(cur) ? ' selected' : '') + '>' + o[1] + '</option>';
  }).join('') + '</select>';
}
function fdeVioConfirmOpen(id){
  var v = fdeVioById(id); if(!v) return;
  FDE_VIO.id = id;
  var days = v.level === '高' ? 3 : v.level === '中' ? 5 : 7;
  var body = '<div class="formgrid">'
    + field('违规等级', fdeVioLevelSelect('vioLevel', v.level))
    + field('责任主管', '<input id="vioSup" value="' + fdeTxt(v.supervisor || '') + '">')
    + field('整改期限', fdeVioSlaSelect('vioSla', days))
    + field('整改要求（每行一项）', '<textarea id="vioReqs" style="min-height:96px">' + fdeTxt((v.reqs || []).join('\n')) + '</textarea>', true)
    + field('认定说明 *', '<textarea id="vioReason" placeholder="说明认定依据与适用条款"></textarea>', true)
    + '</div>';
  modal('认定违规 · ' + v.id, body, btn('取消','closeModal()') + btn('确认认定','fdeVioConfirmSave()','primary'), true);
}
function fdeVioConfirmSave(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var reason = required('vioReason'); if(!reason) return;
  var lv = $('#vioLevel').value, days = Number($('#vioSla').value) || 3;
  var sup = $('#vioSup').value.trim();
  var reqs = $('#vioReqs').value.split('\n').map(function(x){ return x.trim(); }).filter(Boolean);
  v.level = lv; v.supervisor = sup; v.reqs = reqs.length ? reqs : fdeVioDefaultReqs(v.type);
  v.status = '整改中'; v.round = 0; v.confirmAt = FDE_VIO_NOW;
  v.due = fdeVioShift(FDE_VIO_NOW, days * 24);
  fdeVioLog(v, '合规认定：' + lv + '级违规，整改期限 ' + v.due.slice(5, 16) + '；' + reason);
  save('违规认定：' + v.id + '（' + lv + '级）');
  closeModal(); render(); toast('已认定，整改期限 ' + v.due.slice(5, 16));
}
function fdeVioFalseOpen(id){
  var v = fdeVioById(id); if(!v) return;
  FDE_VIO.id = id;
  var body = '<div class="notice">判定误报后，该记录不纳入销售考核与整改，但保留原始证据与操作轨迹。</div>'
    + field('误报原因 *', '<textarea id="vioFalse" placeholder="说明证据不足或误判原因"></textarea>', true);
  modal('判定误报 · ' + v.id, body, btn('取消','closeModal()') + btn('确认误报','fdeVioFalseSave()','primary'), true);
}
function fdeVioFalseSave(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var reason = required('vioFalse'); if(!reason) return;
  v.status = '误报'; v.falseReason = reason; v.due = ''; v.closedAt = FDE_VIO_NOW;
  fdeVioLog(v, '合规复核判定误报：' + reason);
  save('违规判定误报：' + v.id);
  closeModal(); render(); toast('已判定误报，记录不纳入考核');
}
function fdeVioUrge(id){
  var v = fdeVioById(id); if(!v) return;
  v.urge = Number(v.urge || 0) + 1;
  fdeVioLog(v, '已催办销售主管' + (v.supervisor ? ' ' + v.supervisor : '') + '（第 ' + v.urge + ' 次）');
  save('催办违规整改：' + v.id);
  render(); toast('已发送催办（第 ' + v.urge + ' 次）');
}
function fdeVioSubmitOpen(id){
  var v = fdeVioById(id); if(!v) return;
  FDE_VIO.id = id;
  var body = '<div class="formgrid">'
    + field('整改说明 *', '<textarea id="vioSubmitNote" placeholder="说明整改措施、完成情况与客户沟通结果"></textarea>', true)
    + '<div class="vio-checkgroup"><div class="vio-checkgroup-title">整改要求完成情况</div>'
    + (v.reqs || []).map(function(r, i){ return '<label class="vio-chk"><input type="checkbox" id="vioReq' + i + '" checked> ' + fdeTxt(r) + '</label>'; }).join('')
    + '</div>'
    + field('提交材料', '<input id="vioFiles" value="整改说明.pdf、培训签到记录.png">', true)
    + '</div>';
  modal('模拟销售提交整改 · ' + v.id, body, btn('取消','closeModal()') + btn('提交并进入验收','fdeVioSubmitSave()','primary'), true);
}
function fdeVioSubmitSave(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var note = required('vioSubmitNote'); if(!note) return;
  var all = true;
  (v.reqs || []).forEach(function(r, i){ var el = $('#vioReq' + i); if(!el || !el.checked) all = false; });
  if(!all) return toast('请确认全部整改要求已完成');
  v.status = '待验收'; v.submitNote = note; v.submitAt = FDE_VIO_NOW;
  v.files = String($('#vioFiles').value || '').split('、').map(function(x){ return x.trim(); }).filter(Boolean);
  v.due = fdeVioShift(FDE_VIO_NOW, 24);
  fdeVioLog(v, '销售提交整改材料，进入待验收' + (v.files.length ? '（' + v.files.join('、') + '）' : ''));
  save('提交违规整改：' + v.id);
  closeModal(); render(); toast('整改材料已提交，等待风控验收');
}
function fdeVioAcceptOpen(id){
  var v = fdeVioById(id); if(!v) return;
  FDE_VIO.id = id;
  var body = '<div class="formgrid">'
    + '<div class="vio-checkgroup"><div class="vio-checkgroup-title">逐项核验整改要求</div>'
    + (v.reqs || []).map(function(r, i){ return '<label class="vio-chk"><input type="checkbox" id="vioOk' + i + '" checked> ' + fdeTxt(r) + '</label>'; }).join('')
    + '</div>'
    + field('处罚建议', '<select id="vioPunish"><option>警告</option><option>合规培训</option><option>扣分</option><option>暂停展业</option><option>不处罚</option></select>')
    + field('验收说明 *', '<textarea id="vioAcceptNote" placeholder="填写核验结论或退回原因"></textarea>', true)
    + '</div>';
  modal('验收 / 退回 · ' + v.id, body, btn('取消','closeModal()') + btn('退回整改','fdeVioReturnSave()','danger') + btn('验收通过','fdeVioAcceptSave()','primary'), true);
}
function fdeVioAcceptSave(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var note = required('vioAcceptNote'); if(!note) return;
  var all = true;
  (v.reqs || []).forEach(function(r, i){ var el = $('#vioOk' + i); if(!el || !el.checked) all = false; });
  if(!all) return toast('整改要求未全部通过，请退回整改');
  v.status = '已闭环'; v.acceptNote = note; v.acceptAt = FDE_VIO_NOW; v.closedAt = FDE_VIO_NOW;
  v.punish = $('#vioPunish').value; v.due = '';
  fdeVioLog(v, '风控验收通过，已闭环（' + v.punish + '）；' + note);
  save('违规验收通过：' + v.id);
  closeModal(); render(); toast('验收通过，已闭环');
}
function fdeVioReturnSave(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var note = required('vioAcceptNote'); if(!note) return;
  var days = v.level === '高' ? 3 : v.level === '中' ? 5 : 7;
  v.status = '整改中'; v.round = Number(v.round || 0) + 1;
  v.acceptNote = ''; v.due = fdeVioShift(FDE_VIO_NOW, days * 24);
  fdeVioLog(v, '风控退回整改（第 ' + v.round + ' 轮）：' + note);
  save('退回违规整改：' + v.id);
  closeModal(); render(); toast('已退回整改，整改期限 ' + v.due.slice(5, 16));
}
function fdeVioAppealOpen(id){
  var v = fdeVioById(id); if(!v) return;
  FDE_VIO.id = id;
  if(v.status !== '整改中') return toast('当前状态不支持申诉');
  var body = '<div class="notice">申诉期间暂停整改计时，合规复核后维持原结论或撤销记录。</div>'
    + field('申诉原因 *', '<textarea id="vioAppeal" placeholder="说明申诉理由与证据"></textarea>', true);
  modal('提交申诉 · ' + v.id, body, btn('取消','closeModal()') + btn('提交申诉','fdeVioAppealSave()','primary'), true);
}
function fdeVioAppealSave(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var reason = required('vioAppeal'); if(!reason) return;
  v.prevStatus = v.status; v.status = '申诉中'; v.appeal = reason; v.appealAt = FDE_VIO_NOW;
  fdeVioLog(v, '销售提交申诉：' + reason);
  save('违规申诉：' + v.id);
  closeModal(); render(); toast('申诉已提交，等待合规复核');
}
function fdeVioAppealReviewOpen(id){
  var v = fdeVioById(id); if(!v) return;
  FDE_VIO.id = id;
  var body = '<div class="vio-note"><b>申诉原因</b><p>' + fdeTxt(v.appeal || '—') + '</p><small>' + fdeTxt(v.appealAt || '') + '</small></div>'
    + field('复核说明 *', '<textarea id="vioReviewNote" placeholder="填写复核依据"></textarea>', true);
  modal('合规复核 · ' + v.id, body, btn('取消','closeModal()') + btn('撤销记录','fdeVioAppealDrop()','danger') + btn('维持原结论','fdeVioAppealKeep()','primary'), true);
}
function fdeVioAppealKeep(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var note = required('vioReviewNote'); if(!note) return;
  v.status = v.prevStatus || '整改中'; v.due = v.due || fdeVioShift(FDE_VIO_NOW, 48);
  fdeVioLog(v, '申诉复核：维持原结论；' + note);
  save('申诉复核维持：' + v.id);
  closeModal(); render(); toast('已维持原结论');
}
function fdeVioAppealDrop(){
  var v = fdeVioById(FDE_VIO.id); if(!v) return;
  var note = required('vioReviewNote'); if(!note) return;
  v.status = '误报'; v.falseReason = '申诉复核撤销：' + note; v.due = ''; v.closedAt = FDE_VIO_NOW;
  fdeVioLog(v, '申诉复核：撤销记录；' + note);
  save('申诉撤销违规记录：' + v.id);
  closeModal(); render(); toast('已撤销记录，不纳入考核');
}

/* ---------- 客户会话深链 ---------- */
function fdeVioClientChat(cid){
  var hit = null;
  try{
    (fdeArcData().sales || []).forEach(function(s){
      (s.accounts || []).forEach(function(a){
        (a.clients || []).forEach(function(c){ if(c.cid === cid) hit = {sales:s.name, acc:a.id, cid:cid}; });
      });
    });
  }catch(e){}
  if(hit){
    FDE.arc.sales = hit.sales; FDE.arc.acc = hit.acc; FDE.arc.cid = hit.cid;
    FDE.arc.kwSales = ''; FDE.arc.kwAcc = ''; FDE.arc.kwClient = ''; FDE.arc.kwMsg = ''; FDE.arc.kwChat = '';
    FDE.arc.evType = '全部'; FDE.arc.level = '全部'; FDE.arc.time = '全部时间'; FDE.arc.msgType = '全部'; FDE.arc.risk = '全部'; FDE.arc.showAll = false; FDE.arc.tab = 'client';
  }
  closeModal(); navigate('archive');
  if(!hit) toast('该客户暂无会话档案');
}
/* ---------- 导出 ---------- */
function fdeVioExport(){
  var list = fdeVioFiltered();
  var head = ['违规编号','违规时间','销售','团队','主管','客户','客户编号','渠道','来源','违规类型','违规等级','重复次数','处置阶段','整改轮次','整改时限'];
  var lines = [head.join(',')].concat(list.map(function(v){
    return [v.id, v.time, v.sales, v.team, v.supervisor || '', v.client, v.cid, v.channel, v.source, v.type, v.level, fdeVioRepeat(v), v.status, v.round || 0, v.due || ''].join(',');
  }));
  var blob = new Blob(['\ufeff' + lines.join('\n')], {type:'text/csv;charset=utf-8'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '销售违规记录_演示.csv';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('违规记录已导出（演示）');
}

/* ===================== 预警与复核：销售违规二级 Tab ===================== */
var FDE_RV_KIND = {kind:'客诉风险'};
var FDE_RV_VIO = {id:null, tab:'details', typeFilter:'全部'};
var FDE_RV_VIO_TYPES = ['承诺收益','违规荐股','代客操作','返佣飞单','夸大宣传','泄露信息','不当言辞','未揭示风险'];

function fdeRvVioDate(t){
  var m = String(t || '').match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}
function fdeRvVioTimeOk(t){
  var rng = reviewTimeRange();
  if(!rng) return true;
  var d = fdeRvVioDate(t);
  if(!d) return false;
  if(rng.from && d < rng.from) return false;
  if(rng.to && d > rng.to) return false;
  return true;
}
function fdeRvVioTypes(){
  return FDE_RV_VIO_TYPES.slice();
}
function fdeRvVioList(){
  var tf = FDE_RV_VIO.typeFilter || '全部';
  if(tf !== '全部' && FDE_RV_VIO_TYPES.indexOf(tf) < 0) tf = '全部';
  return (state.violations || []).filter(function(v){
    if(v.status !== '待认定' && v.status !== '申诉中') return false;
    if(v.channel !== '企微会话' && v.channel !== '客户群') return false;
    if(tf !== '全部' && v.type !== tf) return false;
    return fdeRvVioTimeOk(v.time);
  }).sort(function(a, b){
    var oa = a.level === '高' ? 0 : a.level === '中' ? 1 : 2;
    var ob = b.level === '高' ? 0 : b.level === '中' ? 1 : 2;
    if(oa !== ob) return oa - ob;
    return fdeVioTs(b.time) - fdeVioTs(a.time);
  });
}
function fdeRvKindCounts(){
  var kf = reviewFilteredEvents().filter(function(e){ return fdeRVChannel(e) === '企微会话'; }).length;
  var list = fdeRvVioList();
  return {
    kf:kf,
    vio:list.length,
    pending:list.filter(function(v){ return v.status === '待认定'; }).length,
    appeal:list.filter(function(v){ return v.status === '申诉中'; }).length
  };
}
function fdeRvKindTabs(){
  if(reviewChannelFilter !== '企微会话'){
    return '<div class="rv-kinds"><div class="rv-kind is-on is-static">客诉风险 <b>' + reviewFilteredEvents().length + '</b></div></div>';
  }
  var c = fdeRvKindCounts();
  var q = FDE_LIVE_Q;
  function tab(k, n){
    var on = FDE_RV_KIND.kind === k;
    return '<div class="rv-kind' + (on ? ' is-on' : '') + '" role="tab" tabindex="0" aria-selected="' + on + '" onclick="fdeRvSetKind(' + q + k + q + ')">' + k + ' <b>' + n + '</b></div>';
  }
  return '<div class="rv-kinds" role="tablist" aria-label="按风险类型复核">' + tab('客诉风险', c.kf) + tab('销售违规', c.vio) + '</div>';
}
function fdeRvSetKind(k){
  if(['客诉风险','销售违规'].indexOf(k) < 0) return;
  FDE_RV_KIND.kind = k;
  FDE_RV_VIO.id = null;
  FDE_RV_VIO.tab = 'details';
  render();
}
function fdeRvVioSelect(id){
  FDE_RV_VIO.id = id;
  FDE_RV_VIO.tab = 'details';
  render();
}

function fdeRvVioTypeSet(v){
  FDE_RV_VIO.typeFilter = (v === '全部' || FDE_RV_VIO_TYPES.indexOf(v) >= 0) ? v : '全部';
  FDE_RV_VIO.id = null;
  FDE_RV_VIO.tab = 'details';
  render();
}
function fdeRvFilterActive(){
  if(reviewChannelFilter === '企微会话' && FDE_RV_KIND.kind === '销售违规'){
    return (FDE_RV_VIO.typeFilter || '全部') !== '全部' || reviewTimeFilter !== '全部时间';
  }
  return reviewTypeFilter !== '全部' || reviewLevelFilter !== '全部' || reviewTimeFilter !== '全部时间';
}
function fdeRvReset(){
  if(reviewChannelFilter === '企微会话' && FDE_RV_KIND.kind === '销售违规'){
    FDE_RV_VIO.typeFilter = '全部';
    FDE_RV_VIO.id = null;
    FDE_RV_VIO.tab = 'details';
  }else{
    reviewTypeFilter = '全部';
    reviewLevelFilter = '全部';
    reviewDetailTab = 'details';
  }
  reviewTimeFilter = '全部时间';
  reviewFrom = '';
  reviewTo = '';
  render();
}
function fdeRvTimeSelect(){
  var times = ['全部时间','近1天','近3天','近7天','近30天','自定义'];
  return '<span class="rv-time"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M12 7.5V12l3 1.8"></path></svg>'
    + '<select aria-label="事件时间范围筛选" onchange="reviewTimeSet(this.value)">'
    + times.map(function(v){ return '<option value="' + fdeTxt(v) + '"' + (reviewTimeFilter === v ? ' selected' : '') + '>' + fdeTxt(v) + '</option>'; }).join('')
    + '</select></span>';
}
function fdeRvDateRange(){
  return '<div class="rv-dates"><input type="date" aria-label="开始日期" title="开始日期" value="' + fdeTxt(reviewFrom) + '" onchange="reviewTimeFrom(this.value)">'
    + '<span>至</span><input type="date" aria-label="结束日期" title="结束日期" value="' + fdeTxt(reviewTo) + '" onchange="reviewTimeTo(this.value)"></div>';
}
function fdeRvContextFilter(){
  if(FDE_RV_KIND.kind === '销售违规'){
    var cur = FDE_RV_VIO.typeFilter || '全部';
    return '<label class="rv-filter"><span>违规类型</span><select aria-label="销售违规类型筛选" onchange="fdeRvVioTypeSet(this.value)">'
      + ['全部'].concat(fdeRvVioTypes()).map(function(v){ return '<option value="' + fdeTxt(v) + '"' + (cur === v ? ' selected' : '') + '>' + (v === '全部' ? '全部类型' : fdeTxt(v)) + '</option>'; }).join('')
      + '</select></label>';
  }
  var level = reviewLevelFilter || '全部';
  return '<label class="rv-filter"><span>风险等级</span><select aria-label="风险等级筛选" onchange="reviewFilterChange(\'level\',this.value)">'
    + ['全部'].concat(reviewLevelsFor(reviewTypeFilter)).map(function(v){ return '<option value="' + fdeTxt(v) + '"' + (level === v ? ' selected' : '') + '>' + (v === '全部' ? '全部等级' : v === '—' ? '未定级' : fdeTxt(v)) + '</option>'; }).join('')
    + '</select></label>';
}
function fdeRvHeader(){
  var dates = reviewTimeFilter === '自定义' ? fdeRvDateRange() : '';
  return '<div class="rv-head">'
    + '<div class="rv-head-row"><div class="rv-head-left">' + fdeRVChannelTabs() + '</div><div class="rv-head-right">' + fdeRvTimeSelect() + dates + '</div></div>'
    + '<div class="rv-head-row rv-head-row2"><div class="rv-head-left">' + fdeRvKindTabs() + fdeRvContextFilter()
    + (fdeRvFilterActive() ? '<button type="button" class="rv-reset" onclick="fdeRvReset()">↺ 重置</button>' : '') + '</div></div>'
    + '</div>';
}

function fdeRvVioSetTab(t){
  FDE_RV_VIO.tab = (t === 'history' || t === 'sales') ? t : 'details';
  render();
}
function fdeRvVioActions(v){
  if(v.status === '待认定'){
    return '<div class="review-disposition"><div class="review-disposition-title"><b>人工复核结论</b>' + badge(v.status) + '</div>'
      + '<div class="review-disposition-actions">'
      + btn('认定违规', "fdeVioConfirmOpen('" + v.id + "')", 'primary')
      + btn('判定误报', "fdeVioFalseOpen('" + v.id + "')")
      + '</div><small class="muted">认定后进入销售整改流程 · 证据不足请判误报</small></div>';
  }
  if(v.status === '申诉中'){
    return '<div class="review-disposition"><div class="review-disposition-title"><b>申诉复核</b>' + badge(v.status) + '</div>'
      + '<div class="review-disposition-actions">' + btn('合规复核', "fdeVioAppealReviewOpen('" + v.id + "')", 'primary') + '</div>'
      + '<small class="muted">维持原结论或撤销违规记录</small></div>';
  }
  return '';
}
function fdeRvVioDetail(v){
  var sameTypeN = (state.violations || []).filter(function(x){ return x.sales === v.sales && x.type === v.type; }).length;
  var html = '<div class="review-event-id">' + fdeTxt(v.id) + '</div>'
    + '<div class="meta">来源：' + fdeTxt(v.source) + ' · ' + fdeTxt(v.channel) + ' · ' + fdeTxt(v.time) + '</div>'
    + '<section class="review-risk-card"><div class="meta">△ AI 销售违规提示</div>'
    + '<div class="review-risk-title">' + badge(v.level, fdeVioLevelColor(v.level)) + ' ' + fdeTxt(v.type) + badge(v.status, v.status === '申诉中' ? 'orange' : 'blue') + '</div>'
    + '<p>' + fdeTxt(v.quote) + '</p>'
    + '<div class="review-result-pair"><span>置信度 <b>' + v.conf + '%</b></span><span>同类型累计 <b>' + sameTypeN + ' 次</b></span></div>'
    + '</section>'
    + '<section class="review-human-card"><small>人工结论</small><p>'
    + (v.status === '申诉中' ? '销售已发起申诉，等待质检复核' : '尚未认定，等待质检复核')
    + '</p>' + (v.status === '申诉中' && v.appeal ? '<div class="notice">申诉原因：' + fdeTxt(v.appeal) + '</div>' : '')
    + '</section>'
    + '<section class="review-rule-card"><small>命中口径</small><h3>销售话术合规（抽检口径）</h3><p>依据识别时证据快照核查 · 质检责任人：周敏</p></section>';
  return html;
}
function fdeRvVioSalesHistory(v){
  var rep = fdeVioRepeat(v);
  var sameTypeN = (state.violations || []).filter(function(x){ return x.sales === v.sales && x.type === v.type; }).length;
  var others = (state.violations || []).filter(function(x){ return x.id !== v.id && x.sales === v.sales; });
  var histHigh = others.filter(function(x){ return x.level === '高'; }).length;
  return '<h3>历史违规</h3>'
    + '<section class="review-rule-card"><small>该销售历史</small><p>其他违规 <b>' + others.length + '</b> 条 · 红线 <b>' + histHigh + '</b> 条 · 同类型累计 <b>' + sameTypeN + '</b> 次</p>'
    + (rep > 1 ? '<p class="muted">本次为该销售同类型第 ' + rep + ' 次触发</p>' : '') + '</section>';
}
function fdeRvVioWorkspace(){
  var list = fdeRvVioList();
  var cur = null;
  for(var i = 0; i < list.length; i++){ if(list[i].id === FDE_RV_VIO.id){ cur = list[i]; break; } }
  if(!cur) cur = list[0] || null;
  FDE_RV_VIO.id = cur ? cur.id : null;
  var pending = list.filter(function(v){ return v.status === '待认定'; }).length;
  var appeal = list.filter(function(v){ return v.status === '申诉中'; }).length;
  var hasFilter = (FDE_RV_VIO.typeFilter || '全部') !== '全部' || reviewTimeFilter !== '全部时间';
  var q = FDE_LIVE_Q;
  var left = '<section class="review-queue"><div class="review-column-head"><b>违规预警 <span class="review-count">' + list.length + '</span></b><span class="muted">待认定 ' + pending + ' · 申诉 ' + appeal + '</span></div>'
    + '<div class="review-queue-scroll">'
    + (list.length ? list.map(function(v){
        var r = fdeVioRepeat(v);
        return '<button class="review-queue-item ' + (cur && cur.id === v.id ? 'active' : '') + (r >= 3 ? ' is-repeat' : '') + '" aria-pressed="' + (cur && cur.id === v.id) + '" onclick="fdeRvVioSelect(' + q + v.id + q + ')">'
          + '<div class="review-queue-badges">' + badge(v.channel, 'blue') + badge(v.level, fdeVioLevelColor(v.level)) + (r > 1 ? '<span class="vio-repeat">第 ' + r + ' 次</span>' : '') + badge(v.status, v.status === '申诉中' ? 'orange' : 'blue') + '</div>'
          + '<h3>' + fdeTxt(v.type) + '</h3>'
          + '<div class="review-queue-person">' + fdeTxt(v.sales) + ' → ' + fdeTxt(v.client) + ' · ' + fdeTxt(v.team) + '</div>'
          + '<p>' + fdeTxt(v.quote) + '</p>'
          + '<div class="meta">' + fdeTxt(v.time) + '　·　' + fdeTxt(v.source) + '</div></button>';
      }).join('') : '<div class="empty">' + (hasFilter
        ? '当前筛选下没有销售违规<p class="muted">调整违规类型或时间范围</p><p>' + btn('重置筛选','fdeRvReset()','link') + '</p>'
        : '✓ 当前销售违规已全部复核<p class="muted">可切换到「客诉风险」继续处理</p>') + '</div>')
    + '</div><div class="review-column-foot">仅企微会话 / 客户群来源 · 按等级与时间排序</div></section>';
  var center = '<section class="review-chat">'
    + (cur
      ? '<div class="review-column-head"><div><h3>' + fdeTxt(cur.client) + ' 与 ' + fdeTxt(cur.sales) + '</h3><div class="meta">' + fdeTxt(cur.team) + ' · ' + fdeTxt(cur.channel) + ' · ' + fdeTxt(cur.cid) + '</div></div></div>'
        + '<div class="review-chat-subhead"><span>▣ 原始会话记录</span><span>证据快照 · ' + fdeTxt(cur.time) + '</span></div>'
        + '<div class="review-chat-scroll">' + fdeVioEvidence(cur) + '</div>'
        + '<div class="review-column-foot">保留原始消息顺序与发送人身份 · 识别快照不随最新状态覆盖</div>'
      : '<div class="empty">暂无待复核的销售违规<p class="muted">切换到「客诉风险」查看客诉预警</p></div>')
    + '</section>';
  var right = '<section class="review-details">'
    + (cur
      ? '<div class="rv-vio-tabs" role="tablist" aria-label="复核内容">'
        + '<div role="tab" tabindex="0" aria-selected="' + (FDE_RV_VIO.tab === 'details') + '" class="rv-vio-tab' + (FDE_RV_VIO.tab === 'details' ? ' active' : '') + '" onclick="fdeRvVioSetTab(' + q + 'details' + q + ')">复核详情</div>'
        + '<div role="tab" tabindex="0" aria-selected="' + (FDE_RV_VIO.tab === 'history') + '" class="rv-vio-tab' + (FDE_RV_VIO.tab === 'history' ? ' active' : '') + '" onclick="fdeRvVioSetTab(' + q + 'history' + q + ')">处理轨迹</div>'
        + '<div role="tab" tabindex="0" aria-selected="' + (FDE_RV_VIO.tab === 'sales') + '" class="rv-vio-tab' + (FDE_RV_VIO.tab === 'sales' ? ' active' : '') + '" onclick="fdeRvVioSetTab(' + q + 'sales' + q + ')">历史违规</div></div>'
        + '<div class="review-details-scroll">'
        + (FDE_RV_VIO.tab === 'history'
          ? '<h3>处理轨迹</h3><div class="timeline">' + (cur.logs || []).map(function(l){ return '<div>' + fdeTxt(l) + '</div>'; }).join('') + '</div>'
          : FDE_RV_VIO.tab === 'sales'
            ? fdeRvVioSalesHistory(cur)
            : fdeRvVioDetail(cur))
        + '</div>' + fdeRvVioActions(cur)
      : '<div class="empty">暂无复核内容<p class="muted">选择左侧违规预警查看证据并作出结论</p></div>')
    + '</section>';
  return '<div class="review-workspace">' + left + center + right + '</div>';
}

var fdeRvPrevChannelTabs = fdeRVChannelTabs;
fdeRVChannelTabs = function(){
  var html = fdeRvPrevChannelTabs();
  var n = fdeRvVioList().length;
  if(!n) return html;
  return html.replace(/企微会话 <b>(\d+)<\/b>/, function(m, c){ return '企微会话 <b>' + (Number(c) + n) + '</b>'; });
};

var fdeRvPrevReview = review;
review = function(){
  if(reviewChannelFilter === '全部' || fdeRVChannelList().indexOf(reviewChannelFilter) < 0) reviewChannelFilter = '企微会话';
  if(reviewChannelFilter !== '企微会话') FDE_RV_KIND.kind = '客诉风险';
  reviewTypeFilter = '全部';
  if(reviewLevelFilter !== '全部' && reviewLevelsFor('全部').indexOf(reviewLevelFilter) < 0) reviewLevelFilter = '全部';
  if(reviewChannelFilter === '企微会话' && FDE_RV_KIND.kind === '销售违规'){
    return head('预警与复核','销售违规线索由 AI 识别后进入待认定；质检复核后进入整改、申诉与验收闭环。',btn('查看违规列表',"navigate('violations')"))
      + fdeRvHeader() + fdeRvVioWorkspace();
  }
  var html = String(fdeRvPrevReview());
  var replaced = false;
  html = html.replace(/<div class="review-topbar">[\s\S]*?(?=<div class="review-workspace">)/, function(){ replaced = true; return fdeRvHeader(); });
  if(!replaced) html = html.replace('<div class="review-workspace">', fdeRvHeader() + '<div class="review-workspace">');
  return html;
};

/* ---------- 预警与复核：右侧风险结论与列表口径一致 ---------- */
var fdeRvPrevReviewDetailContent = reviewDetailContent;
reviewDetailContent = function(e){
  if(reviewDetailTab !== 'details' || !e) return fdeRvPrevReviewDetailContent(e);
  var ai = (e.aiLevel != null ? e.aiLevel : e.level) || '—';
  var lv = (e.level != null ? e.level : ai) || '—';
  var score = (e.aiScore != null ? e.aiScore : e.score);
  var batch = state.batchReports ? state.batchReports.find(function(b){ return (b.ids || []).indexOf(e.id) >= 0; }) : null;
  var nameMap = { T0:'外诉风险', T1:'内诉风险', T2:'退款风险', T3:'抱怨风险' };
  var riskName = e.risk || nameMap[lv] || '';
  return '<div class="review-event-id">' + esc(e.id) + '</div>'
    + '<div class="meta">来源：' + esc(fdeRVChannel(e)) + ' · ' + esc(e.source) + (batch ? ' · ' + esc(batch.id) : '') + '</div>'
    + fdeLevelTrace(e, true)
    + '<section class="review-risk-card"><div class="meta">△ 风险结论</div>'
    + '<div class="review-risk-title">' + (lv === '—' ? '低置信度 · 待核查' : esc(lv) + ' ' + esc(riskName)) + badge(e.status) + '</div>'
    + '<p>' + (lv === '—' ? '当前未命中明确风险，置信度低于复核阈值，请结合上下文核查。' : '请结合客户诉求、完整上下文与业务资料核查，最终以人工结论为准。') + '</p>'
    + '<div class="review-result-pair"><span>AI 原始评分 <b>' + (score == null ? '不评分' : score + ' 分') + '</b></span><span>置信度 <b>' + (e.conf == null ? '—' : e.conf + '%') + '</b></span></div>'
    + '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:12px">' + btn('◎ 定位原文','reviewLocateHit()','link') + btn('修正等级 / 评分', "correct('" + e.id + "')", 'link') + '</div></section>'
    + '<section class="review-rule-card"><small>命中风控规则</small><h3>' + esc(e.rule) + '</h3><p class="muted">' + (lv === '—' ? '因置信度不足进入复核' : '依据识别时证据快照核查') + ' · 风控责任人：' + esc(supervisorOwnerFor(e) || '未分配') + '</p>' + btn('查看事件完整依据', "openEvent('" + e.id + "')", 'link') + '</section>'
    + '<h3>业务证据链</h3>' + business(e);
};

/* ---------- 导航 / 路由 / 图标 ---------- */
(function(){
  var g = navGroups.filter(function(x){ return x[0] === '风险处理'; })[0];
  if(g && !g[1].some(function(x){ return x[0] === 'violations'; })) g[1].push(['violations','⚑','违规列表']);
})();

var fdeVioPrevRender = render;
render = function(){
  if(typeof page === 'undefined' || page !== 'violations') return fdeVioPrevRender();
  fdeVioInit();
  var count = state.events.filter(function(e){ return e.status === '待确认'; }).length;
  var bell = $('#bell'); if(bell) bell.innerText = count;
  $('#nav').innerHTML = navGroups.map(function(g){
    return '<div class="navgroup">' + g[0] + '</div>' + g[1].map(function(it){
      return '<button class="navbtn ' + (page === it[0] ? 'active' : '') + '" onclick="navigate(\'' + it[0] + '\')"><i>' + it[1] + '</i><label>' + it[2] + '</label>' + (it[0] === 'alerts' && count ? '<span>' + count + '</span>' : '') + '</button>';
    }).join('');
  }).join('');
  $('#breadcrumb').innerText = FDE_VIO.mode === 'detail' ? '违规列表 / 违规详情' : '违规列表';
  $('#app').innerHTML = (FDE_VIO.mode === 'detail' ? fdeVioDetailView() : fdeVioListView())
    + '<div class="bottomnote">合规工作台　｜　违规列表 · 全部为虚构演示数据</div>';
};

var fdeVioPrevNavigate = navigate;
navigate = function(p, arg){
  if(p === 'violations'){ FDE_VIO.mode = 'list'; FDE_VIO.id = null; }
  return fdeVioPrevNavigate(p, arg);
};

/* 侧栏图标：React/AntD Menu 按 key 查表，新 key 需补 warning 图标 */
(function(){
  var SVG = '<svg viewBox="64 64 896 896" focusable="false" data-icon="warning" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm-32 232c0-4.4 3.6-8 8-8h48c4.4 0 8 3.6 8 8v272c0 4.4-3.6 8-8 8h-48c-4.4 0-8-3.6-8-8V296zm32 440a48.01 48.01 0 010-96 48.01 48.01 0 010 96z"/></svg>';
  function apply(){
    var doc = window.document || document;
    var li = doc.querySelector('.ant-menu-item[data-menu-id$="-violations"]');
    if(!li || li.querySelector('.ant-menu-item-icon')) return;
    var span = doc.createElement('span');
    span.className = 'anticon anticon-warning ant-menu-item-icon';
    span.setAttribute('role','img');
    span.setAttribute('aria-label','warning');
    span.innerHTML = SVG;
    li.insertBefore(span, li.firstChild);
  }
  var tries = 0;
  (function tick(){ try{ apply(); }catch(e){} if(++tries < 60) setTimeout(tick, 150); })();
  try{ new MutationObserver(function(){ try{ apply(); }catch(e){} }).observe(document.documentElement, {childList:true, subtree:true}); }catch(e){}
})();


fdeVioInit();
