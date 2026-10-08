import json
import pathlib
import shutil
import subprocess
import yaml

root = pathlib.Path(__file__).resolve().parent
config = yaml.safe_load((root / "clash.example.yaml").read_text())
node = shutil.which("node")
assert node, "Node.js is required"
subprocess.run([node, "--check", str(root / "clash-verge-script.js")], check=True)
runner = "const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);process.stdout.write(JSON.stringify(c.main(JSON.parse(fs.readFileSync(0,'utf8')))));"
r = subprocess.run([node, "-e", runner, str(root / "clash-verge-script.js")], input=json.dumps(config), text=True, capture_output=True, check=True)
assert json.loads(r.stdout) == config, "Regeneration changed the example"
rules = config["rules"]
entries = [line for line in (root / "claude-rules.list").read_text().splitlines() if line and not line.startswith("#")]
assert entries and len(entries) == len(set(entries))
assert set(entries) == {r.removesuffix(",Claude-ISP") for r in rules if r.startswith(("DOMAIN,", "DOMAIN-SUFFIX,")) and r.endswith(",Claude-ISP")}
for entry in entries:
    kind, domain = entry.split(",", 1)
    tcp = entry + ",Claude-ISP"
    udp = "AND,((NETWORK,udp),(" + entry + ")),REJECT"
    assert tcp in rules and udp in rules
    assert rules.index(udp) < rules.index(tcp) < rules.index("GEOSITE,cn,DIRECT")
    key = "+." + domain if kind == "DOMAIN-SUFFIX" else domain
    assert all(url.endswith("#Claude-ISP") for url in config["dns"]["nameserver-policy"][key])
for kind, cidr in [("IP-CIDR", "160.79.104.0/23"), ("IP-CIDR6", "2607:6bc0::/48")]:
    entry = f"{kind},{cidr},no-resolve"
    tcp = f"{kind},{cidr},Claude-ISP,no-resolve"
    udp = f"AND,((NETWORK,udp),({entry})),REJECT"
    assert tcp in rules and udp in rules
    assert rules.index(udp) < rules.index(tcp) < rules.index("GEOSITE,cn,DIRECT")
assert not any("160.79.104.0/21" in r or "2607:6bc0::/32" in r for r in rules)
assert not any(r.startswith("DOMAIN-KEYWORD,") and r.endswith(",Claude-ISP") for r in rules)
for shared in ["b-cdn.net", "datadoghq.com", "sentry.io", "intercom.io"]:
    assert f"DOMAIN-SUFFIX,{shared},Claude-ISP" not in rules
assert "DOMAIN-SUFFIX,jd.com,DIRECT" in rules
assert rules[-1] == "MATCH,Proxy"
groups = {g["name"]: g for g in config["proxy-groups"]}
assert groups["Claude-ISP"]["proxies"] == ["Dedicated-ISP"]
assert groups["Proxy"]["proxies"] == ["Japan-Upstream"]
assert all(p["server"].endswith(".example.invalid") for p in config["proxies"])
assert not config.get("secret") and not config.get("external-controller")
print("PASS: placeholders, domain and inbound IP rules, DNS routing, UDP ordering, domestic rules, and regeneration")
