#!/usr/bin/env python3
import sys
import os
import subprocess

def main():
    # Configuration
    username = "proxyuser"  # Single user for all proxies
    base_port = 1080        # Base port (incremented per IP)
    
    # Get proxy password securely
    password_proxy = input("Set proxy password: ").strip()
    
    # System setup
    os.system("apt-get update")
    os.system("apt-get install -y build-essential libwrap0-dev libpam0g-dev libkrb5-dev libsasl2-dev gcc make wget ufw")
    
    # Install Dante
    os.system("wget --no-check-certificate https://ahmetshin.com/static/dante.tgz")
    os.system("tar -xvpzf dante.tgz")
    os.system("mkdir /home/dante")
    os.system("cd dante && ./configure --prefix=/home/dante && make && make install")
    
    # Create system user
    os.system(f"useradd --shell /usr/sbin/nologin -m {username}")
    os.system(f'echo "{username}:{password_proxy}" | chpasswd')
    
    # Get all assigned IPs (excluding loopback)
    ips = subprocess.getoutput(
        "ip -4 addr show ens3 | grep inet | awk '{print $2}' | cut -d'/' -f1"
    ).splitlines()
    
    # Generate configs for each IP
    for i, ip in enumerate(ips):
        port = base_port + i
        
        # Create Dante config
        config = f"""
        logoutput: syslog /var/log/danted_{ip}.log
        internal: {ip} port = {port}
        external: {ip}
        
        socksmethod: username
        user.privileged: root
        user.unprivileged: nobody
        
        client pass {{
            from: 0.0.0.0/0 to: 0.0.0.0/0
            log: error
        }}
        
        socks pass {{
            from: 0.0.0.0/0 to: 0.0.0.0/0
            command: connect
            log: error
            method: username
        }}
        """
        with open(f"/home/dante/danted_{ip}.conf", "w") as f:
            f.write(config)
        
        # Firewall rules
        os.system(f"ufw allow {port}/tcp")
    
    # Finalize firewall
    os.system("ufw allow ssh")
    os.system("echo 'y' | ufw enable")
    
    # Create startup script
    with open("/etc/rc.local", "w") as f:
        f.write("#!/bin/sh -e\n")
        f.write("sleep 15\n")
        for i, ip in enumerate(ips):
            port = base_port + i
            f.write(f"/home/dante/sbin/sockd -f /home/dante/danted_{ip}.conf -D &\n")
        f.write("exit 0\n")
    
    # Set permissions
    os.system("chmod +x /etc/rc.local")
    os.system("chmod +x /home/dante/sbin/sockd")
    
    # Start proxies immediately
    for ip in ips:
        os.system(f"/home/dante/sbin/sockd -f /home/dante/danted_{ip}.conf -D &")
    
    # Output proxy details
    print("\n" + "="*50)
    print("PROXY SETUP COMPLETE\n")
    for i, ip in enumerate(ips):
        print(f"Proxy {i+1}:")
        print(f"IP: {ip}")
        print(f"Port: {base_port + i}")
        print(f"Username: {username}")
        print(f"Password: {password_proxy}")
        print("-"*50)

if __name__ == "__main__":
    main()
