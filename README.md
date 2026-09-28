update to the previious version on thegearybox respository. 

quite simeple, 
  
  1. git clone it,
  2. cd TheGearyBoxV2.0
  3. python3 -m venv  venv
  4. enter virt env
  5. pip install -r requirements.txt
  6. run it with : uvicorn start:app --port 7050


Good logic to have (hopefully) the best streams first/ most reliable. 


set it up as a service with systemctl  for example : 

[Unit]
Description=TheGearyBox stremio addon Service
After=network.target

[Service]
Type=simple
User=
WorkingDirectory=path/to/TheGearyBoxV2.0
Environment=PYTHONUNBUFFERED=1
ExecStart=/path/to/TheGearyBoxV2.0/venv/bin/uvicorn start:app --port 7050
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target


then link it with a tailscale funnal (be warned its a horrible configuration tailscale, tailscaled,  but its really worth it when its done. 
this then gives yopu a static url not like cloudflared that always changes unless you pay them.

yourtailscaleurl.net/manifest.json to add it to any device at all.
