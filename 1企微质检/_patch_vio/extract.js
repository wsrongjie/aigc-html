const fs = require('fs');
const path = '合规工作台_违规列表版_可交互原型.html';
const s = fs.readFileSync(path, 'utf8');
const names = ['pNe','hNe','gNe','mNe','vNe','yNe'];
const parts = [];
for (const n of names) {
  const i = s.indexOf(n + '=`');
  if (i < 0) { console.error('not found', n); process.exit(1); }
  let j = i + n.length + 2;
  for (; j < s.length; j++) {
    if (s[j] === '\\') { j++; continue; }
    if (s[j] === '`') break;
  }
  const expr = s.slice(i + n.length, j + 1);
  const val = eval('(' + expr.slice(1) + ')');
  parts.push(val);
  console.log(n, 'len', val.length);
}
const code = parts.join('\n');
fs.writeFileSync('_patch_vio/_biz.js', code);
console.log('total', code.length);
