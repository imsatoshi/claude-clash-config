// Active split-routing extension. Claude uses the dedicated Tokyo ISP.
// Keep rule mode and TUN enabled in Clash Verge settings.
function main(config) {
  const group = (config["proxy-groups"] || []).find(g => g.name === "Proxy");
  const nodes = new Set((config.proxies || []).map(p => p.name));
  const preferred = "Japan-Upstream";
  if (!group || !nodes.has(preferred)) throw new Error("Expected Proxy group and current JP node; review this script before using a different subscription.");

  // Restore the upstream hop after Verge normalizes proxy overlay fields.
  // The ISP endpoint must be reached through the existing JP transport.
  const claudeISP = (config.proxies || []).find(p => p.name === "Dedicated-ISP");
  if (!claudeISP) throw new Error("Expected dedicated Claude ISP node.");
  claudeISP["dialer-proxy"] = preferred;

  // Verge adds overlay nodes to existing selectors; keep this node Claude-only.
  for (const g of (config["proxy-groups"] || [])) {
    if (g.name !== "Claude-ISP" && Array.isArray(g.proxies))
      g.proxies = g.proxies.filter(n => n !== "Dedicated-ISP");
  }

  // Manual node choice only. Neither DIRECT nor cross-country Auto is a fallback.
  group.type = "select";
  group.proxies = [preferred, ...group.proxies.filter(n => n !== preferred && nodes.has(n))];

  const claudeDomains = [
    "claude.ai", "claude.com", "anthropic.com", "claudeusercontent.com",
    "claudemcpcontent.com", "claudemcpclient.com", "clau.de", "claude.dev"
  ];
  // Match only this Anthropic CDN host, not the shared b-cdn.net service.
  const claudeExactDomains = ["servd-anthropic-website.b-cdn.net"];
  const claudeGroup = "Claude-ISP";
  config["find-process-mode"] = "always";
  config.listeners = [
    ...(config.listeners || []).filter(x => x.name !== "claude-code-isp"),
    { name: "claude-code-isp", type: "http", listen: "127.0.0.1", port: 17898, proxy: claudeGroup }
  ];
  const claudeProcessRules = [
    "PROCESS-NAME,claude,Claude-ISP",
    "PROCESS-NAME,Claude,Claude-ISP",
    "PROCESS-PATH-REGEX,^/Users/[^/]+/[.]local/share/claude/versions/[^/]+$,Claude-ISP",
    "PROCESS-PATH-REGEX,^/Applications/Claude[.]app/Contents/.*,Claude-ISP"
  ];
  // A TCP-only SOCKS5 node is skipped by Mihomo for UDP; reject instead of
  // falling through to the general Proxy/DIRECT rules.
  const claudeUdpRules = [
    ...claudeDomains.map(d => `AND,((NETWORK,udp),(DOMAIN-SUFFIX,${d})),REJECT`),
    ...claudeExactDomains.map(d => `AND,((NETWORK,udp),(DOMAIN,${d})),REJECT`),
    ...claudeProcessRules.map(r => `AND,((NETWORK,udp),(${r.slice(0, r.lastIndexOf(","))})),REJECT`)
  ];
  const domestic = [
    "qq.com", "weixin.com", "weixinbridge.com", "qpic.cn", "qlogo.cn", "gtimg.com",
    "taobao.com", "tmall.com", "alipay.com", "alipayobjects.com", "alicdn.com",
    "jd.com", "360buyimg.com", "jdpay.com", "bilibili.com", "bilivideo.com", "hdslb.com",
    "feishu.cn", "feishucdn.com", "dingtalk.com", "dingtalkapps.com",
    "douyin.com", "douyincdn.com", "douyinpic.com", "iesdouyin.com",
    "xiaohongshu.com", "xhscdn.com", "meituan.com", "dianping.com", "sankuai.com",
    "baidu.com", "bdstatic.com", "bdimg.com", "163.com", "126.com", "netease.com",
    "gitcode.com", "gitee.com", "aliyun.com", "aliyuncs.com", "myqcloud.com",
    "qcloud.com", "tencentcloud.com", "huaweicloud.com", "icloud.com.cn"
  ];
  const overseas = [
    "openai.com", "chatgpt.com",
    "oaistatic.com", "oaiusercontent.com", "github.com", "githubusercontent.com",
    "google.com", "googleapis.com", "gstatic.com",
    "browserleaks.com", "browserleaks.org", "dnsleaktest.com", "ipleak.net",
    "cloudflare.com", "cloudflare-dns.com", "ipify.org"
  ];
  // Shared-address space used by overlays such as Tailscale.
  // Add private operational exceptions locally; do not publish server addresses.
  const ops = ["100.64.0.0/10"];
  config.rules = [
    ...ops.map(x => `IP-CIDR,${x},DIRECT,no-resolve`),
    "GEOIP,private,DIRECT,no-resolve",
    "DOMAIN-SUFFIX,local,DIRECT", "DOMAIN-SUFFIX,lan,DIRECT",
    ...claudeUdpRules,
    ...claudeDomains.map(d => `DOMAIN-SUFFIX,${d},${claudeGroup}`),
    ...claudeExactDomains.map(d => `DOMAIN,${d},${claudeGroup}`),
    ...claudeProcessRules,
    "GEOSITE,category-ads-all,REJECT",
    ...overseas.map(d => `DOMAIN-SUFFIX,${d},Proxy`),
    ...domestic.map(d => `DOMAIN-SUFFIX,${d},DIRECT`),
    // Some domains exist in BOTH lists. Known overseas takes priority.
    "GEOSITE,geolocation-!cn,Proxy",
    "GEOSITE,cn,DIRECT",
    // Match literal/already-known CN IPs without resolving unknown foreign domains
    // merely to decide whether they should become DIRECT.
    "GEOIP,CN,DIRECT,no-resolve",
    "MATCH,Proxy"
  ];

  const domesticDNS = ["https://223.5.5.5/dns-query#DIRECT", "https://1.12.12.12/dns-query#DIRECT"];
  const overseasDNS = ["https://1.1.1.1/dns-query#Proxy", "https://1.0.0.1/dns-query#Proxy"];
  const policy = {};
  // A small explicit domestic DNS list avoids the overlapping geosite:cn problem.
  for (const d of domestic) policy[`+.${d}`] = domesticDNS;
  for (const d of overseas) policy[`+.${d}`] = overseasDNS;
  for (const d of claudeDomains) policy[`+.${d}`] = ["https://1.1.1.1/dns-query#Claude-ISP", "https://1.0.0.1/dns-query#Claude-ISP"];
  for (const d of claudeExactDomains) policy[d] = ["https://1.1.1.1/dns-query#Claude-ISP", "https://1.0.0.1/dns-query#Claude-ISP"];
  // Preserve LAN/mDNS handling in the OS. Do not blanket-route Tailscale service
  // domains DIRECT: its control plane and relay nodes may be overseas.
  const previousDNS = config.dns || {};
  config.dns = {
    ...previousDNS,
    enable: true, ipv6: false, "enhanced-mode": "fake-ip",
    "fake-ip-range": "198.18.0.1/16", "prefer-h3": false,
    "respect-rules": true,
    "default-nameserver": ["223.5.5.5", "1.12.12.12"],
    nameserver: overseasDNS,
    "nameserver-policy": policy,
    "proxy-server-nameserver": domesticDNS,
    "proxy-server-nameserver-policy": {},
    "direct-nameserver": domesticDNS,
    "direct-nameserver-follow-policy": false,
    fallback: [], "fallback-filter": {},
    // Preserve filters from the previously active global DNS override, even
    // when Verge passes only the subscription's original DNS to this script.
    "fake-ip-filter": [...new Set([
      ...(previousDNS["fake-ip-filter"] || []),
      "*.lan", "*.local", "*.arpa", "time.*.com", "ntp.*.com",
      "+.market.xiaomi.com", "localhost.ptlogin2.qq.com",
      "*.msftncsi.com", "www.msftconnecttest.com",
      "*.tailscale.com", "*.tailscale.io", "controlplane.tailscale.com",
      "login.tailscale.com", "derp*.tailscale.com"
    ])]
  };
  return config;
}
