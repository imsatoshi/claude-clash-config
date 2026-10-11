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
    assert all(url.split("#", 1)[1].split("&")[0] == "Claude-ISP" for url in config["dns"]["nameserver-policy"][key])
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
def resolver_addresses(dns):
    for field in ["default-nameserver", "nameserver", "fallback", "proxy-server-nameserver", "direct-nameserver"]:
        yield from dns[field]
    for field in ["nameserver-policy", "proxy-server-nameserver-policy"]:
        for addresses in dns[field].values():
            yield from addresses


for address in resolver_addresses(config["dns"]):
    params = address.split("#", 1)[1].split("&")
    for qtype in [64, 65]:
        assert params.count(f"disable-qtype-{qtype}=true") == 1

# Exercise the switch against an already-filtered config: rollback must remove
# only our two flags, without changing routes, resolver choices or credentials.
toggle_runner = """
const fs=require('fs'),vm=require('vm'),c={};
const source=fs.readFileSync(process.argv[1],'utf8');
if (!source.includes('const BLOCK_DNS_64_65 = true;')) throw Error('Missing enabled switch');
vm.createContext(c);
vm.runInContext(source.replace('const BLOCK_DNS_64_65 = true;', 'const BLOCK_DNS_64_65 = false;'),c);
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const output=c.main(input);
const address='https://dns.example.invalid/dns-query#Claude-ISP&ecs=192.0.2.0/24&disable-qtype-65=true&disable-qtype-64=true';
if (c.withDnsTypeFilter(address)!=='https://dns.example.invalid/dns-query#Claude-ISP&ecs=192.0.2.0/24')
  throw Error('Disabling changed unrelated parameters');
process.stdout.write(JSON.stringify(output));
"""
r = subprocess.run([node, "-e", toggle_runner, str(root / "clash-verge-script.js")], input=json.dumps(config), text=True, capture_output=True, check=True)
disabled = json.loads(r.stdout)
assert not any("disable-qtype-" in address for address in resolver_addresses(disabled["dns"]))
assert {k: v for k, v in disabled.items() if k != "dns"} == {k: v for k, v in config.items() if k != "dns"}
restored = subprocess.run([node, "-e", runner, str(root / "clash-verge-script.js")], input=json.dumps(disabled), text=True, capture_output=True, check=True)
assert json.loads(restored.stdout) == config, "Toggle round trip changed configuration"
print("PASS: placeholders, routes, DNS policies, UDP ordering, domestic rules, regeneration, and DNS 64/65 toggle round trip")
