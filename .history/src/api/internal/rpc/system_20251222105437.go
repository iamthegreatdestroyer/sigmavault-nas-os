// Package rpc provides system-related RPC methods.
package rpc

import (
	"context"
	"time"
)

// SystemStatus represents the overall system status from the RPC engine.
type SystemStatus struct {
	Hostname    string        `json:"hostname"`
	Platform    string        `json:"platform"`
	Uptime      time.Duration `json:"uptime"`
	CPUUsage    float64       `json:"cpu_usage"`
	MemoryUsage MemoryUsage   `json:"memory_usage"`
	DiskUsage   []DiskUsage   `json:"disk_usage"`
	LoadAverage LoadAverage   `json:"load_average"`
	Timestamp   time.Time     `json:"timestamp"`
}

// MemoryUsage represents memory utilization metrics.
type MemoryUsage struct {
	Total       uint64  `json:"total"`
	Used        uint64  `json:"used"`
	Free        uint64  `json:"free"`
	Available   uint64  `json:"available"`
	UsedPercent float64 `json:"used_percent"`
	Cached      uint64  `json:"cached"`
	Buffers     uint64  `json:"buffers"`
	SwapTotal   uint64  `json:"swap_total"`
	SwapUsed    uint64  `json:"swap_used"`
	SwapFree    uint64  `json:"swap_free"`
}

// DiskUsage represents disk utilization for a mount point.
type DiskUsage struct {
	MountPoint  string  `json:"mount_point"`
	Device      string  `json:"device"`
	Filesystem  string  `json:"filesystem"`
	Total       uint64  `json:"total"`
	Used        uint64  `json:"used"`
	Free        uint64  `json:"free"`
	UsedPercent float64 `json:"used_percent"`
}

// LoadAverage represents system load averages.
type LoadAverage struct {
	Load1  float64 `json:"load1"`
	Load5  float64 `json:"load5"`
	Load15 float64 `json:"load15"`
}

// CPUInfo represents CPU information.
type CPUInfo struct {
	Model       string  `json:"model"`
	Cores       int     `json:"cores"`
	Threads     int     `json:"threads"`
	Frequency   float64 `json:"frequency"`
	Temperature float64 `json:"temperature,omitempty"`
	Usage       float64 `json:"usage"`
}

// NetworkInterface represents a network interface.
type NetworkInterface struct {
	Name       string   `json:"name"`
	MacAddress string   `json:"mac_address"`
	IPv4       []string `json:"ipv4"`
	IPv6       []string `json:"ipv6"`
	MTU        int      `json:"mtu"`
	Speed      int64    `json:"speed"` // in Mbps
	State      string   `json:"state"` // up, down, unknown
	RxBytes    uint64   `json:"rx_bytes"`
	TxBytes    uint64   `json:"tx_bytes"`
	RxPackets  uint64   `json:"rx_packets"`
	TxPackets  uint64   `json:"tx_packets"`
	RxErrors   uint64   `json:"rx_errors"`
	TxErrors   uint64   `json:"tx_errors"`
}

// ServiceStatus represents the status of a system service.
type ServiceStatus struct {
	Name        string    `json:"name"`
	DisplayName string    `json:"display_name"`
	Status      string    `json:"status"` // running, stopped, starting, stopping
	Enabled     bool      `json:"enabled"`
	PID         int       `json:"pid,omitempty"`
	Memory      uint64    `json:"memory,omitempty"`
	CPU         float64   `json:"cpu,omitempty"`
	StartTime   time.Time `json:"start_time,omitempty"`
	Restarts    int       `json:"restarts"`
}

// SystemMetrics represents detailed system metrics.
type SystemMetrics struct {
	CPU         []CPUInfo          `json:"cpu"`
	Memory      MemoryUsage        `json:"memory"`
	Disks       []DiskUsage        `json:"disks"`
	Network     []NetworkInterface `json:"network"`
	LoadAverage LoadAverage        `json:"load_average"`
	Processes   int                `json:"processes"`
	Timestamp   time.Time          `json:"timestamp"`
}

// GetSystemStatusParams are parameters for GetSystemStatus.
type GetSystemStatusParams struct {
	IncludeDisks   bool `json:"include_disks,omitempty"`
	IncludeNetwork bool `json:"include_network,omitempty"`
}

// GetSystemStatus retrieves the current system status from the RPC engine.
func (c *Client) GetSystemStatus(ctx context.Context, params *GetSystemStatusParams) (*SystemStatus, error) {
	var result SystemStatus
	if err := c.Call(ctx, "system.status", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetSystemMetrics retrieves detailed system metrics.
func (c *Client) GetSystemMetrics(ctx context.Context) (*SystemMetrics, error) {
	var result SystemMetrics
	if err := c.Call(ctx, "system.metrics", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetCPUInfo retrieves CPU information.
func (c *Client) GetCPUInfo(ctx context.Context) ([]CPUInfo, error) {
	var result []CPUInfo
	if err := c.Call(ctx, "system.cpu", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetMemoryUsage retrieves memory usage information.
func (c *Client) GetMemoryUsage(ctx context.Context) (*MemoryUsage, error) {
	var result MemoryUsage
	if err := c.Call(ctx, "system.memory", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetDiskUsage retrieves disk usage for all mount points.
func (c *Client) GetDiskUsage(ctx context.Context) ([]DiskUsage, error) {
	var result []DiskUsage
	if err := c.Call(ctx, "system.disks", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetLoadAverage retrieves system load averages.
func (c *Client) GetLoadAverage(ctx context.Context) (*LoadAverage, error) {
	var result LoadAverage
	if err := c.Call(ctx, "system.load", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetNetworkInterfaces retrieves network interface information.
func (c *Client) GetNetworkInterfaces(ctx context.Context) ([]NetworkInterface, error) {
	var result []NetworkInterface
	if err := c.Call(ctx, "system.network", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// ListServicesParams are parameters for ListServices.
type ListServicesParams struct {
	Filter string `json:"filter,omitempty"` // Filter by name pattern
	Status string `json:"status,omitempty"` // Filter by status: running, stopped, all
}

// ListServices retrieves the status of system services.
func (c *Client) ListServices(ctx context.Context, params *ListServicesParams) ([]ServiceStatus, error) {
	var result []ServiceStatus
	if err := c.Call(ctx, "system.services", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// ServiceActionParams are parameters for service control actions.
type ServiceActionParams struct {
	Name string `json:"name"`
}

// StartService starts a system service.
func (c *Client) StartService(ctx context.Context, name string) error {
	params := ServiceActionParams{Name: name}
	return c.Call(ctx, "system.service.start", params, nil)
}

// StopService stops a system service.
func (c *Client) StopService(ctx context.Context, name string) error {
	params := ServiceActionParams{Name: name}
	return c.Call(ctx, "system.service.stop", params, nil)
}

// RestartService restarts a system service.
func (c *Client) RestartService(ctx context.Context, name string) error {
	params := ServiceActionParams{Name: name}
	return c.Call(ctx, "system.service.restart", params, nil)
}

// GetServiceStatus retrieves the status of a specific service.
func (c *Client) GetServiceStatus(ctx context.Context, name string) (*ServiceStatus, error) {
	params := ServiceActionParams{Name: name}
	var result ServiceStatus
	if err := c.Call(ctx, "system.service.status", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// RebootParams are parameters for system reboot.
type RebootParams struct {
	Delay   int    `json:"delay,omitempty"`   // Delay in seconds before reboot
	Message string `json:"message,omitempty"` // Broadcast message
}

// Reboot initiates a system reboot.
func (c *Client) Reboot(ctx context.Context, params *RebootParams) error {
	return c.Call(ctx, "system.reboot", params, nil)
}

// Shutdown initiates a system shutdown.
func (c *Client) Shutdown(ctx context.Context, params *RebootParams) error {
	return c.Call(ctx, "system.shutdown", params, nil)
}
