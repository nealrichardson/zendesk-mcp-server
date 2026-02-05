# Load Balancer Configuration for SSE Transport

When deploying the Zendesk MCP server with HTTP/SSE transport behind a load balancer or reverse proxy, additional configuration is required to ensure reliable connections.

## Key Requirements

### 1. Sticky Sessions (Session Affinity)

The MCP SSE transport stores session state in memory. Each SSE connection is assigned a unique session ID, and subsequent POST requests to `/messages` must reach the same backend instance that established the SSE connection.

**Configure your load balancer to use sticky sessions** based on one of:
- Client IP address
- Cookie-based affinity
- Session ID parameter (if supported)

### 2. Disable Response Buffering

Proxies typically buffer responses before forwarding to improve performance. This breaks SSE because events are held in the buffer instead of streaming to the client immediately.

**Symptoms of buffering issues:**
- Events arrive in bursts instead of immediately
- Long delays before first event appears
- Connection appears to hang

### 3. Extended Timeouts

SSE connections are long-lived. Default proxy timeouts (often 60 seconds) will terminate idle connections prematurely.

### 4. Disable Compression

Gzip or other compression algorithms buffer content before compressing, which defeats SSE's streaming nature.

---

## NGINX Configuration

```nginx
upstream mcp_backend {
    ip_hash;  # Sticky sessions based on client IP
    server backend1:8000;
    server backend2:8000;
}

server {
    listen 443 ssl;
    server_name mcp.example.com;

    location / {
        proxy_pass http://mcp_backend;

        # HTTP version and connection handling
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;

        # Disable buffering (critical for SSE)
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header X-Accel-Buffering no;

        # Disable compression for SSE
        gzip off;

        # Extended timeouts for long-lived connections
        proxy_read_timeout 86400;    # 24 hours
        proxy_send_timeout 86400;
        proxy_connect_timeout 60;
    }
}
```

### Cookie-Based Sticky Sessions (Alternative)

If you need stickiness that survives IP address changes:

```nginx
upstream mcp_backend {
    server backend1:8000;
    server backend2:8000;
    sticky cookie srv_id expires=1h path=/;
}
```

Note: The `sticky` directive requires the NGINX Plus commercial version or the `nginx-sticky-module` for open source NGINX.

---

## HAProxy Configuration

```haproxy
frontend mcp_frontend
    bind *:443 ssl crt /etc/ssl/certs/mcp.pem
    default_backend mcp_backend

backend mcp_backend
    balance source                    # Sticky sessions by client IP
    option http-server-close
    option forwardfor

    # Extended timeouts
    timeout client 86400s
    timeout server 86400s
    timeout tunnel 86400s

    # Disable response buffering
    option http-buffer-request
    no option httpclose

    # Health checks
    option httpchk GET /
    http-check expect status 200

    server backend1 backend1:8000 check
    server backend2 backend2:8000 check
```

### Cookie-Based Sticky Sessions (Alternative)

```haproxy
backend mcp_backend
    balance roundrobin
    cookie SERVERID insert indirect nocache
    server backend1 backend1:8000 check cookie s1
    server backend2 backend2:8000 check cookie s2
```

---

## AWS Application Load Balancer (ALB)

### Enable Sticky Sessions

1. Navigate to your Target Group in the EC2 console
2. Go to **Attributes** tab
3. Enable **Stickiness**
4. Choose duration (e.g., 1 day for long SSE connections)

### Important Settings

- **Idle timeout**: Increase to maximum (4000 seconds for ALB). Note: ALB has a hard limit, so for very long-lived connections, consider using NLB or direct connections.
- **Deregistration delay**: Set appropriately for graceful shutdown

### CloudFormation Example

```yaml
TargetGroup:
  Type: AWS::ElasticLoadBalancingV2::TargetGroup
  Properties:
    Protocol: HTTP
    Port: 8000
    TargetGroupAttributes:
      - Key: stickiness.enabled
        Value: "true"
      - Key: stickiness.type
        Value: lb_cookie
      - Key: stickiness.lb_cookie.duration_seconds
        Value: "86400"
      - Key: deregistration_delay.timeout_seconds
        Value: "300"
```

---

## Caddy Configuration

```caddyfile
mcp.example.com {
    reverse_proxy backend1:8000 backend2:8000 {
        lb_policy ip_hash          # Sticky sessions

        # Disable buffering
        flush_interval -1

        # Extended timeouts
        transport http {
            read_timeout 86400s
            write_timeout 86400s
        }
    }

    # Pass forwarded headers
    header_up X-Forwarded-Proto {scheme}
    header_up X-Forwarded-Host {host}
}
```

---

## Traefik Configuration

```yaml
# Dynamic configuration
http:
  services:
    mcp-service:
      loadBalancer:
        sticky:
          cookie:
            name: mcp_sticky
            secure: true
            httpOnly: true
        servers:
          - url: "http://backend1:8000"
          - url: "http://backend2:8000"
        responseForwarding:
          flushInterval: -1        # Disable buffering

  routers:
    mcp-router:
      rule: "Host(`mcp.example.com`)"
      service: mcp-service
      entryPoints:
        - websecure
```

---

## Environment Variables

Remember to configure the MCP server to accept connections from your domain:

```bash
# Allow your domain(s)
MCP_ALLOWED_HOSTS="mcp.example.com:*,*.example.com:*"

# Or disable host validation (not recommended for production)
MCP_ALLOWED_HOSTS="*"
```

---

## Troubleshooting

### Events arrive in bursts, not immediately
- Response buffering is enabled somewhere in the chain
- Check: proxy_buffering, gzip, any caching layers

### Connection drops after ~60 seconds
- Proxy timeout is too short
- Increase read/send timeouts to hours, not seconds

### 404 on /messages endpoint
- Sticky sessions not working; request went to wrong backend
- Verify session affinity configuration

### 421 Invalid Host header
- Host validation is rejecting the request
- Set `MCP_ALLOWED_HOSTS` environment variable

### Connection refused or timeouts
- Backend health checks may be failing
- Verify the MCP server is running and accessible from the load balancer

### Events work initially, then stop
- Idle timeout killing the connection
- Increase idle/read timeouts
- Consider implementing heartbeat/ping events (not currently built into MCP SDK)
