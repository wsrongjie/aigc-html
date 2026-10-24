import re, sys

p = r"C:\Users\wsrji\Desktop\AIGC\AI视频原型\3.0b版本\1企微质检\企业数据资产中心-交互原型.html"
html = open(p, encoding='utf-8').read()
m = re.search(r'<style>(.*?)</style>', html, re.S)
css = m.group(1)

rules = re.findall(r'([^{}]+)\{([^{}]*)\}', css)
prefixes = [k.strip() for k in sys.argv[1].split('|') if k.strip()]
seen = set()
for sel, body in rules:
    s = ' '.join(sel.split())
    parts = [x.strip() for x in s.split(',')]
    for part in parts:
        if any(part.startswith(pre) for pre in prefixes):
            line = f"{s} {{ {body.strip()[:500]} }}"
            if line not in seen:
                seen.add(line)
                print(line)
                print()
            break
