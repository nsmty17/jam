import { createBulkAddJob, getJobStatus, cancelJob, IBulkAddRequest, IJobResponse, IJobStatusResponse } from './jam-api';

/**
 * Helper utilities for bulk operations with job polling and progress tracking
 */

export interface IBulkOperationProgress {
    jobId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    progressPercent: number;
    totalItems: number;
    processedItems: number;
    addedItems: number;
    skippedItems: number;
    failedItems: number;
    errorMessage?: string;
}

/**
 * Simple function to create a bulk add job and poll until completion
 */
export async function createBulkAddJobWithPolling(
    request: IBulkAddRequest,
    onProgress?: (status: IJobStatusResponse) => void
): Promise<IJobStatusResponse> {
    // Create the job
    const jobResponse = await createBulkAddJob(request);
    
    // Poll for completion
    let jobStatus: IJobStatusResponse;
    
    do {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        jobStatus = await getJobStatus(jobResponse.job_id);
        
        if (onProgress) {
            onProgress(jobStatus);
        }
        
    } while (jobStatus.status === 'pending' || jobStatus.status === 'processing');
    
    if (jobStatus.status === 'failed') {
        throw new Error(jobStatus.error_message || 'Job failed');
    }
    
    if (jobStatus.status === 'cancelled') {
        throw new Error('Job was cancelled');
    }
    
    return jobStatus;
}

export class BulkOperationManager {
    private pollInterval: number | null = null;
    private onProgressCallback: ((progress: IBulkOperationProgress) => void) | null = null;

    /**
     * Start a bulk add operation and return the job ID
     */
    async startBulkAdd(
        sourceCollectionId: string,
        targetCollectionId: string,
        selectedCompanyIds: number[],
        selectAll: boolean = false
    ): Promise<string> {
        const request: IBulkAddRequest = {
            source_collection_id: sourceCollectionId,
            target_collection_id: targetCollectionId,
            selection_kind: selectAll ? 'all_matching' : 'explicit',
            selection_data: selectAll 
                ? { total_at_snapshot: 0 } // Backend will calculate actual count
                : { ids: selectedCompanyIds }
        };

        const response: IJobResponse = await createBulkAddJob(request);
        return response.job_id;
    }

    /**
     * Start polling a job for progress updates
     */
    startPolling(jobId: string, onProgress: (progress: IBulkOperationProgress) => void): void {
        this.onProgressCallback = onProgress;
        this.pollJob(jobId);
    }

    /**
     * Stop polling
     */
    stopPolling(): void {
        if (this.pollInterval) {
            window.clearTimeout(this.pollInterval);
            this.pollInterval = null;
        }
        this.onProgressCallback = null;
    }

    /**
     * Cancel a running job
     */
    async cancelJob(jobId: string): Promise<void> {
        await cancelJob(jobId);
    }

    /**
     * Private method to poll job status
     */
    private async pollJob(jobId: string): Promise<void> {
        try {
            const status: IJobStatusResponse = await getJobStatus(jobId);
            
            const progress: IBulkOperationProgress = {
                jobId,
                status: status.status,
                progressPercent: status.progress_pct,
                totalItems: status.total_items,
                processedItems: status.processed_items,
                addedItems: status.added_items,
                skippedItems: status.skipped_items,
                failedItems: status.failed_items,
                errorMessage: status.error_message
            };

            // Notify callback
            if (this.onProgressCallback) {
                this.onProgressCallback(progress);
            }

            // Continue polling if job is still active
            if (status.status === 'pending' || status.status === 'processing') {
                this.pollInterval = window.setTimeout(() => {
                    this.pollJob(jobId);
                }, 1000); // Poll every second
            }
        } catch (error) {
            console.error('Error polling job status:', error);
            // Stop polling on error
            this.stopPolling();
        }
    }
}

/**
 * Convenience function for simple bulk add operations
 */
export async function performBulkAdd(
    sourceCollectionId: string,
    targetCollectionId: string,
    selectedCompanyIds: number[],
    selectAll: boolean = false,
    onProgress?: (progress: IBulkOperationProgress) => void
): Promise<string> {
    const manager = new BulkOperationManager();
    const jobId = await manager.startBulkAdd(sourceCollectionId, targetCollectionId, selectedCompanyIds, selectAll);
    
    if (onProgress) {
        manager.startPolling(jobId, onProgress);
    }
    
    return jobId;
}
