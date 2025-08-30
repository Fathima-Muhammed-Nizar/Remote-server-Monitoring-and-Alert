# Remote-server-Monitoring-and-Alert
## Overview
This project monitors the health of remote servers by checking **disk usage**, **memory utilization**, and **system load**. It automatically sends **email alerts** when thresholds are exceeded. The system supports **multiple remote hosts**, SSH-based checks, and a **TEST_MODE** for simulation/testing without real servers.

## Tech Stack
- **Python 3**  
- **Paramiko** – SSH connections to remote servers  
- **smtplib, email.mime** – Email notifications  
- **JSON** – Hosts configuration  
- **Linux/macOS** – Cron scheduling  

## Installation

1. Clone the repository:
git clone https://github.com/yourusername/remote-monitor.git
cd remote-monitor

2. Install required Python libraries:
pip install -r requirements.txt


Run the script normally (real SSH connections):
python3 monitor.py

Run in test mode (no SSH required):
TEST_MODE=1 python3 monitor.py


