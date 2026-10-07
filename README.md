# Claude 专用出口与国内分流模板

这是从个人 Clash Verge 配置中提取的**脱敏模板**，不是能直接连接的节点订阅。真实节点、用户名、密码、UUID、订阅链接、控制器密钥和个人路径均未包含。

## 路由设计

- Rule 模式 + TUN。
- Claude 指定域名：`Japan-Upstream → Dedicated-ISP → 目标`。
- 普通海外流量：`Proxy → Japan-Upstream`。
- 国内常用网站、局域网和共享地址空间按规则直连。
- 专用 SOCKS5 仅配置 TCP，因此指定 Claude 域名和进程的 UDP 先拒绝，避免回落到普通代理或直连。
- Claude DNS 策略绑定 Claude-ISP；国内 DNS 使用直连 DoH。
- `127.0.0.1:17898` 是固定走 Claude-ISP 的 HTTP 代理端口，可供 Claude Code 使用。

## 文件

- `clash.example.yaml`：完整示例，所有节点参数都是占位符。
- `clash-verge-script.js`：订阅扩展脚本，集中生成域名规则、UDP 拒绝规则和 DNS 策略。
- `claude-rules.list`：9 条域名规则；没有代理策略名称，也不包含 DNS 和 UDP 设置。
- `verify.py`：本地静态检查，不连接节点、不更改系统网络。

## 使用

1. 将示例复制为 `clash.local.yaml`，只在本地填写真实节点信息。前置示例使用 VLESS Reality；如果节点采用其他协议，请替换完整的前置节点段。
2. 保留节点名 `Japan-Upstream` 和 `Dedicated-ISP`，或同步修改脚本。专用 ISP 采用 SOCKS5 用户名密码认证；端口 443 不代表启用了 TLS。
3. 在 Clash Verge 中导入本地配置，保持 Rule 模式。也可以把脚本作为订阅扩展，但原配置必须已经存在两个节点以及 `Proxy`、`Claude-ISP` 组。
4. 该脚本会重建 `rules`、相关 DNS 策略和专用监听器。先备份并检查与你的其他分流是否冲突；不要无检查地叠加到其他订阅。
5. Claude Code 可在本地环境或用户 settings.json 的 env 中设置 `HTTP_PROXY`、`HTTPS_PROXY` 为 `http://127.0.0.1:17898`。这个设置不会自动覆盖工具启动的每一个子进程。
6. 本地验证：`python3 verify.py`，需要 Python PyYAML 和 Node.js。填写节点后，再用本机 Mihomo 的 `-t -f clash.local.yaml` 检查。

## 边界

- 不包含原电脑两个业务服务器的直连例外，迁移到原环境时要从本地配置保留。
- 进程规则面向 macOS；浏览器依靠域名规则，其他系统需调整进程路径。
- 不包含第三方共享 CDN、遥测平台的宽泛兜底，不宣称覆盖 Claude 的所有外部资源。
- 仅对列出的 Claude UDP 目标拒绝，不是全局 WebRTC 防泄漏方案。
- TUN、IPv6 设置和分流规则不能等同于断网或休眠唤醒时的系统级 kill switch。
- 代理出口、IP 检测分数不能保证服务账号可用或改变服务地区资格。
- 模板不包含控制 API 监听端口和密钥；按需仅在本地配置。
- 不要上传 `*.local.*`、原始订阅、备份或日志；`.gitignore` 不能代替内容审查。

## 来源

- [Claude 官方网络文档](https://code.claude.com/docs/en/network-config)
- [v2fly Anthropic 域名集](https://github.com/v2fly/domain-list-community/blob/master/data/anthropic)
- [Mihomo 规则文档](https://wiki.metacubex.one/config/rules/)

这份模板未整体导入第三方分流配置。真实电脑的验证结果不能代替其他设备填写参数后的验证。
