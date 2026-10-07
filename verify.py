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
assert len(entries) == len(set(entries)) == 9
for entry in entries:
    kind, domain = entry.split(",", 1)
    tcp = entry + ",Claude-ISP"
    udp = "AND,((NETWORK,udp),(" + entry + ")),REJECT"
    assert tcp in rules and udp in rules
    assert rules.index(udp) < rules.index(tcp) < rules.index("GEOSITE,cn,DIRECT")
    key = "+." + domain if kind == "DOMAIN-SUFFIX" else domain
    assert all(url.endswith("#Claude-ISP") for url in config["dns"]["nameserver-policy"][key])
assert "DOMAIN-SUFFIX,b-cdn.net,Claude-ISP" not in rules
assert "DOMAIN-SUFFIX,jd.com,DIRECT" in rules
assert rules[-1] == "MATCH,Proxy"
groups = {g["name"]: g for g in config["proxy-groups"]}
assert groups["Claude-ISP"]["proxies"] == ["Dedicated-ISP"]
assert groups["Proxy"]["proxies"] == ["Japan-Upstream"]
assert all(p["server"].endswith(".example.invalid") for p in config["proxies"])
assert not config.get("secret") and not config.get("external-controller")
print("PASS: placeholders, nine domains, DNS routing, UDP ordering, domestic rules, and regeneration")
