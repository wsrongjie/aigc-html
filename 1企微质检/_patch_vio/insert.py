import os, shutil

base = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(base)
src = os.path.join(root, '合规工作台_风险处置合并版_可交互原型.html')
dst = os.path.join(root, '合规工作台_违规列表版_可交互原型.html')

shutil.copyfile(src, dst)
s = open(dst, encoding='utf-8').read()

patch = open(os.path.join(base, 'vio_patch.js'), encoding='utf-8').read()
patch = patch.replace(chr(92), chr(92) * 2)
anchor = ' fdeV7Init();render();'
assert s.count(anchor) == 1, s.count(anchor)
assert 'FDE_VIO_NOW' not in s, '已插入过补丁'
s = s.replace(anchor, '\n' + patch + '\n' + anchor)

css = open(os.path.join(base, 'vio.css'), encoding='utf-8').read()
assert s.count('</head>') == 1, s.count('</head>')
s = s.replace('</head>', '<style id="vio-style">\n' + css + '</style>\n</head>')

open(dst, 'w', encoding='utf-8').write(s)
print('inserted chars', len(s))
