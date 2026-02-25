# 腾讯云轻量服务器部署指南（Ubuntu 20.04）

## 1. 目标
- 解决服务器环境下相对导入报错问题。
- 使用 `gunicorn + systemd + nginx` 部署后端服务。

项目已增加部署入口：`wsgi.py`（`app = create_app()`）。

## 2. 服务器准备
在项目根目录执行：

```bash
cd ~/your-repo-path
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r docs/requirements.txt
pip install gunicorn
```

## 3. 先本地启动验证（服务器内）

### 方式 A：推荐（包模式）
```bash
python3 -m server
```

### 方式 B：WSGI 方式
```bash
gunicorn -w 2 -b 127.0.0.1:5000 wsgi:app
```

若能访问：
```bash
curl http://127.0.0.1:5000/api/projects
```
说明后端正常。

## 4. 配置 systemd 常驻
创建服务文件：

```bash
sudo nano /etc/systemd/system/my-backend.service
```

填入（按你的实际路径替换）：

```ini
[Unit]
Description=My Backend Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/your-repo-path
Environment="PATH=/home/ubuntu/your-repo-path/.venv/bin"
ExecStart=/home/ubuntu/your-repo-path/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 wsgi:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动并开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable my-backend
sudo systemctl start my-backend
sudo systemctl status my-backend
```

查看日志：

```bash
journalctl -u my-backend -f
```

## 5. 配置 Nginx 反向代理
安装并配置：

```bash
sudo apt update
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/my-backend
```

写入：

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置并重载：

```bash
sudo ln -s /etc/nginx/sites-available/my-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 常见报错排查

### 报错：`ImportError: attempted relative import with no known parent package`
原因：用了文件直跑方式，例如 `python3 server/app_factory.py`。  
解决：改用
- `python3 -m server`，或
- `gunicorn ... wsgi:app`。

### 报错：`ModuleNotFoundError: No module named 'server'`
原因：启动目录不在项目根目录。  
解决：先 `cd` 到项目根目录（与 `wsgi.py` 同级）再启动。

### 报错：端口不通
- 检查腾讯云防火墙/安全组是否放行 `80/443`。
- `systemctl status my-backend` 与 `journalctl -u my-backend -f` 查看服务状态。

## 7. 更新代码后的发布
```bash
cd ~/your-repo-path
git pull
source .venv/bin/activate
pip install -r docs/requirements.txt
sudo systemctl restart my-backend
sudo systemctl status my-backend
```
