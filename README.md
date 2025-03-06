
#  Peer to Peer File Synchronization Project

## Overview
This project is a Docker-based peer-to-peer (P2P) file synchronization system. It creates multiple nodes that can communicate and sync files within an isolated network. Each node runs inside a Docker container and syncs files through a designated directory.
## Project Set Up
Prerequisites
- Docker installed
- Docker Compose installed


## Installation and Running the Project

Install my-project with npm

```bash
# Clone this repository
git clone <repository_url>
cd <project_directory>

# Ensure Docker is running

# Build and start the project using Docker Compose
docker-compose up --build

# Verify that the containers are running
docker ps

# Stop the containers when finished
docker-compose down
```
    
## Project Structure
```bash
project_directory/
├── clientServer.py     # Main Python script for synchronization
├── Dockerfile          # Docker build instructions
├── docker-compose.yml  # Configuration for multiple nodes
├── sync/               # Directory containing node-specific sync folders
│   ├── node1/
│   ├── node2/
│   ├── node3/
│   ├── node4/
│
└── README.md           # Project documentation
```
## How it Works
- Nodes synchronize files using a shared volume (./sync/nodeX:/sync).
- The clientServer.py script handles file synchronization between nodes.
- Containers communicate over the syncnet network.
## Collaborators
- Deanna Solis
- Danniella Martinez

