# Phoenix LLM Observability UI — proxied under /phoenix/
location /phoenix/ {
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header Host $host;

    proxy_http_version 1.1;
    # WebSocket support for real-time trace streaming
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    proxy_redirect off;
    rewrite ^/phoenix(/.*)$ $1 break;
    rewrite ^/phoenix/?$ / break;
    proxy_pass http://phoenix_server;
}
