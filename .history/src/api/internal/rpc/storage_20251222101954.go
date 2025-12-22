// Package rpc provides storage-related RPC methods.
package rpc

import (
	"context"
	"time"
)

// StoragePool represents a ZFS storage pool.
type StoragePool struct {
	Name        string           `json:"name"`
	GUID        string           `json:"guid"`
	State       string           `json:"state"` // ONLINE, DEGRADED, FAULTED, OFFLINE, UNAVAIL
	Status      string           `json:"status"`
	Size        uint64           `json:"size"`
	Allocated   uint64           `json:"allocated"`
	Free        uint64           `json:"free"`
	Fragmentation int            `json:"fragmentation"`
	Capacity    float64          `json:"capacity"` // percentage used
	Dedup       float64          `json:"dedup"`
	Health      string           `json:"health"`
	Datasets    []Dataset        `json:"datasets,omitempty"`
	VDevs       []VDev           `json:"vdevs,omitempty"`
	Properties  map[string]string `json:"properties,omitempty"`
	ScanStatus  *ScanStatus      `json:"scan_status,omitempty"`
	CreatedAt   time.Time        `json:"created_at"`
}

// VDev represents a virtual device in a pool.
type VDev struct {
	Name     string  `json:"name"`
	Type     string  `json:"type"` // disk, file, mirror, raidz, raidz2, raidz3, spare, log, cache
	State    string  `json:"state"`
	Path     string  `json:"path,omitempty"`
	GUID     string  `json:"guid"`
	Size     uint64  `json:"size"`
	Allocated uint64 `json:"allocated"`
	Children []VDev  `json:"children,omitempty"`
	ReadErrors  uint64 `json:"read_errors"`
	WriteErrors uint64 `json:"write_errors"`
	ChecksumErrors uint64 `json:"checksum_errors"`
}

// Dataset represents a ZFS dataset (filesystem or volume).
type Dataset struct {
	Name          string            `json:"name"`
	Type          string            `json:"type"` // filesystem, volume, snapshot
	Pool          string            `json:"pool"`
	MountPoint    string            `json:"mountpoint,omitempty"`
	Used          uint64            `json:"used"`
	Available     uint64            `json:"available"`
	Referenced    uint64            `json:"referenced"`
	Quota         uint64            `json:"quota,omitempty"`
	Reservation   uint64            `json:"reservation,omitempty"`
	Compression   string            `json:"compression"`
	CompressRatio float64           `json:"compress_ratio"`
	Encryption    string            `json:"encryption,omitempty"`
	Dedup         string            `json:"dedup"`
	Snapshots     []Snapshot        `json:"snapshots,omitempty"`
	Properties    map[string]string `json:"properties,omitempty"`
	CreatedAt     time.Time         `json:"created_at"`
}

// Snapshot represents a ZFS snapshot.
type Snapshot struct {
	Name       string    `json:"name"`
	Dataset    string    `json:"dataset"`
	Used       uint64    `json:"used"`
	Referenced uint64    `json:"referenced"`
	CreatedAt  time.Time `json:"created_at"`
}

// ScanStatus represents the status of a pool scan (scrub/resilver).
type ScanStatus struct {
	Type      string    `json:"type"` // scrub, resilver
	State     string    `json:"state"` // scanning, finished, canceled
	Progress  float64   `json:"progress"`
	Examined  uint64    `json:"examined"`
	Total     uint64    `json:"total"`
	Rate      uint64    `json:"rate"` // bytes per second
	Errors    int       `json:"errors"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time,omitempty"`
	ETA       time.Time `json:"eta,omitempty"`
}

// Disk represents a physical disk.
type Disk struct {
	Name        string   `json:"name"`
	Path        string   `json:"path"`
	Model       string   `json:"model"`
	Serial      string   `json:"serial"`
	Size        uint64   `json:"size"`
	Sector      int      `json:"sector"`
	Type        string   `json:"type"` // hdd, ssd, nvme
	Transport   string   `json:"transport"` // sata, sas, nvme, usb
	Rotational  bool     `json:"rotational"`
	Removable   bool     `json:"removable"`
	Partitions  []Partition `json:"partitions,omitempty"`
	SMART       *SMARTData  `json:"smart,omitempty"`
	InUse       bool     `json:"in_use"`
	Pool        string   `json:"pool,omitempty"`
	Temperature int      `json:"temperature,omitempty"`
}

// Partition represents a disk partition.
type Partition struct {
	Name       string `json:"name"`
	Path       string `json:"path"`
	Number     int    `json:"number"`
	Size       uint64 `json:"size"`
	Start      uint64 `json:"start"`
	Filesystem string `json:"filesystem,omitempty"`
	Label      string `json:"label,omitempty"`
	UUID       string `json:"uuid,omitempty"`
	MountPoint string `json:"mountpoint,omitempty"`
}

// SMARTData represents SMART monitoring data.
type SMARTData struct {
	Healthy         bool              `json:"healthy"`
	Temperature     int               `json:"temperature"`
	PowerOnHours    uint64            `json:"power_on_hours"`
	PowerCycles     uint64            `json:"power_cycles"`
	ReallocatedSectors int            `json:"reallocated_sectors"`
	PendingSectors  int               `json:"pending_sectors"`
	Attributes      map[string]int    `json:"attributes,omitempty"`
	LastTest        *SMARTTest        `json:"last_test,omitempty"`
	CollectedAt     time.Time         `json:"collected_at"`
}

// SMARTTest represents SMART self-test results.
type SMARTTest struct {
	Type      string    `json:"type"` // short, long, conveyance
	Status    string    `json:"status"`
	Progress  int       `json:"progress"`
	Remaining int       `json:"remaining"` // hours
	StartedAt time.Time `json:"started_at"`
}

// Share represents a network share (SMB/NFS).
type Share struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Path        string            `json:"path"`
	Protocol    string            `json:"protocol"` // smb, nfs
	Description string            `json:"description,omitempty"`
	Enabled     bool              `json:"enabled"`
	ReadOnly    bool              `json:"read_only"`
	GuestAccess bool              `json:"guest_access"`
	Users       []string          `json:"users,omitempty"`
	Groups      []string          `json:"groups,omitempty"`
	Options     map[string]string `json:"options,omitempty"`
	CreatedAt   time.Time         `json:"created_at"`
	ModifiedAt  time.Time         `json:"modified_at"`
}

// ListPoolsParams are parameters for ListPools.
type ListPoolsParams struct {
	IncludeDatasets bool `json:"include_datasets,omitempty"`
	IncludeVDevs    bool `json:"include_vdevs,omitempty"`
}

// ListPools retrieves all storage pools.
func (c *Client) ListPools(ctx context.Context, params *ListPoolsParams) ([]StoragePool, error) {
	var result []StoragePool
	if err := c.Call(ctx, "storage.pools.list", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetPoolParams are parameters for GetPool.
type GetPoolParams struct {
	Name string `json:"name"`
}

// GetPool retrieves a specific storage pool.
func (c *Client) GetPool(ctx context.Context, name string) (*StoragePool, error) {
	params := GetPoolParams{Name: name}
	var result StoragePool
	if err := c.Call(ctx, "storage.pools.get", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CreatePoolParams are parameters for creating a pool.
type CreatePoolParams struct {
	Name        string            `json:"name"`
	VDevs       []CreateVDevParam `json:"vdevs"`
	Properties  map[string]string `json:"properties,omitempty"`
	MountPoint  string            `json:"mountpoint,omitempty"`
	Encryption  *EncryptionParams `json:"encryption,omitempty"`
}

// CreateVDevParam represents a vdev configuration for pool creation.
type CreateVDevParam struct {
	Type   string   `json:"type"` // disk, mirror, raidz, raidz2, raidz3
	Disks  []string `json:"disks"`
}

// EncryptionParams are encryption settings for pool/dataset creation.
type EncryptionParams struct {
	Algorithm  string `json:"algorithm,omitempty"` // aes-256-gcm, aes-256-ccm
	KeyFormat  string `json:"key_format,omitempty"` // passphrase, raw, hex
	Passphrase string `json:"passphrase,omitempty"`
	KeyFile    string `json:"key_file,omitempty"`
}

// CreatePool creates a new storage pool.
func (c *Client) CreatePool(ctx context.Context, params *CreatePoolParams) (*StoragePool, error) {
	var result StoragePool
	if err := c.Call(ctx, "storage.pools.create", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// DestroyPoolParams are parameters for destroying a pool.
type DestroyPoolParams struct {
	Name  string `json:"name"`
	Force bool   `json:"force,omitempty"`
}

// DestroyPool destroys a storage pool.
func (c *Client) DestroyPool(ctx context.Context, name string, force bool) error {
	params := DestroyPoolParams{Name: name, Force: force}
	return c.Call(ctx, "storage.pools.destroy", params, nil)
}

// ScrubPoolParams are parameters for scrubbing a pool.
type ScrubPoolParams struct {
	Name string `json:"name"`
	Stop bool   `json:"stop,omitempty"`
}

// ScrubPool starts or stops a pool scrub.
func (c *Client) ScrubPool(ctx context.Context, name string, stop bool) error {
	params := ScrubPoolParams{Name: name, Stop: stop}
	return c.Call(ctx, "storage.pools.scrub", params, nil)
}

// ListDisks retrieves all available disks.
func (c *Client) ListDisks(ctx context.Context) ([]Disk, error) {
	var result []Disk
	if err := c.Call(ctx, "storage.disks.list", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetDiskParams are parameters for GetDisk.
type GetDiskParams struct {
	Name string `json:"name"`
}

// GetDisk retrieves information about a specific disk.
func (c *Client) GetDisk(ctx context.Context, name string) (*Disk, error) {
	params := GetDiskParams{Name: name}
	var result Disk
	if err := c.Call(ctx, "storage.disks.get", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetDiskSMART retrieves SMART data for a disk.
func (c *Client) GetDiskSMART(ctx context.Context, name string) (*SMARTData, error) {
	params := GetDiskParams{Name: name}
	var result SMARTData
	if err := c.Call(ctx, "storage.disks.smart", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListDatasetsParams are parameters for ListDatasets.
type ListDatasetsParams struct {
	Pool            string `json:"pool,omitempty"`
	IncludeSnapshots bool  `json:"include_snapshots,omitempty"`
	Recursive       bool   `json:"recursive,omitempty"`
}

// ListDatasets retrieves datasets.
func (c *Client) ListDatasets(ctx context.Context, params *ListDatasetsParams) ([]Dataset, error) {
	var result []Dataset
	if err := c.Call(ctx, "storage.datasets.list", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// CreateDatasetParams are parameters for creating a dataset.
type CreateDatasetParams struct {
	Name        string            `json:"name"`
	Type        string            `json:"type,omitempty"` // filesystem, volume
	Properties  map[string]string `json:"properties,omitempty"`
	Quota       uint64            `json:"quota,omitempty"`
	Reservation uint64            `json:"reservation,omitempty"`
	Encryption  *EncryptionParams `json:"encryption,omitempty"`
}

// CreateDataset creates a new dataset.
func (c *Client) CreateDataset(ctx context.Context, params *CreateDatasetParams) (*Dataset, error) {
	var result Dataset
	if err := c.Call(ctx, "storage.datasets.create", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// DestroyDatasetParams are parameters for destroying a dataset.
type DestroyDatasetParams struct {
	Name      string `json:"name"`
	Recursive bool   `json:"recursive,omitempty"`
	Force     bool   `json:"force,omitempty"`
}

// DestroyDataset destroys a dataset.
func (c *Client) DestroyDataset(ctx context.Context, name string, recursive, force bool) error {
	params := DestroyDatasetParams{Name: name, Recursive: recursive, Force: force}
	return c.Call(ctx, "storage.datasets.destroy", params, nil)
}

// CreateSnapshotParams are parameters for creating a snapshot.
type CreateSnapshotParams struct {
	Dataset   string `json:"dataset"`
	Name      string `json:"name"`
	Recursive bool   `json:"recursive,omitempty"`
}

// CreateSnapshot creates a snapshot.
func (c *Client) CreateSnapshot(ctx context.Context, params *CreateSnapshotParams) (*Snapshot, error) {
	var result Snapshot
	if err := c.Call(ctx, "storage.snapshots.create", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListSharesParams are parameters for ListShares.
type ListSharesParams struct {
	Protocol string `json:"protocol,omitempty"` // smb, nfs, all
}

// ListShares retrieves all network shares.
func (c *Client) ListShares(ctx context.Context, params *ListSharesParams) ([]Share, error) {
	var result []Share
	if err := c.Call(ctx, "storage.shares.list", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// CreateShareParams are parameters for creating a share.
type CreateShareParams struct {
	Name        string            `json:"name"`
	Path        string            `json:"path"`
	Protocol    string            `json:"protocol"`
	Description string            `json:"description,omitempty"`
	ReadOnly    bool              `json:"read_only,omitempty"`
	GuestAccess bool              `json:"guest_access,omitempty"`
	Users       []string          `json:"users,omitempty"`
	Groups      []string          `json:"groups,omitempty"`
	Options     map[string]string `json:"options,omitempty"`
}

// CreateShare creates a new network share.
func (c *Client) CreateShare(ctx context.Context, params *CreateShareParams) (*Share, error) {
	var result Share
	if err := c.Call(ctx, "storage.shares.create", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// DeleteShareParams are parameters for deleting a share.
type DeleteShareParams struct {
	ID string `json:"id"`
}

// DeleteShare deletes a network share.
func (c *Client) DeleteShare(ctx context.Context, id string) error {
	params := DeleteShareParams{ID: id}
	return c.Call(ctx, "storage.shares.delete", params, nil)
}
