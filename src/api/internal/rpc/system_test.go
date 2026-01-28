// Package rpc provides tests for system-related RPC methods.
package rpc

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestSystemStatus_JSONSerialization(t *testing.T) {
	status := SystemStatus{
		Hostname: "sigmavault-nas",
		Platform: "linux",
		Uptime:   time.Hour * 24 * 7,
		CPUUsage: 35.5,
		MemoryUsage: MemoryUsage{
			Total:       16 * 1024 * 1024 * 1024,
			Used:        8 * 1024 * 1024 * 1024,
			Free:        8 * 1024 * 1024 * 1024,
			Available:   10 * 1024 * 1024 * 1024,
			UsedPercent: 50.0,
		},
		LoadAverage: LoadAverage{
			Load1:  1.5,
			Load5:  1.2,
			Load15: 0.8,
		},
		Timestamp: time.Now(),
	}

	data, err := json.Marshal(status)
	require.NoError(t, err)

	var parsed SystemStatus
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, status.Hostname, parsed.Hostname)
	assert.Equal(t, status.Platform, parsed.Platform)
	assert.Equal(t, status.CPUUsage, parsed.CPUUsage)
}

func TestMemoryUsage_JSONSerialization(t *testing.T) {
	memory := MemoryUsage{
		Total:       32 * 1024 * 1024 * 1024,
		Used:        16 * 1024 * 1024 * 1024,
		Free:        8 * 1024 * 1024 * 1024,
		Available:   12 * 1024 * 1024 * 1024,
		UsedPercent: 50.0,
		Cached:      4 * 1024 * 1024 * 1024,
		Buffers:     2 * 1024 * 1024 * 1024,
		SwapTotal:   8 * 1024 * 1024 * 1024,
		SwapUsed:    1 * 1024 * 1024 * 1024,
		SwapFree:    7 * 1024 * 1024 * 1024,
	}

	data, err := json.Marshal(memory)
	require.NoError(t, err)

	var parsed MemoryUsage
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, memory.Total, parsed.Total)
	assert.Equal(t, memory.Used, parsed.Used)
	assert.Equal(t, memory.Free, parsed.Free)
	assert.Equal(t, memory.Available, parsed.Available)
	assert.Equal(t, memory.UsedPercent, parsed.UsedPercent)
	assert.Equal(t, memory.SwapTotal, parsed.SwapTotal)
}

func TestDiskUsage_JSONSerialization(t *testing.T) {
	disk := DiskUsage{
		MountPoint:  "/",
		Device:      "/dev/sda1",
		Filesystem:  "ext4",
		Total:       500 * 1024 * 1024 * 1024,
		Used:        200 * 1024 * 1024 * 1024,
		Free:        300 * 1024 * 1024 * 1024,
		UsedPercent: 40.0,
	}

	data, err := json.Marshal(disk)
	require.NoError(t, err)

	var parsed DiskUsage
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, disk.MountPoint, parsed.MountPoint)
	assert.Equal(t, disk.Device, parsed.Device)
	assert.Equal(t, disk.Filesystem, parsed.Filesystem)
	assert.Equal(t, disk.Total, parsed.Total)
	assert.Equal(t, disk.UsedPercent, parsed.UsedPercent)
}

func TestLoadAverage_JSONSerialization(t *testing.T) {
	load := LoadAverage{
		Load1:  2.5,
		Load5:  1.8,
		Load15: 1.2,
	}

	data, err := json.Marshal(load)
	require.NoError(t, err)

	var parsed LoadAverage
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, load.Load1, parsed.Load1)
	assert.Equal(t, load.Load5, parsed.Load5)
	assert.Equal(t, load.Load15, parsed.Load15)
}

func TestCPUInfo_JSONSerialization(t *testing.T) {
	cpu := CPUInfo{
		Model:       "AMD Ryzen 9 5950X",
		Cores:       16,
		Threads:     32,
		Frequency:   3400.0,
		Temperature: 45.5,
		Usage:       25.0,
	}

	data, err := json.Marshal(cpu)
	require.NoError(t, err)

	var parsed CPUInfo
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, cpu.Model, parsed.Model)
	assert.Equal(t, cpu.Cores, parsed.Cores)
	assert.Equal(t, cpu.Threads, parsed.Threads)
	assert.Equal(t, cpu.Frequency, parsed.Frequency)
	assert.Equal(t, cpu.Temperature, parsed.Temperature)
	assert.Equal(t, cpu.Usage, parsed.Usage)
}

func TestNetworkInterface_JSONSerialization(t *testing.T) {
	iface := NetworkInterface{
		Name:       "eth0",
		MacAddress: "00:11:22:33:44:55",
		IPv4:       []string{"192.168.1.100"},
		IPv6:       []string{"fe80::1"},
		MTU:        1500,
		Speed:      10000,
		State:      "up",
		RxBytes:    1024 * 1024 * 1024,
		TxBytes:    512 * 1024 * 1024,
		RxPackets:  1000000,
		TxPackets:  500000,
		RxErrors:   0,
		TxErrors:   0,
	}

	data, err := json.Marshal(iface)
	require.NoError(t, err)

	var parsed NetworkInterface
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, iface.Name, parsed.Name)
	assert.Equal(t, iface.MacAddress, parsed.MacAddress)
	assert.Equal(t, iface.IPv4, parsed.IPv4)
	assert.Equal(t, iface.IPv6, parsed.IPv6)
	assert.Equal(t, iface.State, parsed.State)
	assert.Equal(t, iface.Speed, parsed.Speed)
}

func TestServiceStatus_JSONSerialization(t *testing.T) {
	now := time.Now()
	service := ServiceStatus{
		Name:        "sigmavault-engine",
		DisplayName: "SigmaVault RPC Engine",
		Status:      "running",
		Enabled:     true,
		PID:         1234,
		Memory:      100 * 1024 * 1024,
		CPU:         5.5,
		StartTime:   now,
		Restarts:    0,
	}

	data, err := json.Marshal(service)
	require.NoError(t, err)

	var parsed ServiceStatus
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, service.Name, parsed.Name)
	assert.Equal(t, service.DisplayName, parsed.DisplayName)
	assert.Equal(t, service.Status, parsed.Status)
	assert.Equal(t, service.Enabled, parsed.Enabled)
	assert.Equal(t, service.PID, parsed.PID)
}

func TestServiceStatus_Values(t *testing.T) {
	validStatuses := []string{"running", "stopped", "starting", "stopping"}

	for _, status := range validStatuses {
		t.Run(status, func(t *testing.T) {
			service := ServiceStatus{
				Name:   "test-service",
				Status: status,
			}
			assert.Equal(t, status, service.Status)
		})
	}
}

func TestNetworkInterfaceState_Values(t *testing.T) {
	validStates := []string{"up", "down", "unknown"}

	for _, state := range validStates {
		t.Run(state, func(t *testing.T) {
			iface := NetworkInterface{
				Name:  "eth0",
				State: state,
			}
			assert.Equal(t, state, iface.State)
		})
	}
}

func TestSystemMetrics_Full(t *testing.T) {
	metrics := SystemMetrics{
		CPU: []CPUInfo{
			{Model: "Intel i9", Cores: 8, Threads: 16, Usage: 45.0},
		},
		Memory: MemoryUsage{
			Total:       32 * 1024 * 1024 * 1024,
			UsedPercent: 65.0,
		},
		Disks: []DiskUsage{
			{MountPoint: "/", Total: 1024 * 1024 * 1024 * 1024},
		},
		Network: []NetworkInterface{
			{Name: "eth0", State: "up", Speed: 10000},
		},
		LoadAverage: LoadAverage{Load1: 1.0, Load5: 0.8, Load15: 0.5},
		Processes:   150,
	}

	data, err := json.Marshal(metrics)
	require.NoError(t, err)

	var parsed SystemMetrics
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, 1, len(parsed.CPU))
	assert.Equal(t, 1, len(parsed.Disks))
	assert.Equal(t, 1, len(parsed.Network))
	assert.Equal(t, 150, parsed.Processes)
}

func TestMultipleDiskUsage(t *testing.T) {
	disks := []DiskUsage{
		{MountPoint: "/", Device: "/dev/sda1", Total: 256 * 1024 * 1024 * 1024},
		{MountPoint: "/home", Device: "/dev/sda2", Total: 1024 * 1024 * 1024 * 1024},
		{MountPoint: "/data", Device: "/dev/sdb1", Total: 4 * 1024 * 1024 * 1024 * 1024},
	}

	status := SystemStatus{
		Hostname:  "nas-server",
		DiskUsage: disks,
	}

	data, err := json.Marshal(status)
	require.NoError(t, err)

	var parsed SystemStatus
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, 3, len(parsed.DiskUsage))
	assert.Equal(t, "/", parsed.DiskUsage[0].MountPoint)
	assert.Equal(t, "/home", parsed.DiskUsage[1].MountPoint)
	assert.Equal(t, "/data", parsed.DiskUsage[2].MountPoint)
}

func TestMultipleNetworkInterfaces(t *testing.T) {
	interfaces := []NetworkInterface{
		{Name: "lo", State: "up", IPv4: []string{"127.0.0.1"}},
		{Name: "eth0", State: "up", IPv4: []string{"192.168.1.100"}},
		{Name: "eth1", State: "down", IPv4: []string{}},
		{Name: "docker0", State: "up", IPv4: []string{"172.17.0.1"}},
	}

	metrics := SystemMetrics{
		Network: interfaces,
	}

	data, err := json.Marshal(metrics)
	require.NoError(t, err)

	var parsed SystemMetrics
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, 4, len(parsed.Network))

	// Find eth0
	var eth0 *NetworkInterface
	for i := range parsed.Network {
		if parsed.Network[i].Name == "eth0" {
			eth0 = &parsed.Network[i]
			break
		}
	}
	require.NotNil(t, eth0)
	assert.Equal(t, "up", eth0.State)
	assert.Contains(t, eth0.IPv4, "192.168.1.100")
}

func TestMemoryUsage_Calculations(t *testing.T) {
	memory := MemoryUsage{
		Total:       16 * 1024 * 1024 * 1024, // 16 GB
		Used:        10 * 1024 * 1024 * 1024, // 10 GB
		Free:        2 * 1024 * 1024 * 1024,  // 2 GB
		Available:   6 * 1024 * 1024 * 1024,  // 6 GB
		Cached:      4 * 1024 * 1024 * 1024,  // 4 GB
		UsedPercent: 62.5,
	}

	// Verify percentages
	calculatedPercent := float64(memory.Used) / float64(memory.Total) * 100
	assert.InDelta(t, calculatedPercent, memory.UsedPercent, 1.0)

	// Available should be >= Free
	assert.GreaterOrEqual(t, memory.Available, memory.Free)
}

func TestDiskUsage_Calculations(t *testing.T) {
	disk := DiskUsage{
		Total:       1000 * 1024 * 1024 * 1024, // 1 TB
		Used:        400 * 1024 * 1024 * 1024,  // 400 GB
		Free:        600 * 1024 * 1024 * 1024,  // 600 GB
		UsedPercent: 40.0,
	}

	// Verify Used + Free = Total
	assert.Equal(t, disk.Total, disk.Used+disk.Free)

	// Verify percentage
	calculatedPercent := float64(disk.Used) / float64(disk.Total) * 100
	assert.InDelta(t, calculatedPercent, disk.UsedPercent, 0.1)
}
