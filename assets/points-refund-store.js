(function (global) {
  'use strict';

  var STORAGE_KEY = 'xingzao_points_refund_prototype_v1';
  var COMMERCIAL_KEY = 'xingzao_commercial_prototype_v1';
  var CURRENT_USER = { id: 'u_wang_xiaoming', name: '王晓明' };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function isValidImageDataUrl(value) {
    var match = /^data:image\/(jpeg|png|webp);base64,([A-Za-z0-9+/]+={0,2})$/i.exec(String(value || ''));
    return !!(match && match[2].length % 4 === 0);
  }

  function isValidDemoAssetPath(value) {
    return /^assets\/refund-demo-(lipsync|hand)\.jpg$/.test(String(value || ''));
  }

  function normalizeAttachments(items) {
    return (Array.isArray(items) ? items : []).slice(0, 3).filter(function (item) {
      return item && (isValidImageDataUrl(item.dataUrl) || isValidDemoAssetPath(item.assetPath));
    }).map(function (item) {
      return {
        id: /^[A-Za-z0-9_-]+$/.test(String(item.id || '')) ? String(item.id) : makeId('ATT-'),
        name: String(item.name || '问题截图'),
        type: String(item.type || 'image/jpeg'),
        size: Math.max(0, Number(item.size) || 0),
        originalType: String(item.originalType || item.type || 'image/jpeg'),
        originalSize: Math.max(0, Number(item.originalSize) || Number(item.size) || 0),
        dataUrl: isValidImageDataUrl(item.dataUrl) ? String(item.dataUrl) : '',
        assetPath: isValidDemoAssetPath(item.assetPath) ? String(item.assetPath) : ''
      };
    });
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function addDays(value, days) {
    var date = new Date(value);
    date.setDate(date.getDate() + days);
    return date;
  }

  function addBusinessDay(value) {
    var date = new Date(value);
    do { date.setDate(date.getDate() + 1); } while (date.getDay() === 0 || date.getDay() === 6);
    return date;
  }

  function formatDateTime(value) {
    if (!value) return '—';
    var date = new Date(value);
    if (isNaN(date.getTime())) return value;
    return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0') + ' ' + String(date.getHours()).padStart(2, '0') + ':' + String(date.getMinutes()).padStart(2, '0');
  }

  function makeId(prefix) {
    return prefix + Date.now() + String(Math.floor(Math.random() * 1000)).padStart(3, '0');
  }

  function charge(type, label, points, batchId, expiresAt) {
    return {
      id: makeId('CHG-'),
      type: type,
      label: label,
      points: points,
      refundablePoints: points,
      deductions: [{ batchId: batchId || 'CB-0720', points: points, originalExpiresAt: expiresAt || '2026-08-20T10:00:00+08:00' }]
    };
  }

  function demoAttachments() {
    return [
      { id:'ATT-DEMO-LIPSYNC', name:'口型异常截图.jpg', type:'image/jpeg', size:36899, originalType:'image/jpeg', originalSize:36899, assetPath:'assets/refund-demo-lipsync.jpg' },
      { id:'ATT-DEMO-HAND', name:'手部异常截图.jpg', type:'image/jpeg', size:37946, originalType:'image/jpeg', originalSize:37946, assetPath:'assets/refund-demo-hand.jpg' }
    ];
  }

  function seededApplication(overrides) {
    var base = {
      id: 'RA202607270001',
      tenantId: 't001',
      tenantName: '雨虹投资',
      videoKey: 'director:5',
      sourceTaskId: 'BATCH-INSURANCE',
      sourceSubTaskId: 5,
      taskTitle: '生成中_保险配置攻略',
      videoTitle: '重大疾病保险的保额建议设置为年收入的3-5倍',
      applicantId: CURRENT_USER.id,
      applicantName: CURRENT_USER.name,
      reasonCode: 'lip_sync',
      reasonLabel: '口型 / 音画不同步',
      description: '12秒附近口型与台词明显不同步，人物嘴部有短暂变形。',
      issueTime: '00:12',
      requestedPoints: 28,
      chargeSnapshot: [
        charge('first_frame', '首帧生成', 10),
        charge('video', '视频生成', 18)
      ],
      deliverySnapshot: [],
      status: 'pending',
      submittedAt: '2026-07-27T10:20:00+08:00',
      dueAt: '2026-07-28T10:20:00+08:00',
      reviewedAt: null,
      reviewer: null,
      reviewNote: '',
      refundTransactions: [],
      attachments: demoAttachments(),
      version: 1
    };
    Object.keys(overrides || {}).forEach(function (key) { base[key] = overrides[key]; });
    return base;
  }

  function defaultState() {
    return {
      version: 1,
      applications: [
        seededApplication({}),
        seededApplication({
          id: 'RA202607260006', videoKey: 'director:6', sourceTaskId: 'BATCH-PENSION', sourceSubTaskId: 6,
          taskTitle: '已完成_养老金规划', videoTitle: '养老金规划越早开始越好', reasonCode: 'motion', reasonLabel: '动作 / 肢体异常',
          description: '人物右手动作不自然，影响成片使用。', issueTime: '00:05', requestedPoints: 24,
          chargeSnapshot: [charge('first_frame', '首帧生成', 10), charge('video', '视频生成', 14)],
          status: 'approved', submittedAt: '2026-07-26T14:10:00+08:00', dueAt: '2026-07-27T14:10:00+08:00',
          reviewedAt: '2026-07-26T16:40:00+08:00', reviewer: '运营管理员', reviewNote: '确认人物手部存在明显异常，同意退还首帧与视频生成的实际扣费积分。',
          attachments: [],
          refundTransactions: [{ id: 'RF202607260006', batchId: 'CB-0720', points: 24, expiresAt: '2026-08-20 10:00', type: 'restore' }]
        }),
        seededApplication({
          id: 'RA202607250007', videoKey: 'director:7', sourceTaskId: 'BATCH-PENSION', sourceSubTaskId: 7,
          taskTitle: '已完成_养老金规划', videoTitle: '个人养老金制度税收优惠', reasonCode: 'config_mismatch', reasonLabel: '与生成配置不符',
          description: '希望人物语速更慢，但成片节奏仍偏快。', issueTime: '', requestedPoints: 22,
          chargeSnapshot: [charge('first_frame', '首帧生成', 10), charge('video', '视频生成', 12)],
          status: 'rejected', submittedAt: '2026-07-25T09:30:00+08:00', dueAt: '2026-07-28T09:30:00+08:00',
          reviewedAt: '2026-07-25T11:15:00+08:00', reviewer: '运营管理员', reviewNote: '复核成片语速与提交配置一致，本次申请未通过。',
          attachments: []
        })
      ],
      deliveryRecords: [],
      auditLogs: [],
      updatedAt: nowIso()
    };
  }

  function normalizeState(state) {
    if (!state || state.version !== 1) return defaultState();
    state.applications = Array.isArray(state.applications) ? state.applications : [];
    state.applications = state.applications.filter(function(application) {
      return application.status !== 'withdrawn';
    });
    state.applications.forEach(function(application) {
      application.chargeSnapshot = (application.chargeSnapshot || []).filter(function(component) {
        return component.type !== 'voice' && component.label !== '语音合成';
      });
      application.attachments = normalizeAttachments(application.attachments);
      if (application.id === 'RA202607270001' && application.status === 'pending' && !application.attachments.length) {
        application.attachments = normalizeAttachments(demoAttachments());
      }
      application.requestedPoints = application.chargeSnapshot.reduce(function(sum, component) {
        return sum + Number(component.refundablePoints || 0);
      }, 0);
      if (application.status === 'approved' && Array.isArray(application.refundTransactions)) {
        var remaining = application.requestedPoints;
        application.refundTransactions = application.refundTransactions.map(function(transaction) {
          var normalized = clone(transaction);
          normalized.points = Math.min(Math.max(0, Number(transaction.points) || 0), remaining);
          remaining -= normalized.points;
          return normalized;
        }).filter(function(transaction) { return transaction.points > 0; });
      }
    });
    state.deliveryRecords = Array.isArray(state.deliveryRecords) ? state.deliveryRecords : [];
    state.auditLogs = Array.isArray(state.auditLogs) ? state.auditLogs : [];
    return state;
  }

  function load() {
    try {
      return normalizeState(JSON.parse(global.localStorage.getItem(STORAGE_KEY) || 'null'));
    } catch (error) {
      return defaultState();
    }
  }

  function save(state) {
    state.updatedAt = nowIso();
    global.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    try { global.dispatchEvent(new CustomEvent('xingzao-refund-change', { detail: clone(state) })); } catch (error) {}
    return clone(state);
  }

  function ensure() {
    var state = load();
    if (!global.localStorage.getItem(STORAGE_KEY)) save(state);
    return state;
  }

  function getApplicationByVideo(videoKey, state) {
    return (state || load()).applications.find(function (item) { return item.videoKey === videoKey; }) || null;
  }

  function getApplication(id, state) {
    return (state || load()).applications.find(function (item) { return item.id === id; }) || null;
  }

  function getDeliveryRecords(videoKey, state) {
    return (state || load()).deliveryRecords.filter(function (item) { return item.videoKey === videoKey; });
  }

  function getEligibility(video, user) {
    var state = load();
    var actor = user || CURRENT_USER;
    var existing = getApplicationByVideo(video.key, state);
    if (video.status !== 'completed') return { eligible: false, code: 'not_completed', message: '仅已完成的视频可申请积分退还', application: existing };
    if (video.creatorId !== actor.id) return { eligible: false, code: 'not_creator', message: '仅任务创建人可申请积分退还', application: existing };
    if (existing) {
      var text = { pending: '申请审核中', approved: '积分已退还', rejected: '申请已驳回，不可再次申请' };
      return { eligible: false, code: existing.status, message: text[existing.status] || '该视频已有退还申请', application: clone(existing) };
    }
    var deliveries = getDeliveryRecords(video.key, state);
    if (deliveries.some(function (item) { return item.type === 'publish'; })) return { eligible: false, code: 'published', message: '该视频已发起外部发布，不可申请积分退还', application: null };
    return { eligible: true, code: 'eligible', message: '可申请积分退还', application: null };
  }

  function buildChargeSnapshot(video, requested) {
    if (Array.isArray(video.chargeSnapshot) && video.chargeSnapshot.length) return clone(video.chargeSnapshot).filter(function(item) { return item.type !== 'voice'; });
    var videoPoints = Math.max(0, Number(video.cost) || 0);
    var components = [
      { type: 'first_frame', label: '首帧生成', points: Math.max(4, Math.round(videoPoints * 0.5)) },
      { type: 'video', label: '视频生成', points: videoPoints }
    ];
    if (requested && requested.length) components = requested.filter(function(item) { return item.type !== 'voice' && item.label !== '语音合成'; });
    var commercial = null;
    try { commercial = JSON.parse(global.localStorage.getItem(COMMERCIAL_KEY) || 'null'); } catch (error) {}
    var allocationTime = new Date();
    var batches = commercial && Array.isArray(commercial.creditBatches) ? commercial.creditBatches.filter(function (item) {
      return Number(item.remain || 0) > 0 && new Date(String(item.expire).replace(' ', 'T')) > allocationTime;
    }) : [];
    batches.sort(function (a, b) { return new Date(String(a.expire).replace(' ', 'T')) - new Date(String(b.expire).replace(' ', 'T')); });
    var fallback = { id: 'CB-0720', expire: '2026-08-20 10:00' };
    var batch = batches[0] || fallback;
    return components.map(function (item) {
      return {
        id: makeId('CHG-'), type: item.type, label: item.label, points: Number(item.points) || 0,
        refundablePoints: Number(item.points) || 0,
        deductions: [{ batchId: batch.id, points: Number(item.points) || 0, originalExpiresAt: String(batch.expire).replace(' ', 'T') }]
      };
    });
  }

  function submitApplication(payload) {
    var state = load();
    var video = payload.video;
    var actor = payload.applicant || CURRENT_USER;
    var eligibility = getEligibility(video, actor);
    if (!eligibility.eligible) return { ok: false, message: eligibility.message, application: eligibility.application };
    if (!String(payload.description || '').trim()) return { ok: false, message: '请填写问题描述' };
    if (Array.isArray(payload.attachments) && payload.attachments.length > 3) return { ok: false, message: '最多上传 3 张问题截图' };
    if ((payload.attachments || []).some(function(item) { return !isValidImageDataUrl(item && item.dataUrl); })) return { ok: false, message: '附件格式无效，仅支持 JPG、PNG、WebP 图片' };
    var attachments = normalizeAttachments(payload.attachments);
    if (attachments.some(function(item) { return item.originalSize > 5 * 1024 * 1024; })) return { ok: false, message: '单张原图不能超过 5MB' };
    if (attachments.some(function(item) { return item.dataUrl.length > 500000; })) return { ok: false, message: '单张截图处理后仍过大，请重新选择' };
    if (attachments.reduce(function(sum, item) { return sum + item.dataUrl.length; }, 0) > 1500000) return { ok: false, message: '截图总容量过大，请减少图片或更换尺寸更小的截图' };
    if ((payload.attachments || []).length !== attachments.length) return { ok: false, message: '附件格式无效，仅支持 JPG、PNG、WebP 图片' };
    var charges = Array.isArray(payload.chargeSnapshot) && payload.chargeSnapshot.length
      ? clone(payload.chargeSnapshot).filter(function(item) { return item.type !== 'voice'; })
      : buildChargeSnapshot(video);
    var requestedPoints = charges.reduce(function (sum, item) { return sum + Number(item.refundablePoints || 0); }, 0);
    if (!isFinite(requestedPoints) || requestedPoints <= 0) return { ok: false, message: '未找到可退还的生成扣费记录' };
    var submittedAt = nowIso();
    var application = {
      id: makeId('RA'), tenantId: payload.tenantId || 't001', tenantName: payload.tenantName || '雨虹投资',
      videoKey: video.key, sourceTaskId: video.taskId || video.taskName || video.key, sourceSubTaskId: video.subTaskId || video.id,
      taskTitle: video.taskName || '未命名任务', videoTitle: video.title || video.script || '单条成片视频',
      applicantId: actor.id, applicantName: actor.name,
      description: String(payload.description).trim(), attachments: attachments,
      requestedPoints: requestedPoints,
      chargeSnapshot: charges, deliverySnapshot: getDeliveryRecords(video.key, state), status: 'pending', submittedAt: submittedAt,
      dueAt: addBusinessDay(submittedAt).toISOString(), reviewedAt: null, reviewer: null, reviewNote: '',
      refundTransactions: [], version: 1
    };
    state.applications.unshift(application);
    state.auditLogs.unshift({ id: makeId('AUD-'), applicationId: application.id, action: 'submit', operator: actor.name, time: submittedAt, note: application.description });
    save(state);
    return { ok: true, application: clone(application) };
  }

  function canDeliver(videoKey) {
    var application = getApplicationByVideo(videoKey);
    if (application && (application.status === 'pending' || application.status === 'approved')) {
      return { allowed: false, message: application.status === 'pending' ? '积分退还申请审核中，暂不可下载或发布' : '该视频积分已退还，不可下载或发布', application: clone(application) };
    }
    return { allowed: true, message: '' };
  }

  function recordDelivery(videoKey, type, actor) {
    if (type !== 'download' && type !== 'publish') return { ok: false, message: '交付类型无效' };
    var state = load();
    var guard = canDeliver(videoKey);
    if (!guard.allowed) return { ok: false, message: guard.message };
    var user = actor || CURRENT_USER;
    var record = { id: makeId('DLV-'), videoKey: videoKey, type: type, actorId: user.id, actorName: user.name, time: nowIso() };
    state.deliveryRecords.unshift(record);
    save(state);
    return { ok: true, record: clone(record) };
  }

  function restoreCredits(application, approvedAt) {
    var commercial;
    try { commercial = JSON.parse(global.localStorage.getItem(COMMERCIAL_KEY) || 'null'); } catch (error) {}
    if (!commercial || commercial.version !== 1) commercial = { version: 1, state: { hasCreditRecharge: true }, creditBatches: [], entitlements: [], orders: [] };
    commercial.tenantId = commercial.tenantId || 't001';
    if (commercial.tenantId !== application.tenantId) return { ok: false, message: '申请租户与积分账户不一致，已转数据异常处理' };
    commercial.creditBatches = Array.isArray(commercial.creditBatches) ? commercial.creditBatches : [];
    commercial.refundApplications = commercial.refundApplications || {};
    if (commercial.refundApplications[application.id]) {
      return { ok: true, transactions: clone(commercial.refundApplications[application.id]) };
    }
    var transactions = [];
    var expiredPoints = 0;
    var restorePlan = [];
    var approvedDate = new Date(approvedAt);
    var invalidMessage = '';
    (application.chargeSnapshot || []).forEach(function (component) {
      var remaining = Math.max(0, Number(component.refundablePoints) || 0);
      var deductionTotal = (component.deductions || []).reduce(function (sum, split) { return sum + Number(split.points || 0); }, 0);
      if (!isFinite(Number(component.refundablePoints)) || Number(component.refundablePoints) <= 0 ||
          !isFinite(deductionTotal) || Math.abs(deductionTotal - remaining) > 0.000001) {
        invalidMessage = '可退积分与扣费分摊不一致，已转数据异常处理';
        return;
      }
      (component.deductions || []).forEach(function (split) {
        if (remaining <= 0 || invalidMessage) return;
        var points = Math.min(remaining, Math.max(0, Number(split.points) || 0));
        remaining -= points;
        var expiresAt = new Date(split.originalExpiresAt);
        var batch = commercial.creditBatches.find(function (item) { return item.id === split.batchId; });
        if (!points) return;
        if (isNaN(expiresAt.getTime())) {
          invalidMessage = '扣费快照中的批次有效期无效，已转数据异常处理';
          return;
        }
        if (expiresAt > approvedDate) {
          if (!batch) {
            invalidMessage = '原积分批次不存在，已转数据异常处理';
            return;
          }
          var batchExpiresAt = new Date(String(batch.expire || '').replace(' ', 'T'));
          if (isNaN(batchExpiresAt.getTime()) || Math.abs(batchExpiresAt.getTime() - expiresAt.getTime()) >= 60000) {
            invalidMessage = '原积分批次有效期与扣费快照不一致，已转数据异常处理';
            return;
          }
          restorePlan.push({ batch: batch, points: points });
        } else {
          expiredPoints += points;
        }
      });
      if (remaining > 0 && !invalidMessage) invalidMessage = '可退积分缺少完整扣费分摊，已转数据异常处理';
    });
    if (invalidMessage) return { ok: false, message: invalidMessage };
    restorePlan.forEach(function (item) {
      item.batch.remain = Number(item.batch.remain || 0) + item.points;
      transactions.push({ id: makeId('RF-'), batchId: item.batch.id, points: item.points, expiresAt: item.batch.expire, type: 'restore' });
    });
    if (expiredPoints > 0) {
      var compensationId = 'REFUND-' + application.id;
      var compensationExpiry = addDays(approvedAt, 7);
      commercial.creditBatches.push({ id: compensationId, source: '质量退还补偿', remain: expiredPoints, arrived: formatDateTime(approvedAt), expire: formatDateTime(compensationExpiry) });
      transactions.push({ id: makeId('RF-'), batchId: compensationId, points: expiredPoints, expiresAt: formatDateTime(compensationExpiry), type: 'compensation' });
    }
    commercial.refundApplications[application.id] = clone(transactions);
    global.localStorage.setItem(COMMERCIAL_KEY, JSON.stringify(commercial));
    return { ok: true, transactions: transactions };
  }

  function reviewApplication(id, decision, note, reviewer) {
    var state = load();
    var application = getApplication(id, state);
    if (!application) return { ok: false, message: '申请不存在' };
    if (application.status !== 'pending') return { ok: false, message: '该申请已处理，不可重复审核' };
    if (decision !== 'approved' && decision !== 'rejected') return { ok: false, message: '审核结果无效' };
    if (!String(note || '').trim()) return { ok: false, message: '请填写处理说明' };
    var approvedAt = nowIso();
    application.status = decision;
    application.reviewedAt = approvedAt;
    application.reviewer = reviewer || '运营管理员';
    application.reviewNote = String(note).trim();
    application.version += 1;
    var commercialBefore = decision === 'approved' ? global.localStorage.getItem(COMMERCIAL_KEY) : null;
    try {
      if (decision === 'approved') {
        var restored = restoreCredits(application, approvedAt);
        if (!restored.ok) return { ok: false, message: restored.message };
        application.refundTransactions = restored.transactions;
      }
      state.auditLogs.unshift({ id: makeId('AUD-'), applicationId: id, action: decision, operator: application.reviewer, time: approvedAt, note: application.reviewNote });
      save(state);
    } catch (error) {
      if (decision === 'approved') {
        try {
          if (commercialBefore === null) global.localStorage.removeItem(COMMERCIAL_KEY);
          else global.localStorage.setItem(COMMERCIAL_KEY, commercialBefore);
        } catch (rollbackError) {}
      }
      return { ok: false, message: '审核保存失败，积分账户未发生变动，请重试' };
    }
    return { ok: true, application: clone(application) };
  }

  function getStatusMeta(status) {
    return {
      pending: { label: '待审核', tone: 'orange' }, approved: { label: '已通过', tone: 'green' },
      rejected: { label: '已驳回', tone: 'red' }
    }[status] || { label: status || '未知', tone: 'gray' };
  }

  function resetDemo() {
    global.localStorage.removeItem(STORAGE_KEY);
    return save(defaultState());
  }

  global.XingzaoRefundStore = {
    STORAGE_KEY: STORAGE_KEY,
    CURRENT_USER: clone(CURRENT_USER),
    REASONS: [
      { code: 'person', label: '人物 / 主体异常' }, { code: 'lip_sync', label: '口型 / 音画不同步' },
      { code: 'motion', label: '动作 / 肢体异常' }, { code: 'visual', label: '画面 / 背景 / 镜头异常' },
      { code: 'audio_caption', label: '音频 / 字幕异常' }, { code: 'config_mismatch', label: '与生成配置不符' },
      { code: 'other', label: '其他' }
    ],
    ensure: ensure,
    load: function () { return clone(load()); },
    getApplication: function (id) { var item = getApplication(id); return item ? clone(item) : null; },
    getApplicationByVideo: function (key) { var item = getApplicationByVideo(key); return item ? clone(item) : null; },
    getDeliveryRecords: function (key) { return clone(getDeliveryRecords(key)); },
    getEligibility: getEligibility,
    buildChargeSnapshot: buildChargeSnapshot,
    submitApplication: submitApplication,
    canDeliver: canDeliver,
    recordDelivery: recordDelivery,
    reviewApplication: reviewApplication,
    getStatusMeta: getStatusMeta,
    formatDateTime: formatDateTime,
    resetDemo: resetDemo
  };

  ensure();
})(window);
