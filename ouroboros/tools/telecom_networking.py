"""Ouroboros — Telecom & Networking tools."""
from __future__ import annotations
import ipaddress, math, logging
from typing import Any, Dict
from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)


def subnet_calculator(ip: str, mask: str = "24") -> Dict[str, Any]:
    mask = mask.lstrip("/")
    try:
        net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
    except ValueError:
        return {"error": f"Invalid IP/mask: {ip}/{mask}"}
    hosts = list(net.hosts())
    return {"network": str(net.network_address), "broadcast": str(net.broadcast_address),
            "netmask": str(net.netmask), "wildcard": str(net.hostmask), "cidr": f"/{net.prefixlen}",
            "total_hosts": net.num_addresses, "usable_hosts": len(hosts),
            "host_range": f"{hosts[0]} - {hosts[-1]}" if hosts else "N/A",
            "prefix_length": net.prefixlen, "is_private": net.is_private}


def vlan_designer(num_users: int = 100, departments: str = "management,data,voice,guest",
                  base_network: str = "10.0.0.0/16") -> Dict[str, Any]:
    deps = [d.strip() for d in departments.split(",")]
    base = ipaddress.IPv4Network(base_network, strict=False)
    users_per_dept = max(2, num_users // len(deps))
    prefix = max(16, 32 - math.ceil(math.log2(users_per_dept + 2)))
    subnets = list(base.subnets(new_prefix=prefix))
    vlans, vlan_id = [], 10
    for i, dep in enumerate(deps):
        if i >= len(subnets):
            break
        sn = subnets[i]
        hosts = list(sn.hosts())
        vlans.append({"vlan_id": vlan_id, "name": dep, "subnet": str(sn),
                      "gateway": str(hosts[0]) if hosts else "N/A",
                      "dhcp_range": f"{hosts[1]} - {hosts[-1]}" if len(hosts) > 1 else "N/A",
                      "capacity": len(hosts)})
        vlan_id += 10
    return {"total_users": num_users, "base_network": base_network, "vlans": vlans,
            "trunk_config": "switchport mode trunk\nswitchport trunk allowed vlan " +
                            ",".join(str(v["vlan_id"]) for v in vlans)}


def network_diagram(topology: str = "star", nodes: int = 8, node_names: str = "") -> Dict[str, Any]:
    names = [n.strip() for n in node_names.split(",") if n.strip()] if node_names else [f"N{i}" for i in range(nodes)]
    nodes = len(names)
    lines = []
    if topology == "star":
        lines.append(f"        [{names[0]}]")
        lines.append("       " + "/|\\" * min(3, nodes - 1))
        lines.append("  " + "  ".join(f"[{n}]" for n in names[1:]))
    elif topology == "ring":
        top, bot = names[:nodes // 2], names[nodes // 2:]
        lines.append("  " + " --- ".join(f"[{n}]" for n in top))
        lines.append(f"  |{' ' * max(1, len(top) * 8 - 3)}|")
        lines.append("  " + " --- ".join(f"[{n}]" for n in reversed(bot)))
    elif topology == "mesh":
        for i, n in enumerate(names):
            lines.append(f"  [{n}] <-> {', '.join(names[j] for j in range(nodes) if j != i)}")
    elif topology == "hybrid":
        mid = nodes // 2
        lines += ["  Core:", "    " + " === ".join(f"[{n}]" for n in names[:2]),
                  "  Distribution:", "    " + " --- ".join(f"[{n}]" for n in names[2:mid]),
                  "  Access:", "    " + " --- ".join(f"[{n}]" for n in names[mid:])]
    else:
        lines.append("  " + " --- ".join(f"[{n}]" for n in names))
    return {"topology": topology, "node_count": nodes, "diagram": "\n".join(lines)}


def bandwidth_calculator(users: int = 50, apps: str = "web,email,voip",
                         overhead_pct: float = 20.0, qos_enabled: bool = True) -> Dict[str, Any]:
    app_bw = {"web": 2.0, "email": 0.5, "voip": 0.1, "video": 5.0, "streaming": 8.0,
              "vpn": 3.0, "cloud": 4.0, "gaming": 10.0, "file_transfer": 6.0, "erp": 1.5}
    details, total = [], 0.0
    for a in (x.strip() for x in apps.split(",")):
        bw = app_bw.get(a, 2.0)
        details.append({"app": a, "per_user_mbps": bw, "total_mbps": bw * users})
        total += bw * users
    tot_oh = total * (1 + overhead_pct / 100)
    qos_alloc = {"critical": round(tot_oh * 0.3, 1), "high": round(tot_oh * 0.3, 1),
                 "medium": round(tot_oh * 0.25, 1), "best_effort": round(tot_oh * 0.15, 1)} if qos_enabled else {}
    tiers = [(100, "100 Mbps"), (250, "250 Mbps"), (500, "500 Mbps"),
             (1000, "1 Gbps"), (2500, "2.5 Gbps"), (10000, "10 Gbps")]
    rec = next((t[1] for t in tiers if t[0] >= tot_oh), "10+ Gbps")
    return {"users": users, "breakdown": details, "raw_total_mbps": round(total, 1),
            "with_overhead_mbps": round(tot_oh, 1), "recommended_link": rec, "qos_allocation": qos_alloc}


def voip_planner(concurrent_calls: int = 20, codec: str = "G.711",
                 qos_enabled: bool = True) -> Dict[str, Any]:
    codecs = {"G.711": (64, 160, 50, 4.4), "G.729": (8, 20, 50, 3.9),
              "G.722": (64, 160, 50, 4.5), "OPUS": (32, 80, 50, 4.3)}
    bitrate, payload, pps, mos = codecs.get(codec, codecs["G.711"])
    bw_per_call = (payload + 40) * 8 * pps / 1000  # kbps; 40 = IP+UDP+RTP overhead
    total_bw = bw_per_call * concurrent_calls / 1000
    qos = {"dscp": "EF (46)", "cos": 5, "priority_queue": True,
           "max_latency_ms": 150, "max_jitter_ms": 30, "max_loss_pct": 1.0} if qos_enabled else {}
    return {"codec": codec, "codec_bitrate_kbps": bitrate,
            "bandwidth_per_call_kbps": round(bw_per_call, 1), "concurrent_calls": concurrent_calls,
            "total_bandwidth_mbps": round(total_bw, 2), "expected_mos": mos, "qos_settings": qos,
            "sip_config": {"transport": "UDP/TCP 5060, TLS 5061", "rtp_range": "16384-32767",
                           "dtmf": "RFC 2833", "registration_interval": 3600}}


def wireless_planner(area_sqft: int = 5000, users: int = 50,
                     band: str = "dual", environment: str = "office") -> Dict[str, Any]:
    cov = {"office": 1500, "warehouse": 3000, "outdoor": 5000, "classroom": 1000, "auditorium": 800}.get(environment, 1500)
    num_aps = max(math.ceil(area_sqft / cov), math.ceil(users / 25))
    ch24, ch5 = [1, 6, 11], [36, 40, 44, 48, 149, 153, 157, 161]
    plan = []
    for i in range(num_aps):
        ap = {"ap": f"AP-{i+1}"}
        if band in ("2.4", "dual"):
            ap["channel_2.4GHz"] = ch24[i % 3]
            ap["power_2.4GHz_dBm"] = 14 if environment == "office" else 20
        if band in ("5", "dual"):
            ap["channel_5GHz"] = ch5[i % 8]
            ap["power_5GHz_dBm"] = 17 if environment == "office" else 23
        plan.append(ap)
    return {"area_sqft": area_sqft, "users": users, "recommended_aps": num_aps, "channel_plan": plan,
            "ssid_design": [{"ssid": "Corp-Secure", "auth": "WPA3-Enterprise", "vlan": 10},
                            {"ssid": "Guest", "auth": "WPA3-Personal + Captive Portal", "vlan": 99}],
            "notes": f"Environment: {environment}. Min SNR: 25 dB. Overlap: 20%."}


def firewall_acl(rules: str = "", vendor: str = "cisco", default_action: str = "deny") -> Dict[str, Any]:
    parsed = []
    for line in rules.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 4:
            parsed.append({"action": parts[0], "proto": parts[1], "src": parts[2],
                           "dst": parts[3], "port": parts[4] if len(parts) > 4 else "any"})
    out, seq = [], 10
    if vendor == "cisco":
        out.append("ip access-list extended GENERATED_ACL")
        for r in parsed:
            p = f"eq {r['port']}" if r["port"] != "any" else ""
            out.append(f" {seq} {r['action']} {r['proto']} {r['src']} {r['dst']} {p}".rstrip())
            seq += 10
        out.append(f" {seq} {default_action} ip any any")
    elif vendor == "juniper":
        out.append("set firewall family inet filter GENERATED_ACL {")
        for i, r in enumerate(parsed):
            out += [f"  term RULE_{i} {{", f"    from source-address {r['src']};",
                    f"    from destination-address {r['dst']};"]
            if r["port"] != "any":
                out.append(f"    from destination-port {r['port']};")
            out += [f"    then {r['action']};", "  }"]
        out += [f"  term DEFAULT {{ then {default_action}; }}", "}"]
    elif vendor == "paloalto":
        for i, r in enumerate(parsed):
            svc = f"service-{r['proto']}-{r['port']}" if r["port"] != "any" else "any"
            out.append(f"set rulebase security rules RULE_{i} from any to any source {r['src']} "
                       f"destination {r['dst']} application any service {svc} action {r['action']}")
    return {"vendor": vendor, "rule_count": len(parsed), "config": "\n".join(out)}


def bgp_config(local_as: int = 65000, neighbor_ip: str = "10.0.0.1",
               remote_as: int = 65001, prefixes: str = "10.0.0.0/24", vendor: str = "cisco") -> Dict[str, Any]:
    pfx = [p.strip() for p in prefixes.split(",")]
    lines = []
    if vendor == "cisco":
        lines += [f"router bgp {local_as}", f" bgp router-id {neighbor_ip.rsplit('.', 1)[0]}.1",
                  f" neighbor {neighbor_ip} remote-as {remote_as}",
                  f" neighbor {neighbor_ip} description PEER_AS{remote_as}",
                  f" neighbor {neighbor_ip} route-map PEER_IN in",
                  f" neighbor {neighbor_ip} route-map PEER_OUT out", "!"]
        for p in pfx:
            lines.append(f" network {p.split('/')[0]} mask {ipaddress.IPv4Network(p, strict=False).netmask}")
        lines += ["!", f"ip prefix-list ADVERTISED seq 5 permit {pfx[0]}", "!",
                  "route-map PEER_IN permit 10", f" set community {local_as}:100",
                  "route-map PEER_OUT permit 10", " match ip address prefix-list ADVERTISED"]
    elif vendor == "juniper":
        lines += ["protocols {", "  bgp {", f"    group PEER_AS{remote_as} {{",
                  "      type external;", f"      peer-as {remote_as};", f"      local-as {local_as};",
                  f"      neighbor {neighbor_ip};", "      import PEER_IN;", "      export PEER_OUT;",
                  "    }", "  }", "}"]
        for p in pfx:
            lines.append(f"policy-options prefix-list ADVERTISED {{ {p}; }}")
    return {"local_as": local_as, "remote_as": remote_as, "neighbor": neighbor_ip,
            "vendor": vendor, "config": "\n".join(lines)}


def network_troubleshoot(symptom: str = "latency") -> Dict[str, Any]:
    trees = {
        "latency": ["Check interface errors: show interface | inc errors",
                     "Check CPU/memory: show processes cpu sorted",
                     "Traceroute to identify hop with delay",
                     "Check QoS queues: show policy-map interface",
                     "Check duplex mismatch: show interface status",
                     "Check MTU issues: ping with DF bit set"],
        "packet_loss": ["Check interface CRC/input errors", "Check buffer overruns: show buffers",
                        "Check QoS drops: show policy-map interface", "Verify cable/SFP health",
                        "Check spanning-tree topology changes", "Run extended ping with sweep sizes"],
        "dns": ["Verify DNS config: nslookup/dig target", "Check DNS server reachability",
                "Check /etc/resolv.conf or ipconfig /all", "Try alternate DNS (8.8.8.8, 1.1.1.1)",
                "Check for DNS cache poisoning: flush cache", "Verify DNSSEC if applicable"],
        "routing": ["Check routing table: show ip route", "Verify neighbor adjacencies (OSPF/BGP)",
                    "Check for route flapping: show ip bgp flap-statistics",
                    "Verify redistribution: show route-map", "Check ACLs blocking routing protocols",
                    "Verify next-hop reachability"],
        "connectivity": ["Verify physical link: show interface status", "Check VLAN: show vlan brief",
                         "Verify ARP table: show arp", "Check STP: show spanning-tree",
                         "Traceroute to destination", "Check firewall rules in path"],
    }
    steps = trees.get(symptom, trees["connectivity"])
    return {"symptom": symptom, "diagnostic_steps": [f"{i+1}. {s}" for i, s in enumerate(steps)],
            "tools": ["ping", "traceroute", "mtr", "tcpdump", "wireshark", "nmap"]}


def capacity_planner(current_usage_mbps: float = 500, total_capacity_mbps: float = 1000,
                     growth_rate_pct: float = 15, planning_years: int = 3) -> Dict[str, Any]:
    util = current_usage_mbps / total_capacity_mbps * 100
    projections, usage = [], current_usage_mbps
    for y in range(1, planning_years + 1):
        usage *= (1 + growth_rate_pct / 100)
        u = usage / total_capacity_mbps * 100
        projections.append({"year": y, "projected_mbps": round(usage, 1), "utilization_pct": round(u, 1),
                            "status": "OK" if u < 70 else "WARNING" if u < 85 else "CRITICAL"})
    upgrades = []
    if any(p["status"] != "OK" for p in projections):
        target = projections[-1]["projected_mbps"] * 1.5
        tiers = [(1000, "1 Gbps"), (2500, "2.5 Gbps"), (10000, "10 Gbps"),
                 (25000, "25 Gbps"), (40000, "40 Gbps"), (100000, "100 Gbps")]
        rec = next((t[1] for t in tiers if t[0] >= target), "100+ Gbps")
        first_warn = next((p["year"] for p in projections if p["status"] != "OK"), planning_years)
        upgrades.append({"upgrade_by_year": first_warn, "recommended_capacity": rec,
                         "target_headroom_mbps": round(target, 1)})
    return {"current_usage_mbps": current_usage_mbps, "total_capacity_mbps": total_capacity_mbps,
            "current_utilization_pct": round(util, 1), "growth_rate_pct": growth_rate_pct,
            "projections": projections, "upgrade_recommendations": upgrades}


# ── Tool registry ──────────────────────────────────────────────────────
def _raw_tools() -> list:
    P = "type"
    return [
        {"name": "subnet_calculator", "description": "Calculate subnet details from IP/mask: network, broadcast, host range, CIDR.",
         "parameters": {"type": "object", "properties": {"ip": {P: "string"}, "mask": {P: "string", "default": "24"}}, "required": ["ip"]},
         "function": subnet_calculator},
        {"name": "vlan_designer", "description": "Design VLAN architecture with IP schemes for departments.",
         "parameters": {"type": "object", "properties": {"num_users": {P: "integer", "default": 100}, "departments": {P: "string", "default": "management,data,voice,guest"}, "base_network": {P: "string", "default": "10.0.0.0/16"}}},
         "function": vlan_designer},
        {"name": "network_diagram", "description": "Generate text-based network topology diagram (star, mesh, ring, hybrid).",
         "parameters": {"type": "object", "properties": {"topology": {P: "string", "enum": ["star", "mesh", "ring", "hybrid"], "default": "star"}, "nodes": {P: "integer", "default": 8}, "node_names": {P: "string"}}},
         "function": network_diagram},
        {"name": "bandwidth_calculator", "description": "Calculate bandwidth requirements from users, apps, overhead, QoS.",
         "parameters": {"type": "object", "properties": {"users": {P: "integer", "default": 50}, "apps": {P: "string", "default": "web,email,voip"}, "overhead_pct": {P: "number", "default": 20.0}, "qos_enabled": {P: "boolean", "default": True}}},
         "function": bandwidth_calculator},
        {"name": "voip_planner", "description": "VoIP deployment: codec selection, bandwidth/call, QoS, SIP config.",
         "parameters": {"type": "object", "properties": {"concurrent_calls": {P: "integer", "default": 20}, "codec": {P: "string", "enum": ["G.711", "G.729", "G.722", "OPUS"], "default": "G.711"}, "qos_enabled": {P: "boolean", "default": True}}},
         "function": voip_planner},
        {"name": "wireless_planner", "description": "WiFi deployment: AP placement, channel planning, power levels, coverage.",
         "parameters": {"type": "object", "properties": {"area_sqft": {P: "integer", "default": 5000}, "users": {P: "integer", "default": 50}, "band": {P: "string", "enum": ["2.4", "5", "dual"], "default": "dual"}, "environment": {P: "string", "enum": ["office", "warehouse", "outdoor", "classroom", "auditorium"], "default": "office"}}},
         "function": wireless_planner},
        {"name": "firewall_acl", "description": "Generate firewall ACL rules for Cisco/Juniper/Palo Alto syntax.",
         "parameters": {"type": "object", "properties": {"rules": {P: "string", "description": "Newline-separated: action proto src dst [port]"}, "vendor": {P: "string", "enum": ["cisco", "juniper", "paloalto"], "default": "cisco"}, "default_action": {P: "string", "enum": ["permit", "deny"], "default": "deny"}}, "required": ["rules"]},
         "function": firewall_acl},
        {"name": "bgp_config", "description": "Generate BGP config: peering, route maps, prefix lists, communities.",
         "parameters": {"type": "object", "properties": {"local_as": {P: "integer", "default": 65000}, "neighbor_ip": {P: "string", "default": "10.0.0.1"}, "remote_as": {P: "integer", "default": 65001}, "prefixes": {P: "string", "default": "10.0.0.0/24"}, "vendor": {P: "string", "enum": ["cisco", "juniper"], "default": "cisco"}}},
         "function": bgp_config},
        {"name": "network_troubleshoot", "description": "Diagnostic decision tree for network issues: latency, packet_loss, dns, routing, connectivity.",
         "parameters": {"type": "object", "properties": {"symptom": {P: "string", "enum": ["latency", "packet_loss", "dns", "routing", "connectivity"], "default": "latency"}}},
         "function": network_troubleshoot},
        {"name": "capacity_planner", "description": "Network capacity planning: project growth, recommend upgrades.",
         "parameters": {"type": "object", "properties": {"current_usage_mbps": {P: "number", "default": 500}, "total_capacity_mbps": {P: "number", "default": 1000}, "growth_rate_pct": {P: "number", "default": 15}, "planning_years": {P: "integer", "default": 3}}},
         "function": capacity_planner},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
