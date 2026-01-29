# SigmaVault NAS OS - Engined

The Python RPC engine for SigmaVault NAS OS, providing:

- **Agent Swarm Management**: 40 AI agents with tiered capabilities
- **Compression Engine**: AI-powered compression with 70%+ ratios
- **RPC API**: JSON-RPC 2.0 interface for Go API integration

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the engine
python -m engined.main
```

## API Endpoints

- `http://localhost:8002/api/v1/rpc` - JSON-RPC endpoint
- `http://localhost:8002/health` - Health check

## RPC Methods

### System

- `system.status` - Get system status

### Agents

- `agents.list` - List all agents
- `agents.status` - Get swarm status

### Compression

- `compression.compress.data` - Compress data in-memory
- `compression.decompress.data` - Decompress data
- `compression.queue.submit` - Submit async compression job
- `compression.queue.status` - Get job status
- `compression.queue.running` - Get running jobs
