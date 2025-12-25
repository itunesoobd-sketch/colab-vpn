# Colab VPN

This project allows you to use a Google Colab notebook as a system-wide VPN service for Windows 11. By running a Python script, you can automatically set up an OpenVPN server on a Colab instance and generate a client configuration file to connect to it.

## How it Works

The `vpn_setup.py` script performs the following steps:

1.  **Starts an ngrok tunnel.** It uses the `pyngrok` library to create an SSH tunnel to the Colab notebook.
2.  **Connects to a Google Colab notebook via SSH.** It uses the `paramiko` library to establish an SSH connection to the Colab instance.
3.  **Installs OpenVPN and Easy-RSA.** The script installs the necessary software on the Colab instance to create a VPN server.
4.  **Configures the OpenVPN server.** It generates the server configuration files and certificates using Easy-RSA.
5.  **Generates a client configuration file.** The script creates an OpenVPN client configuration file (`.ovpn`) that you can use to connect to the VPN server.
6.  **Transfers the client configuration file to your local machine.** It uses the `scp` protocol to securely transfer the `.ovpn` file from the Colab instance to your local machine.
7.  **Opens the OpenVPN client.** The script automatically opens the generated `.ovpn` file with the default application, which should be your OpenVPN client.

## Prerequisites

- Windows 11
- Python 3.x
- An ngrok account and authentication token
- OpenVPN client installed on your machine. You can download it from the [official website](https://openvpn.net/community-downloads/).

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/colab-vpn.git
   cd colab-vpn
   ```

2. **Install the required Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your ngrok authentication token.**
   - Open the `vpn_setup.py` file and replace `"YOUR_NGROK_AUTHTOKEN"` with your ngrok authentication token.

4. **Run the script.**
   - Open your terminal or command prompt and run the script:
     ```bash
     python vpn_setup.py
     ```
   - You will be prompted to enter the password for the `root` user on your Colab instance. The default password is `colab`.

## Connecting to the VPN

Once the script finishes, it will create a file named `colab.ovpn` in the same directory and automatically open it with your default OpenVPN client.

To connect to the VPN, simply click the "Connect" button in your OpenVPN client.

## Disclaimer

This project is for educational purposes only. Please be aware of the terms of service of Google Colab and ngrok.
