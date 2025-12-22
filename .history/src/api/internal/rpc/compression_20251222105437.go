// Package rpc provides compression-related RPC methods.
package rpc

import (
	"context"
	"time"
)

// CompressionStats represents compression statistics.
type CompressionStats struct {
	TotalBytesIn   uint64                     `json:"total_bytes_in"`
	TotalBytesOut  uint64                     `json:"total_bytes_out"`
	AverageRatio   float64                    `json:"average_ratio"`
	BestRatio      float64                    `json:"best_ratio"`
	WorstRatio     float64                    `json:"worst_ratio"`
	TotalJobs      int64                      `json:"total_jobs"`
	SuccessfulJobs int64                      `json:"successful_jobs"`
	FailedJobs     int64                      `json:"failed_jobs"`
	ActiveJobs     int                        `json:"active_jobs"`
	QueuedJobs     int                        `json:"queued_jobs"`
	AverageSpeed   float64                    `json:"average_speed_mbps"`
	TotalSavings   uint64                     `json:"total_savings"`
	AlgorithmStats map[string]*AlgorithmStats `json:"algorithm_stats"`
	LastUpdated    time.Time                  `json:"last_updated"`
}

// AlgorithmStats represents statistics for a specific compression algorithm.
type AlgorithmStats struct {
	Algorithm     string  `json:"algorithm"`
	JobsCompleted int64   `json:"jobs_completed"`
	BytesIn       uint64  `json:"bytes_in"`
	BytesOut      uint64  `json:"bytes_out"`
	AverageRatio  float64 `json:"average_ratio"`
	AverageSpeed  float64 `json:"average_speed_mbps"`
}

// CompressionJob represents a compression/decompression job.
type CompressionJob struct {
	ID          string         `json:"id"`
	Type        string         `json:"type"`   // compress, decompress
	Status      string         `json:"status"` // pending, running, completed, failed, cancelled
	Algorithm   string         `json:"algorithm"`
	Level       int            `json:"level"`
	SourcePath  string         `json:"source_path"`
	DestPath    string         `json:"dest_path"`
	InputSize   uint64         `json:"input_size"`
	OutputSize  uint64         `json:"output_size,omitempty"`
	Ratio       float64        `json:"ratio,omitempty"`
	Progress    float64        `json:"progress"`
	Speed       float64        `json:"speed_mbps,omitempty"`
	ETA         int64          `json:"eta_seconds,omitempty"`
	Error       string         `json:"error,omitempty"`
	Options     map[string]any `json:"options,omitempty"`
	StartedAt   *time.Time     `json:"started_at,omitempty"`
	CompletedAt *time.Time     `json:"completed_at,omitempty"`
	CreatedAt   time.Time      `json:"created_at"`
}

// CompressionAlgorithm represents a supported compression algorithm.
type CompressionAlgorithm struct {
	Name            string  `json:"name"`
	Description     string  `json:"description"`
	Extension       string  `json:"extension"`
	SupportedLevels []int   `json:"supported_levels"`
	DefaultLevel    int     `json:"default_level"`
	SupportsAI      bool    `json:"supports_ai"` // Uses AI-powered compression
	AverageRatio    float64 `json:"average_ratio"`
	AverageSpeed    float64 `json:"average_speed_mbps"`
	IsQuantumSafe   bool    `json:"is_quantum_safe"` // Uses post-quantum encryption
}

// CompressionProfile represents a preset compression profile.
type CompressionProfile struct {
	ID          string         `json:"id"`
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Algorithm   string         `json:"algorithm"`
	Level       int            `json:"level"`
	Options     map[string]any `json:"options"`
	UseAI       bool           `json:"use_ai"`
	UseQuantum  bool           `json:"use_quantum_encryption"`
	IsDefault   bool           `json:"is_default"`
}

// AnalysisResult represents the result of file analysis for compression.
type AnalysisResult struct {
	FilePath        string                    `json:"file_path"`
	FileSize        uint64                    `json:"file_size"`
	FileType        string                    `json:"file_type"`
	MimeType        string                    `json:"mime_type"`
	Entropy         float64                   `json:"entropy"`
	Compressibility float64                   `json:"compressibility"` // 0-1, higher = more compressible
	Recommendations []AlgorithmRecommendation `json:"recommendations"`
	EstimatedRatio  float64                   `json:"estimated_ratio"`
	EstimatedTime   int64                     `json:"estimated_time_seconds"`
}

// AlgorithmRecommendation represents a recommended algorithm for a file.
type AlgorithmRecommendation struct {
	Algorithm      string  `json:"algorithm"`
	Level          int     `json:"level"`
	EstimatedRatio float64 `json:"estimated_ratio"`
	EstimatedSpeed float64 `json:"estimated_speed_mbps"`
	Score          float64 `json:"score"` // Overall recommendation score
	Reason         string  `json:"reason"`
}

// GetCompressionStats retrieves overall compression statistics.
func (c *Client) GetCompressionStats(ctx context.Context) (*CompressionStats, error) {
	var result CompressionStats
	if err := c.Call(ctx, "compression.stats", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListAlgorithms retrieves all supported compression algorithms.
func (c *Client) ListAlgorithms(ctx context.Context) ([]CompressionAlgorithm, error) {
	var result []CompressionAlgorithm
	if err := c.Call(ctx, "compression.algorithms.list", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// ListProfiles retrieves all compression profiles.
func (c *Client) ListProfiles(ctx context.Context) ([]CompressionProfile, error) {
	var result []CompressionProfile
	if err := c.Call(ctx, "compression.profiles.list", nil, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// ListJobsParams are parameters for listing compression jobs.
type ListJobsParams struct {
	Status string `json:"status,omitempty"`
	Type   string `json:"type,omitempty"`
	Limit  int    `json:"limit,omitempty"`
	Offset int    `json:"offset,omitempty"`
}

// ListCompressionJobs retrieves compression jobs.
func (c *Client) ListCompressionJobs(ctx context.Context, params *ListJobsParams) ([]CompressionJob, error) {
	var result []CompressionJob
	if err := c.Call(ctx, "compression.jobs.list", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetJobStatusParams are parameters for GetJobStatus.
type GetJobStatusParams struct {
	JobID string `json:"job_id"`
}

// GetCompressionJobStatus retrieves the status of a compression job.
func (c *Client) GetCompressionJobStatus(ctx context.Context, jobID string) (*CompressionJob, error) {
	params := GetJobStatusParams{JobID: jobID}
	var result CompressionJob
	if err := c.Call(ctx, "compression.jobs.status", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CreateJobParams are parameters for creating a compression job.
type CreateJobParams struct {
	Type       string         `json:"type"` // compress, decompress
	SourcePath string         `json:"source_path"`
	DestPath   string         `json:"dest_path,omitempty"`
	Algorithm  string         `json:"algorithm,omitempty"`
	Level      int            `json:"level,omitempty"`
	ProfileID  string         `json:"profile_id,omitempty"`
	UseAI      bool           `json:"use_ai,omitempty"`
	UseQuantum bool           `json:"use_quantum_encryption,omitempty"`
	Options    map[string]any `json:"options,omitempty"`
	Priority   int            `json:"priority,omitempty"`
}

// CreateCompressionJob creates a new compression/decompression job.
func (c *Client) CreateCompressionJob(ctx context.Context, params *CreateJobParams) (*CompressionJob, error) {
	var result CompressionJob
	if err := c.Call(ctx, "compression.jobs.create", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CancelCompressionJob cancels a running or pending compression job.
func (c *Client) CancelCompressionJob(ctx context.Context, jobID string) error {
	params := map[string]string{"job_id": jobID}
	return c.Call(ctx, "compression.jobs.cancel", params, nil)
}

// AnalyzeFileParams are parameters for file analysis.
type AnalyzeFileParams struct {
	FilePath string `json:"file_path"`
}

// AnalyzeFile analyzes a file for compression recommendations.
func (c *Client) AnalyzeFile(ctx context.Context, filePath string) (*AnalysisResult, error) {
	params := AnalyzeFileParams{FilePath: filePath}
	var result AnalysisResult
	if err := c.Call(ctx, "compression.analyze", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// BatchAnalyzeParams are parameters for batch file analysis.
type BatchAnalyzeParams struct {
	FilePaths []string `json:"file_paths"`
}

// BatchAnalyzeFiles analyzes multiple files for compression.
func (c *Client) BatchAnalyzeFiles(ctx context.Context, filePaths []string) ([]AnalysisResult, error) {
	params := BatchAnalyzeParams{FilePaths: filePaths}
	var result []AnalysisResult
	if err := c.Call(ctx, "compression.analyze.batch", params, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// CreateProfileParams are parameters for creating a compression profile.
type CreateProfileParams struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Algorithm   string         `json:"algorithm"`
	Level       int            `json:"level"`
	Options     map[string]any `json:"options,omitempty"`
	UseAI       bool           `json:"use_ai,omitempty"`
	UseQuantum  bool           `json:"use_quantum_encryption,omitempty"`
}

// CreateProfile creates a new compression profile.
func (c *Client) CreateProfile(ctx context.Context, params *CreateProfileParams) (*CompressionProfile, error) {
	var result CompressionProfile
	if err := c.Call(ctx, "compression.profiles.create", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// DeleteProfile deletes a compression profile.
func (c *Client) DeleteProfile(ctx context.Context, profileID string) error {
	params := map[string]string{"id": profileID}
	return c.Call(ctx, "compression.profiles.delete", params, nil)
}

// QuickCompressParams are parameters for quick compression.
type QuickCompressParams struct {
	SourcePath string `json:"source_path"`
	Algorithm  string `json:"algorithm,omitempty"`
	UseAI      bool   `json:"use_ai,omitempty"`
}

// QuickCompressResult represents the result of quick compression.
type QuickCompressResult struct {
	SourcePath string  `json:"source_path"`
	DestPath   string  `json:"dest_path"`
	InputSize  uint64  `json:"input_size"`
	OutputSize uint64  `json:"output_size"`
	Ratio      float64 `json:"ratio"`
	Algorithm  string  `json:"algorithm"`
	Duration   int64   `json:"duration_ms"`
}

// QuickCompress performs synchronous compression on a file.
func (c *Client) QuickCompress(ctx context.Context, params *QuickCompressParams) (*QuickCompressResult, error) {
	var result QuickCompressResult
	if err := c.Call(ctx, "compression.quick.compress", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// QuickDecompressParams are parameters for quick decompression.
type QuickDecompressParams struct {
	SourcePath string `json:"source_path"`
	DestPath   string `json:"dest_path,omitempty"`
}

// QuickDecompressResult represents the result of quick decompression.
type QuickDecompressResult struct {
	SourcePath string `json:"source_path"`
	DestPath   string `json:"dest_path"`
	InputSize  uint64 `json:"input_size"`
	OutputSize uint64 `json:"output_size"`
	Algorithm  string `json:"algorithm"`
	Duration   int64  `json:"duration_ms"`
}

// QuickDecompress performs synchronous decompression on a file.
func (c *Client) QuickDecompress(ctx context.Context, params *QuickDecompressParams) (*QuickDecompressResult, error) {
	var result QuickDecompressResult
	if err := c.Call(ctx, "compression.quick.decompress", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// EstimateParams are parameters for compression estimation.
type EstimateParams struct {
	SourcePath string `json:"source_path"`
	Algorithm  string `json:"algorithm,omitempty"`
	Level      int    `json:"level,omitempty"`
}

// EstimateResult represents compression estimation.
type EstimateResult struct {
	SourcePath      string  `json:"source_path"`
	InputSize       uint64  `json:"input_size"`
	EstimatedOutput uint64  `json:"estimated_output_size"`
	EstimatedRatio  float64 `json:"estimated_ratio"`
	EstimatedTime   int64   `json:"estimated_time_seconds"`
	Confidence      float64 `json:"confidence"` // 0-1
}

// EstimateCompression estimates compression for a file.
func (c *Client) EstimateCompression(ctx context.Context, params *EstimateParams) (*EstimateResult, error) {
	var result EstimateResult
	if err := c.Call(ctx, "compression.estimate", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}
