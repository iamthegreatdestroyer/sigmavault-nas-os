// Package rpc provides compression RPC methods aligned with the Python engined handlers.
// This file implements the v2 compression API that matches the Python RPC handlers.
package rpc

import (
	"context"
	"encoding/base64"
)

// CompressDataParams are parameters for data compression.
type CompressDataParams struct {
	Data  string `json:"data"`  // Base64 encoded data
	Level string `json:"level"` // fast, balanced, maximum
}

// CompressDataResult is the result of data compression.
type CompressDataResult struct {
	JobID            string  `json:"job_id"`
	Success          bool    `json:"success"`
	OriginalSize     int64   `json:"original_size"`
	CompressedSize   int64   `json:"compressed_size"`
	CompressionRatio float64 `json:"compression_ratio"`
	ElapsedSeconds   float64 `json:"elapsed_seconds"`
	Data             string  `json:"data"` // Base64 encoded compressed data
}

// CompressData compresses data via the Python RPC engine.
func (c *Client) CompressData(ctx context.Context, data []byte, level string) (*CompressDataResult, error) {
	params := CompressDataParams{
		Data:  base64.StdEncoding.EncodeToString(data),
		Level: level,
	}

	var result CompressDataResult
	if err := c.Call(ctx, "compression.compress.data", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CompressFileParams are parameters for file compression.
type CompressFileParams struct {
	SourcePath string `json:"source_path"`
	DestPath   string `json:"dest_path,omitempty"`
	Level      string `json:"level"` // fast, balanced, maximum
}

// CompressFileResult is the result of file compression.
type CompressFileResult struct {
	JobID            string  `json:"job_id"`
	Success          bool    `json:"success"`
	OriginalSize     int64   `json:"original_size"`
	CompressedSize   int64   `json:"compressed_size"`
	CompressionRatio float64 `json:"compression_ratio"`
	ElapsedSeconds   float64 `json:"elapsed_seconds"`
	SourcePath       string  `json:"source_path"`
	DestPath         string  `json:"dest_path"`
}

// CompressFile compresses a file via the Python RPC engine.
func (c *Client) CompressFile(ctx context.Context, params *CompressFileParams) (*CompressFileResult, error) {
	var result CompressFileResult
	if err := c.Call(ctx, "compression.compress.file", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// DecompressDataParams are parameters for data decompression.
type DecompressDataParams struct {
	Data  string `json:"data"`             // Base64 encoded compressed data
	JobID string `json:"job_id,omitempty"` // Optional job ID for tracking
}

// DecompressDataResult is the result of data decompression.
type DecompressDataResult struct {
	JobID            string  `json:"job_id"`
	Success          bool    `json:"success"`
	CompressedSize   int64   `json:"compressed_size"`
	DecompressedSize int64   `json:"decompressed_size"`
	ElapsedSeconds   float64 `json:"elapsed_seconds"`
	Data             string  `json:"data"` // Base64 encoded decompressed data
}

// DecompressData decompresses data via the Python RPC engine.
func (c *Client) DecompressData(ctx context.Context, data []byte, jobID string) (*DecompressDataResult, error) {
	params := DecompressDataParams{
		Data:  base64.StdEncoding.EncodeToString(data),
		JobID: jobID,
	}

	var result DecompressDataResult
	if err := c.Call(ctx, "compression.decompress.data", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// DecompressFileParams are parameters for file decompression.
type DecompressFileParams struct {
	SourcePath string `json:"source_path"`
	DestPath   string `json:"dest_path,omitempty"`
}

// DecompressFileResult is the result of file decompression.
type DecompressFileResult struct {
	JobID            string  `json:"job_id"`
	Success          bool    `json:"success"`
	CompressedSize   int64   `json:"compressed_size"`
	DecompressedSize int64   `json:"decompressed_size"`
	ElapsedSeconds   float64 `json:"elapsed_seconds"`
	SourcePath       string  `json:"source_path"`
	DestPath         string  `json:"dest_path"`
}

// DecompressFile decompresses a file via the Python RPC engine.
func (c *Client) DecompressFile(ctx context.Context, params *DecompressFileParams) (*DecompressFileResult, error) {
	var result DecompressFileResult
	if err := c.Call(ctx, "compression.decompress.file", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// QueueSubmitParams are parameters for submitting a job to the queue.
type QueueSubmitParams struct {
	Type       string `json:"type"`                  // compress_data, compress_file, decompress_data, decompress_file
	SourcePath string `json:"source_path,omitempty"` // For file operations
	DestPath   string `json:"dest_path,omitempty"`   // For file operations
	Data       string `json:"data,omitempty"`        // Base64 encoded data for data operations
	Priority   string `json:"priority,omitempty"`    // low, normal, high, critical
}

// QueueSubmitResult is the result of submitting a job to the queue.
type QueueSubmitResult struct {
	JobID     string `json:"job_id"`
	Status    string `json:"status"`
	Priority  string `json:"priority"`
	JobType   string `json:"job_type"`
	CreatedAt string `json:"created_at"`
}

// QueueSubmit submits a compression job to the queue.
func (c *Client) QueueSubmit(ctx context.Context, params *QueueSubmitParams) (*QueueSubmitResult, error) {
	var result QueueSubmitResult
	if err := c.Call(ctx, "compression.queue.submit", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// QueueStatusParams are parameters for getting queue status.
type QueueStatusParams struct {
	JobID string `json:"job_id,omitempty"` // Optional, if empty returns overall stats
}

// QueueJobStatus represents detailed status of a queued job.
type QueueJobStatus struct {
	JobID       string  `json:"job_id"`
	Status      string  `json:"status"`
	Priority    string  `json:"priority"`
	JobType     string  `json:"job_type"`
	Progress    float64 `json:"progress"`
	CreatedAt   string  `json:"created_at"`
	StartedAt   *string `json:"started_at,omitempty"`
	CompletedAt *string `json:"completed_at,omitempty"`
	Error       *string `json:"error,omitempty"`
}

// QueueStats represents overall queue statistics.
type QueueStats struct {
	TotalJobs     int `json:"total_jobs"`
	PendingJobs   int `json:"pending_jobs"`
	RunningJobs   int `json:"running_jobs"`
	CompletedJobs int `json:"completed_jobs"`
	FailedJobs    int `json:"failed_jobs"`
	CancelledJobs int `json:"cancelled_jobs"`
}

// GetQueueStatus gets status of a specific job or overall queue stats.
func (c *Client) GetQueueStatus(ctx context.Context, jobID string) (*QueueJobStatus, error) {
	params := QueueStatusParams{JobID: jobID}
	var result QueueJobStatus
	if err := c.Call(ctx, "compression.queue.status", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetQueueStats gets overall queue statistics.
func (c *Client) GetQueueStats(ctx context.Context) (*QueueStats, error) {
	var result QueueStats
	if err := c.Call(ctx, "compression.queue.status", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// RunningJobsParams are parameters for getting running jobs.
type RunningJobsParams struct {
	IncludePending bool `json:"include_pending,omitempty"`
	Limit          int  `json:"limit,omitempty"`
}

// RunningJob represents a running or pending job with detailed progress info.
type RunningJob struct {
	JobID          string            `json:"job_id"`
	Status         string            `json:"status"`
	JobType        string            `json:"job_type"`
	Priority       string            `json:"priority"`
	Progress       float64           `json:"progress"`
	Phase          string            `json:"phase"`
	BytesProcessed int64             `json:"bytes_processed"`
	BytesTotal     int64             `json:"bytes_total"`
	CurrentRatio   float64           `json:"current_ratio"`
	ElapsedSeconds float64           `json:"elapsed_seconds"`
	ETASeconds     float64           `json:"eta_seconds"`
	InputPath      string            `json:"input_path,omitempty"`
	OutputPath     string            `json:"output_path,omitempty"`
	CreatedAt      string            `json:"created_at"`
	StartedAt      *string           `json:"started_at,omitempty"`
	UserID         *string           `json:"user_id,omitempty"`
	Tags           map[string]string `json:"tags,omitempty"`
}

// RunningJobsResult is the result of getting running jobs.
type RunningJobsResult struct {
	Jobs         []RunningJob `json:"jobs"`
	TotalRunning int          `json:"total_running"`
	TotalPending int          `json:"total_pending"`
	TotalJobs    int          `json:"total_jobs"`
}

// GetRunningJobs gets all running and pending jobs with detailed progress.
// This is optimized for WebSocket progress streaming.
func (c *Client) GetRunningJobs(ctx context.Context, includePending bool) (*RunningJobsResult, error) {
	params := RunningJobsParams{
		IncludePending: includePending,
		Limit:          50,
	}
	var result RunningJobsResult
	if err := c.Call(ctx, "compression.queue.running", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// QueueCancelParams are parameters for cancelling a job.
type QueueCancelParams struct {
	JobID string `json:"job_id"`
}

// QueueCancelResult is the result of cancelling a job.
type QueueCancelResult struct {
	JobID     string `json:"job_id"`
	Cancelled bool   `json:"cancelled"`
}

// QueueCancel cancels a queued job.
func (c *Client) QueueCancel(ctx context.Context, jobID string) (*QueueCancelResult, error) {
	params := QueueCancelParams{JobID: jobID}
	var result QueueCancelResult
	if err := c.Call(ctx, "compression.queue.cancel", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// CompressionConfig represents compression configuration.
type CompressionConfig struct {
	Level       string `json:"level"` // fast, balanced, maximum
	ChunkSize   int    `json:"chunk_size"`
	UseSemantic bool   `json:"use_semantic"`
	Lossless    bool   `json:"lossless"`
	Engine      string `json:"engine"` // semantic, stub
}

// GetCompressionConfig gets the current compression configuration.
func (c *Client) GetCompressionConfig(ctx context.Context) (*CompressionConfig, error) {
	var result CompressionConfig
	if err := c.Call(ctx, "compression.config.get", nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// SetCompressionConfigParams are parameters for setting compression config.
type SetCompressionConfigParams struct {
	Level       string `json:"level,omitempty"`
	ChunkSize   int    `json:"chunk_size,omitempty"`
	UseSemantic *bool  `json:"use_semantic,omitempty"`
	Lossless    *bool  `json:"lossless,omitempty"`
}

// SetCompressionConfig updates compression configuration.
func (c *Client) SetCompressionConfig(ctx context.Context, params *SetCompressionConfigParams) (*CompressionConfig, error) {
	var result CompressionConfig
	if err := c.Call(ctx, "compression.config.set", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}
