import subprocess
import time
import os
import paramiko
from getpass import getpass
from scp import SCPClient
import logging
import re
from pyngrok import ngrok
import webbrowser
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def install_packages():
    """Installs the required packages if they are not already installed."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install packages: {e}")
        sys.exit(1)

def execute_ssh_command(client, command):
    """Executes a command on the remote server and logs the output."""
    logging.info(f"Executing command: {command}")
    stdin, stdout, stderr = client.exec_command(command)
    stdout_output = stdout.read().decode()
    stderr_output = stderr.read().decode()
    if stdout_output:
        logging.info(f"Stdout: {stdout_output}")
    if stderr_output:
        logging.error(f"Stderr: {stderr_output}")
    return stdout_output, stderr_output

def get_ngrok_tunnel():
    """Starts an ngrok tunnel and returns the SSH command."""
    try:
        # Set your ngrok authtoken
        ngrok.set_auth_token("YOUR_NGROK_AUTHTOKEN")  # Replace with your ngrok authtoken

        # Start an SSH tunnel
        ssh_tunnel = ngrok.connect(22, "tcp")
        logging.info(f"ngrok tunnel created: {ssh_tunnel.public_url}")
        return ssh_tunnel.public_url
    except Exception as e:
        logging.error(f"Failed to start ngrok tunnel: {e}")
        return None

def generate_server_config():
    return """
port 1194
proto udp
dev tun
ca ca.crt
cert server.crt
key server.key
dh dh.pem
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 208.67.222.222"
push "dhcp-option DNS 208.67.220.220"
keepalive 10 120
cipher AES-256-GCM
persist-key
persist-tun
status openvpn-status.log
verb 3
"""

def open_ovpn_file(ovpn_file):
    """Opens the .ovpn file with the default application."""
    try:
        if sys.platform == "win32":
            os.startfile(ovpn_file)
        elif sys.platform == "darwin":
            subprocess.run(["open", ovpn_file])
        else:
            subprocess.run(["xdg-open", ovpn_file])
        logging.info(f"Successfully opened {ovpn_file} with the default application.")
    except Exception as e:
        logging.error(f"Failed to open {ovpn_file}: {e}")

def main():
    # Install required packages
    install_packages()

    # Get ngrok tunnel
    ngrok_url = get_ngrok_tunnel()
    if not ngrok_url:
        return
        
    password = getpass("Enter your password for Colab: ")
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Extract hostname and port from the ngrok URL
        match = re.match(r"tcp://(.+):(\d+)", ngrok_url)
        if not match:
            logging.error(f"Invalid ngrok URL format: {ngrok_url}")
            return
            
        hostname, port = match.groups()
        port = int(port)
        username = "root"

        logging.info(f"Connecting to {hostname}:{port} as {username}...")
        client.connect(hostname, port=port, username=username, password=password)

        logging.info("Installing OpenVPN and Easy-RSA on Colab...")
        execute_ssh_command(client, 'apt-get update && apt-get install -y openvpn easy-rsa')

        logging.info("Setting up OpenVPN server on Colab...")
        
        execute_ssh_command(client, 'mkdir -p /etc/openvpn/easy-rsa')
        execute_ssh_command(client, 'cp -r /usr/share/easy-rsa/* /etc/openvpn/easy-rsa/')
        
        vars_file = """
set_var EASYRSA_REQ_COUNTRY    "US"
set_var EASYRSA_REQ_PROVINCE   "California"
set_var EASYRSA_REQ_CITY       "San Francisco"
set_var EASYRSA_REQ_ORG        "Copyleft"
set_var EASYRSA_REQ_EMAIL      "me@example.net"
set_var EASYRSA_REQ_OU         "MyOrganizationalUnit"
set_var EASYRSA_BATCH          "1"
"""
        execute_ssh_command(client, f"echo '{vars_file}' > /etc/openvpn/easy-rsa/vars")

        execute_ssh_command(client, """
cd /etc/openvpn/easy-rsa
./easyrsa init-pki
./easyrsa --batch build-ca nopass
./easyrsa --batch gen-req server nopass
./easyrsa --batch sign-req server server
./easyrsa gen-dh
""")

        execute_ssh_command(client, 'cp /etc/openvpn/easy-rsa/pki/ca.crt /etc/openvpn/')
        execute_ssh_command(client, 'cp /etc/openvpn/easy-rsa/pki/issued/server.crt /etc/openvpn/')
        execute_ssh_command(client, 'cp /etc/openvpn/easy-rsa/pki/private/server.key /etc/openvpn/')
        execute_ssh_command(client, 'cp /etc/openvpn/easy-rsa/pki/dh.pem /etc/openvpn/')
        
        server_config = generate_server_config()
        execute_ssh_command(client, f"echo '{server_config}' > /etc/openvpn/server.conf")
        
        execute_ssh_command(client, 'openvpn --config /etc/openvpn/server.conf &')

        execute_ssh_command(client, """
cd /etc/openvpn/easy-rsa
./easyrsa --batch gen-req client nopass
./easyrsa --batch sign-req client client
""")
        
        colab_ip, _ = execute_ssh_command(client, 'curl -s ifconfig.me')
        colab_ip = colab_ip.strip()

        execute_ssh_command(client, f"""
cat <<EOF > /root/colab.ovpn
client
dev tun
proto udp
remote {colab_ip} 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
verb 3
<ca>
$(cat /etc/openvpn/ca.crt)
</ca>
<cert>
$(cat /etc/openvpn/easy-rsa/pki/issued/client.crt)
</cert>
<key>
$(cat /etc/openvpn/easy-rsa/pki/private/client.key)
</key>
EOF
""")

        logging.info("Downloading client configuration file...")
        with SCPClient(client.get_transport()) as scp:
            scp.get('/root/colab.ovpn', 'colab.ovpn')

        client.close()
        
        logging.info("Generated colab.ovpn")
        
        logging.info("Opening OpenVPN client with the generated configuration file...")
        open_ovpn_file('colab.ovpn')

    except paramiko.AuthenticationException as e:
        logging.error(f"Authentication failed: {e}")
    except paramiko.SSHException as e:
        logging.error(f"SSH connection failed: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
