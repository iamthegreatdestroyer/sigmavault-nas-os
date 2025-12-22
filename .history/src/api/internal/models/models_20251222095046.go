// Package models defines the data structures used throughout the API.
package models

import "time"

// User represents a system user.
type User struct {
	ID        string    `json:"id"`
	Username  string    `json:"username"`
	Email     string    `json:"email"`
	Role      string    `json:"role"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// StoragePool represents a ZFS storage pool.
type StoragePool struct {
	ID         string  `json:"id"`
	Name       string  `json:"name"`
	Status     string  `json:"status"` // healthy, degraded, critical, unknown
	TotalBytes uint64  `json:"total_bytes"`
	UsedBytes  uint64  `json:"used_bytes"`
	FreeBytes  uint64  `json:"free_bytes"`
	UsedPct    float64 `json:"used_pct"`
}

// SystemStatus represents the overall system status.
type SystemStatus struct {
	Hostname     string    `json:"hostname"`
	Uptime       int64     `json:"uptime_seconds"`
	CPUUsage     float64   `json:"cpu_usage_pct"`
	MemoryTotal  uint64    `json:"memory_total_bytes"`
	MemoryUsed   uint64    `json:"memory_used_bytes"`
	MemoryUsePct float64   `json:"memory_used_pct"`
	LoadAvg      []float64 `json:"load_avg"`
	Timestamp    time.Time `json:"timestamp"`
}

// NetworkInterface represents a network interface.
type NetworkInterface struct {
	Name        string `json:"name"`
	Status      string `json:"status"` // up, down
	IPAddress   string `json:"ip_address"`
	MacAddress  string `json:"mac_address"`
	Speed       uint64 `json:"speed_mbps"`
	RxBytes     uint64 `json:"rx_bytes"`
	TxBytes     uint64 `json:"tx_bytes"`
	RxBytesRate uint64 `json:"rx_bytes_rate"`
	TxBytesRate uint64 `json:"tx_bytes_rate"`
}

// Service represents a system service.
type Service struct {
	Name      string    `json:"name"`
	Status    string    `json:"status"` // running, stopped, failed
	Enabled   bool      `json:"enabled"`
	StartedAt time.Time `json:"started_at,omitempty"`
}

// Share represents a file share (SMB/NFS).
type Share struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Path        string    `json:"path"`
	Type        string    `json:"type"` // smb, nfs, both
	Description string    `json:"description"`
	ReadOnly    bool      `json:"read_only"`
	AllowedIPs  []string  `json:"allowed_ips,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// CompressionJob represents an AI compression job.
type CompressionJob struct {
	ID               string    `json:"id"`
	Status           string    `json:"status"` // pending, running, completed, failed
	SourcePath       string    `json:"source_path"`
	DestPath         string    `json:"dest_path,omitempty"`
	OriginalSize     uint64    `json:"original_size_bytes"`
	CompressedSize   uint64    `json:"compressed_size_bytes,omitempty"`
	CompressionRatio float64   `json:"compression_ratio,omitempty"`
	Algorithm        string    `json:"algorithm"`
	Progress         float64   `json:"progress_pct"`
	StartedAt        time.Time `json:"started_at,omitempty"`
	CompletedAt      time.Time `json:"completed_at,omitempty"`
	Error            string    `json:"error,omitempty"`
}

// EncryptionKey represents a quantum-resistant encryption key.
type EncryptionKey struct {
	ID         string    `json:"id"`
	Name       string    `json:"name"`
	Algorithm  string    `json:"algorithm"` // kyber, dilithium, sphincs
	KeySize    int       `json:"key_size_bits"`
	Purpose    string    `json:"purpose"` // storage, transport, signing
	CreatedAt  time.Time `json:"created_at"`
	ExpiresAt  time.Time `json:"expires_at,omitempty"`
	LastUsedAt time.Time `json:"last_used_at,omitempty"`
}

// VPNPeer represents a PhantomMesh VPN peer.
type VPNPeer struct {
	ID            string    `json:"id"`
	Name          string    `json:"name"`
	PublicKey     string    `json:"public_key"`
	Endpoint      string    `json:"endpoint,omitempty"`
	AllowedIPs    []string  `json:"allowed_ips"`
	Status        string    `json:"status"` // connected, disconnected, handshaking
	LastHandshake time.Time `json:"last_handshake,omitempty"`
	RxBytes       uint64    `json:"rx_bytes"`
	TxBytes       uint64    `json:"tx_bytes"`
}

// AgentStatus represents the status of an AI agent in the swarm.
type AgentStatus struct {
	ID             string    `json:"id"`
	Name           string    `json:"name"`
	Type           string    `json:"type"`   // compression, encryption, analysis, etc.
	Status         string    `json:"status"` // active, idle, error
	TasksQueued    int       `json:"tasks_queued"`
	TasksCompleted int       `json:"tasks_completed"`
	CPUUsage       float64   `json:"cpu_usage_pct"`
	MemoryUsage    uint64    `json:"memory_usage_bytes"`
	LastActive     time.Time `json:"last_active"`
}

// Notification represents a system notification.
type Notification struct {
	ID        string    `json:"id"`
	Type      string    `json:"type"` // info, success, warning, error
	Title     string    `json:"title"`
	Message   string    `json:"message"`
	Read      bool      `json:"read"`
	CreatedAt time.Time `json:"created_at"`
}
